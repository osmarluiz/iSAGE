"""
Dynamic Annotation Dropout Loss with Consistency Regularization

Strategy to prevent overfitting on sparse annotations by:
1. Randomly dropping out annotated points each batch
2. Dynamically swapping points based on model confidence/correctness
3. Prioritizing "confident wrong" points for training
4. Using held-out annotated points as internal validation
5. Consistency regularization on ALL pixels

Training Need Score (higher = needs more training):
    - Confident Wrong:   4 (urgent!)
    - Uncertain Wrong:   3
    - Uncertain Correct: 2
    - Confident Correct: 1 (already learned)

Author: Generated for SIAL project
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional


class DynamicAnnotationLoss(nn.Module):
    """
    BCE Loss with Dynamic Annotation Dropout.

    Instead of training on all annotated points every batch:
    - Randomly select a subset for training
    - Monitor predictions on held-out annotated points
    - Swap points based on "training need score"

    Args:
        dropout_rate: Fraction of annotated points to hold out (default: 0.5)
        confidence_threshold: Threshold for confident vs uncertain (default: 0.85)
        warmup_epochs: Epochs before starting dynamic swapping (default: 3)
        ignore_value: Value in mask indicating unlabeled pixels (default: 2)
        eps: Small constant for numerical stability (default: 1e-7)
    """

    def __init__(
        self,
        dropout_rate: float = 0.5,
        confidence_threshold: float = 0.85,
        warmup_epochs: int = 3,
        ignore_value: int = 2,
        eps: float = 1e-7
    ):
        super().__init__()
        self.dropout_rate = dropout_rate
        self.confidence_threshold = confidence_threshold
        self.warmup_epochs = warmup_epochs
        self.ignore_value = ignore_value
        self.eps = eps

        # Current epoch (set externally)
        self.current_epoch = 0

        # Statistics for monitoring
        self.stats = {}

    def compute_training_need_score(
        self,
        pred: torch.Tensor,
        gt: torch.Tensor,
        confidence: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute training need score for each pixel.

        Higher score = needs more training:
            - Confident Wrong:   4
            - Uncertain Wrong:   3
            - Uncertain Correct: 2
            - Confident Correct: 1
        """
        is_correct = ((pred > 0.5) == (gt == 1))
        is_confident = confidence > self.confidence_threshold

        # Base score
        score = torch.ones_like(pred)

        # Confident Correct: 1 (lowest need)
        score[is_confident & is_correct] = 1.0

        # Uncertain Correct: 2
        score[~is_confident & is_correct] = 2.0

        # Uncertain Wrong: 3
        score[~is_confident & ~is_correct] = 3.0

        # Confident Wrong: 4 (highest need)
        score[is_confident & ~is_correct] = 4.0

        # Add confidence as tiebreaker within categories
        confidence_bonus = (confidence - 0.5) * 0.5  # 0 to 0.25
        score = torch.where(
            is_correct,
            score - confidence_bonus,  # Correct: more confident = less need
            score + confidence_bonus   # Wrong: more confident = more need
        )

        return score

    def create_dynamic_mask(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Create training and holdout masks based on dynamic selection.
        """
        B, H, W = mask.shape
        device = mask.device

        # Find annotated points (not ignore)
        annotated = mask != self.ignore_value

        # Compute confidence
        confidence = torch.max(pred, 1 - pred)

        # Compute training need scores
        scores = self.compute_training_need_score(pred, mask.float(), confidence)

        # Initialize masks
        train_mask = torch.zeros_like(annotated)
        holdout_mask = torch.zeros_like(annotated)

        # Process each image in batch
        for b in range(B):
            # Get annotated points for this image
            ann_points = annotated[b].nonzero(as_tuple=False)  # (N, 2)
            n_points = len(ann_points)

            if n_points == 0:
                continue

            # Get scores for these points
            point_scores = scores[b][annotated[b]]  # (N,)

            if self.current_epoch < self.warmup_epochs:
                # Warmup: random selection
                n_train = int(n_points * (1 - self.dropout_rate))
                perm = torch.randperm(n_points, device=device)
                train_indices = perm[:n_train]
                holdout_indices = perm[n_train:]
            else:
                # Dynamic selection based on scores
                # Higher score = higher priority for training
                sorted_indices = torch.argsort(point_scores, descending=True)

                n_train = int(n_points * (1 - self.dropout_rate))

                # Top scores go to training
                train_indices = sorted_indices[:n_train]
                holdout_indices = sorted_indices[n_train:]

            # Create masks
            for idx in train_indices:
                y, x = ann_points[idx]
                train_mask[b, y, x] = True

            for idx in holdout_indices:
                y, x = ann_points[idx]
                holdout_mask[b, y, x] = True

        return train_mask, holdout_mask

    def forward(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Dict]:
        """
        Compute Dynamic Annotation Loss.

        Returns:
            loss: BCE loss on training points
            train_mask: Mask of training points
            holdout_mask: Mask of holdout points
            stats: Statistics dict
        """
        # Handle shape
        if pred.dim() == 4 and pred.shape[1] == 1:
            pred = pred.squeeze(1)

        # Create dynamic train/holdout split
        with torch.no_grad():
            train_mask, holdout_mask = self.create_dynamic_mask(pred, mask)

        # Compute BCE loss only on training points
        pred_clamped = torch.clamp(pred, min=self.eps, max=1.0 - self.eps)

        bce = -(mask.float() * torch.log(pred_clamped) +
                (1 - mask.float()) * torch.log(1 - pred_clamped))

        # Mask to only training points
        if train_mask.any():
            loss = (bce * train_mask.float()).sum() / (train_mask.float().sum() + self.eps)
        else:
            loss = torch.tensor(0.0, device=pred.device)

        # Compute statistics
        with torch.no_grad():
            stats = self._compute_statistics(pred, mask, train_mask, holdout_mask)

        return loss, train_mask, holdout_mask, stats

    def _compute_statistics(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        train_mask: torch.Tensor,
        holdout_mask: torch.Tensor
    ) -> Dict[str, float]:
        """Compute statistics for monitoring."""
        confidence = torch.max(pred, 1 - pred)
        is_correct = ((pred > 0.5) == (mask == 1))
        is_confident = confidence > self.confidence_threshold

        stats = {}

        # Training set statistics
        if train_mask.any():
            stats['train_cc'] = (is_confident & is_correct & train_mask).sum().item()
            stats['train_cw'] = (is_confident & ~is_correct & train_mask).sum().item()
            stats['train_uc'] = (~is_confident & is_correct & train_mask).sum().item()
            stats['train_uw'] = (~is_confident & ~is_correct & train_mask).sum().item()
            stats['train_total'] = train_mask.sum().item()

        # Holdout set statistics
        if holdout_mask.any():
            stats['holdout_cc'] = (is_confident & is_correct & holdout_mask).sum().item()
            stats['holdout_cw'] = (is_confident & ~is_correct & holdout_mask).sum().item()
            stats['holdout_uc'] = (~is_confident & is_correct & holdout_mask).sum().item()
            stats['holdout_uw'] = (~is_confident & ~is_correct & holdout_mask).sum().item()
            stats['holdout_total'] = holdout_mask.sum().item()

            # Holdout accuracy
            n_holdout = holdout_mask.sum().item()
            n_correct = (is_correct & holdout_mask).sum().item()
            stats['holdout_accuracy'] = n_correct / n_holdout if n_holdout > 0 else 0.0

        return stats

    def set_epoch(self, epoch: int):
        """Set current epoch for warmup handling."""
        self.current_epoch = epoch


class DynamicAnnotationWithConsistencyLoss(nn.Module):
    """
    Combines Dynamic Annotation Loss with Confidence-Weighted Consistency.

    1. Dynamic Annotation Loss on selected annotated points (BCE)
    2. Confidence-weighted Consistency Loss on ALL pixels

    Args:
        dropout_rate: Fraction of annotated points to hold out
        confidence_threshold: Threshold for confident vs uncertain
        consistency_weight: Max weight for consistency loss (default: 0.1)
        consistency_rampup: Epochs to ramp up consistency weight (default: 10)
        warmup_epochs: Epochs before dynamic selection starts (default: 3)
        ignore_value: Value indicating unlabeled pixels
    """

    def __init__(
        self,
        dropout_rate: float = 0.5,
        confidence_threshold: float = 0.85,
        consistency_weight: float = 0.1,
        consistency_rampup: int = 10,
        warmup_epochs: int = 3,
        ignore_value: int = 2,
        eps: float = 1e-7
    ):
        super().__init__()

        self.dynamic_loss = DynamicAnnotationLoss(
            dropout_rate=dropout_rate,
            confidence_threshold=confidence_threshold,
            warmup_epochs=warmup_epochs,
            ignore_value=ignore_value,
            eps=eps
        )

        self.confidence_threshold = confidence_threshold
        self.consistency_weight = consistency_weight
        self.consistency_rampup = consistency_rampup
        self.eps = eps

        self.current_epoch = 0
        self.stats = {}

    def compute_consistency_loss(
        self,
        model: nn.Module,
        images: torch.Tensor,
        pred_original: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute confidence-weighted consistency loss.

        Uses horizontal flip as augmentation.
        Weights consistency by confidence (more confident = enforce more).

        Returns:
            consistency_loss: The loss value
            pred_aug_aligned: The aligned augmented predictions (for stats)
        """
        # Augment: horizontal flip
        images_flip = torch.flip(images, dims=[-1])

        # Get prediction for flipped images
        pred_flip = model(images_flip)
        if pred_flip.dim() == 4 and pred_flip.shape[1] == 1:
            pred_flip = pred_flip.squeeze(1)

        # Align by flipping prediction back
        pred_flip_aligned = torch.flip(pred_flip, dims=[-1])

        # Confidence from original prediction
        confidence = torch.max(pred_original, 1 - pred_original)

        # Confidence-weighted MSE
        # Higher confidence = stronger consistency enforcement
        diff_squared = (pred_original - pred_flip_aligned) ** 2
        weighted_diff = confidence * diff_squared

        consistency_loss = weighted_diff.mean()

        return consistency_loss, pred_flip_aligned

    def get_consistency_weight(self) -> float:
        """Get ramped consistency weight based on current epoch."""
        if self.current_epoch < self.consistency_rampup:
            return self.consistency_weight * (self.current_epoch / self.consistency_rampup)
        return self.consistency_weight

    def forward(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        model: nn.Module,
        images: torch.Tensor,
        return_components: bool = False
    ) -> torch.Tensor:
        """
        Compute combined loss.

        Args:
            pred: Model predictions (B, 1, H, W) or (B, H, W)
            mask: Ground truth (B, H, W)
            model: The model (needed for consistency loss)
            images: Input images (needed for consistency loss)
            return_components: If True, return (loss, stats) tuple
        """
        # Handle shape
        if pred.dim() == 4 and pred.shape[1] == 1:
            pred_squeezed = pred.squeeze(1)
        else:
            pred_squeezed = pred

        # 1. Dynamic annotation loss
        supervised_loss, train_mask, holdout_mask, dyn_stats = self.dynamic_loss(
            pred_squeezed, mask
        )

        # 2. Consistency loss
        consistency_loss, pred_aug = self.compute_consistency_loss(
            model, images, pred_squeezed
        )
        lambda_consist = self.get_consistency_weight()

        # Combined loss
        total_loss = supervised_loss + lambda_consist * consistency_loss

        # Collect stats
        with torch.no_grad():
            # Consistency stats
            confidence = torch.max(pred_squeezed, 1 - pred_squeezed)
            pred_diff = torch.abs(pred_squeezed - pred_aug)
            avg_consistency = pred_diff.mean().item()

            # Where confident, how consistent?
            confident_mask = confidence > self.confidence_threshold
            if confident_mask.any():
                confident_consistency = pred_diff[confident_mask].mean().item()
            else:
                confident_consistency = 0.0

        self.stats = {
            **dyn_stats,
            'supervised_loss': supervised_loss.item(),
            'consistency_loss': consistency_loss.item(),
            'consistency_weight': lambda_consist,
            'avg_pred_diff': avg_consistency,
            'confident_pred_diff': confident_consistency,
            'total_loss': total_loss.item()
        }

        if return_components:
            return total_loss, self.stats
        return total_loss

    def set_epoch(self, epoch: int):
        """Set current epoch."""
        self.current_epoch = epoch
        self.dynamic_loss.set_epoch(epoch)


def format_stats(stats: Dict, compact: bool = True) -> str:
    """Format statistics for printing."""
    if compact:
        train_total = stats.get('train_total', 0)
        holdout_total = stats.get('holdout_total', 0)
        holdout_acc = stats.get('holdout_accuracy', 0) * 100

        train_cw = stats.get('train_cw', 0)
        holdout_cw = stats.get('holdout_cw', 0)

        sup_loss = stats.get('supervised_loss', 0)
        con_loss = stats.get('consistency_loss', 0)
        con_w = stats.get('consistency_weight', 0)

        return (f"Tr:{train_total}(cw={train_cw}) Ho:{holdout_total}(cw={holdout_cw},acc={holdout_acc:.0f}%) "
                f"L_sup={sup_loss:.4f} L_con={con_loss:.4f}(w={con_w:.2f})")
    else:
        lines = []
        lines.append(f"Train: CC={stats.get('train_cc',0)} CW={stats.get('train_cw',0)} "
                    f"UC={stats.get('train_uc',0)} UW={stats.get('train_uw',0)}")
        lines.append(f"Holdout: CC={stats.get('holdout_cc',0)} CW={stats.get('holdout_cw',0)} "
                    f"UC={stats.get('holdout_uc',0)} UW={stats.get('holdout_uw',0)} "
                    f"Acc={stats.get('holdout_accuracy',0)*100:.1f}%")
        lines.append(f"Loss: sup={stats.get('supervised_loss',0):.4f} "
                    f"con={stats.get('consistency_loss',0):.4f} "
                    f"(w={stats.get('consistency_weight',0):.2f})")
        return "\n".join(lines)
