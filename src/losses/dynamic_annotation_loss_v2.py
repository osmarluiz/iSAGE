"""
Dynamic Annotation Dropout Loss v2 - CORRECTED

Key differences from v1:
1. Maintains PERSISTENT train/holdout sets across batches
2. SWAPS points between sets (not reselects everything)
3. Holdout always has a MIX of easy/hard cases (useful for validation)
4. Swap rate limits how many points move per epoch

Strategy:
- Start with random 50/50 split
- Each epoch, identify candidates for swap:
  - FROM TRAIN → HOLDOUT: "confident correct" (already learned)
  - FROM HOLDOUT → TRAIN: "confident wrong" (needs learning)
- Swap limited number to maintain diversity in both sets
- Holdout accuracy is meaningful proxy for generalization

Author: Generated for SIAL project
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional, List
from collections import defaultdict


class DynamicAnnotationLossV2(nn.Module):
    """
    BCE Loss with Dynamic Annotation Dropout - CORRECTED VERSION.

    Maintains persistent train/holdout assignment per image.
    Swaps points between sets based on model performance.

    Args:
        dropout_rate: Fraction of annotated points in holdout (default: 0.5)
        confidence_threshold: Threshold for confident vs uncertain (default: 0.85)
        swap_rate: Max fraction of points to swap per epoch (default: 0.1)
        warmup_epochs: Epochs before starting swaps (default: 3)
        ignore_value: Value in mask indicating unlabeled pixels (default: 2)
    """

    def __init__(
        self,
        dropout_rate: float = 0.5,
        confidence_threshold: float = 0.85,
        swap_rate: float = 0.1,  # Max 10% of points swap per epoch
        warmup_epochs: int = 3,
        ignore_value: int = 2,
        eps: float = 1e-7
    ):
        super().__init__()
        self.dropout_rate = dropout_rate
        self.confidence_threshold = confidence_threshold
        self.swap_rate = swap_rate
        self.warmup_epochs = warmup_epochs
        self.ignore_value = ignore_value
        self.eps = eps

        self.current_epoch = 0

        # Persistent assignment: image_idx -> {'train': set of (y,x), 'holdout': set of (y,x)}
        self.assignments = {}
        self.initialized = False

        # Track swaps for logging
        self.swaps_this_epoch = {'to_train': 0, 'to_holdout': 0}

    def initialize_assignments(self, masks: torch.Tensor, batch_indices: List[int]):
        """Initialize random train/holdout split for new images."""
        B = masks.shape[0]

        for b in range(B):
            img_idx = batch_indices[b]

            if img_idx in self.assignments:
                continue  # Already initialized

            # Find annotated points
            annotated = (masks[b] != self.ignore_value).cpu().numpy()
            points = list(zip(*np.where(annotated)))

            if len(points) == 0:
                self.assignments[img_idx] = {'train': set(), 'holdout': set()}
                continue

            # Random split
            np.random.shuffle(points)
            n_holdout = int(len(points) * self.dropout_rate)

            holdout_points = set(points[:n_holdout])
            train_points = set(points[n_holdout:])

            self.assignments[img_idx] = {
                'train': train_points,
                'holdout': holdout_points
            }

    def compute_point_categories(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        points: set
    ) -> Dict[str, List[Tuple[int, int, float]]]:
        """
        Categorize points by confidence and correctness.

        Returns dict with lists of (y, x, score) for each category.
        Score is used to prioritize within category.
        """
        categories = {
            'confident_correct': [],
            'confident_wrong': [],
            'uncertain_correct': [],
            'uncertain_wrong': []
        }

        pred_np = pred.detach().cpu().numpy()
        mask_np = mask.detach().cpu().numpy()

        for (y, x) in points:
            p = pred_np[y, x]
            gt = mask_np[y, x]

            confidence = max(p, 1 - p)
            is_correct = (p > 0.5) == (gt == 1)
            is_confident = confidence > self.confidence_threshold

            # Score: higher confidence = higher priority for action
            score = confidence

            if is_confident and is_correct:
                categories['confident_correct'].append((y, x, score))
            elif is_confident and not is_correct:
                categories['confident_wrong'].append((y, x, score))
            elif not is_confident and is_correct:
                categories['uncertain_correct'].append((y, x, score))
            else:
                categories['uncertain_wrong'].append((y, x, score))

        # Sort each category by score (descending)
        for cat in categories:
            categories[cat].sort(key=lambda x: -x[2])

        return categories

    def perform_swaps(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        img_idx: int
    ) -> Dict[str, int]:
        """
        Perform swaps between train and holdout sets for one image.

        Swap logic:
        - FROM TRAIN → HOLDOUT: top "confident correct" (already learned)
        - FROM HOLDOUT → TRAIN: top "confident wrong" (needs learning urgently!)

        Returns counts of swaps made.
        """
        assignment = self.assignments[img_idx]
        train_points = assignment['train']
        holdout_points = assignment['holdout']

        # Categorize current train points
        train_cats = self.compute_point_categories(pred, mask, train_points)

        # Categorize current holdout points
        holdout_cats = self.compute_point_categories(pred, mask, holdout_points)

        # Calculate max swaps allowed
        total_points = len(train_points) + len(holdout_points)
        max_swaps = max(1, int(total_points * self.swap_rate))

        swaps = {'to_train': 0, 'to_holdout': 0}

        # Find candidates for swap
        # FROM HOLDOUT → TRAIN: confident wrong (urgent!) and uncertain wrong
        candidates_to_train = (
            holdout_cats['confident_wrong'] +
            holdout_cats['uncertain_wrong']
        )

        # FROM TRAIN → HOLDOUT: confident correct (already learned)
        candidates_to_holdout = train_cats['confident_correct']

        # Perform balanced swaps
        n_swaps = min(len(candidates_to_train), len(candidates_to_holdout), max_swaps)

        for i in range(n_swaps):
            # Move from holdout to train
            y, x, _ = candidates_to_train[i]
            holdout_points.discard((y, x))
            train_points.add((y, x))
            swaps['to_train'] += 1

            # Move from train to holdout
            y, x, _ = candidates_to_holdout[i]
            train_points.discard((y, x))
            holdout_points.add((y, x))
            swaps['to_holdout'] += 1

        return swaps

    def get_masks_for_batch(
        self,
        masks: torch.Tensor,
        batch_indices: List[int]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Get train and holdout masks for a batch."""
        B, H, W = masks.shape
        device = masks.device

        train_mask = torch.zeros((B, H, W), dtype=torch.bool, device=device)
        holdout_mask = torch.zeros((B, H, W), dtype=torch.bool, device=device)

        for b in range(B):
            img_idx = batch_indices[b]
            assignment = self.assignments.get(img_idx, {'train': set(), 'holdout': set()})

            for (y, x) in assignment['train']:
                train_mask[b, y, x] = True

            for (y, x) in assignment['holdout']:
                holdout_mask[b, y, x] = True

        return train_mask, holdout_mask

    def forward(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        batch_indices: List[int],
        do_swaps: bool = True
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Compute loss with dynamic annotation dropout.

        Args:
            pred: Predictions (B, 1, H, W) or (B, H, W)
            mask: Ground truth (B, H, W)
            batch_indices: List of image indices in this batch
            do_swaps: Whether to perform swaps this forward pass
        """
        if pred.dim() == 4 and pred.shape[1] == 1:
            pred = pred.squeeze(1)

        B = pred.shape[0]

        # Initialize assignments for new images
        self.initialize_assignments(mask, batch_indices)

        # Perform swaps if past warmup
        if do_swaps and self.current_epoch >= self.warmup_epochs:
            for b in range(B):
                swaps = self.perform_swaps(pred[b], mask[b], batch_indices[b])
                self.swaps_this_epoch['to_train'] += swaps['to_train']
                self.swaps_this_epoch['to_holdout'] += swaps['to_holdout']

        # Get current train/holdout masks
        train_mask, holdout_mask = self.get_masks_for_batch(mask, batch_indices)

        # Compute BCE loss on train points only
        pred_clamped = torch.clamp(pred, min=self.eps, max=1.0 - self.eps)
        bce = -(mask.float() * torch.log(pred_clamped) +
                (1 - mask.float()) * torch.log(1 - pred_clamped))

        if train_mask.any():
            loss = (bce * train_mask.float()).sum() / (train_mask.float().sum() + self.eps)
        else:
            loss = torch.tensor(0.0, device=pred.device)

        # Compute statistics
        stats = self._compute_stats(pred, mask, train_mask, holdout_mask)

        return loss, stats

    def _compute_stats(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        train_mask: torch.Tensor,
        holdout_mask: torch.Tensor
    ) -> Dict:
        """Compute detailed statistics."""
        confidence = torch.max(pred, 1 - pred)
        is_correct = ((pred > 0.5) == (mask == 1))
        is_confident = confidence > self.confidence_threshold

        stats = {}

        # Train stats
        stats['train_cc'] = (is_confident & is_correct & train_mask).sum().item()
        stats['train_cw'] = (is_confident & ~is_correct & train_mask).sum().item()
        stats['train_uc'] = (~is_confident & is_correct & train_mask).sum().item()
        stats['train_uw'] = (~is_confident & ~is_correct & train_mask).sum().item()
        stats['train_total'] = train_mask.sum().item()

        # Holdout stats
        stats['holdout_cc'] = (is_confident & is_correct & holdout_mask).sum().item()
        stats['holdout_cw'] = (is_confident & ~is_correct & holdout_mask).sum().item()
        stats['holdout_uc'] = (~is_confident & is_correct & holdout_mask).sum().item()
        stats['holdout_uw'] = (~is_confident & ~is_correct & holdout_mask).sum().item()
        stats['holdout_total'] = holdout_mask.sum().item()

        # Holdout accuracy
        holdout_correct = stats['holdout_cc'] + stats['holdout_uc']
        stats['holdout_accuracy'] = holdout_correct / stats['holdout_total'] if stats['holdout_total'] > 0 else 0

        return stats

    def set_epoch(self, epoch: int):
        """Set epoch and reset swap counters."""
        self.current_epoch = epoch
        self.swaps_this_epoch = {'to_train': 0, 'to_holdout': 0}

    def get_swap_counts(self) -> Dict[str, int]:
        """Get swap counts for current epoch."""
        return self.swaps_this_epoch.copy()


class DynamicAnnotationWithConsistencyV2(nn.Module):
    """
    Dynamic Annotation Loss V2 + Confidence-Weighted Consistency.

    1. Dynamic point selection with proper SWAPS
    2. Consistency loss on ALL pixels (weighted by confidence)
    """

    def __init__(
        self,
        dropout_rate: float = 0.5,
        confidence_threshold: float = 0.85,
        swap_rate: float = 0.1,
        consistency_weight: float = 0.1,
        consistency_rampup: int = 10,
        warmup_epochs: int = 3,
        ignore_value: int = 2,
        eps: float = 1e-7
    ):
        super().__init__()

        self.dynamic_loss = DynamicAnnotationLossV2(
            dropout_rate=dropout_rate,
            confidence_threshold=confidence_threshold,
            swap_rate=swap_rate,
            warmup_epochs=warmup_epochs,
            ignore_value=ignore_value,
            eps=eps
        )

        self.confidence_threshold = confidence_threshold
        self.consistency_weight = consistency_weight
        self.consistency_rampup = consistency_rampup
        self.eps = eps
        self.current_epoch = 0

    def compute_consistency_loss(
        self,
        model: nn.Module,
        images: torch.Tensor,
        pred_original: torch.Tensor
    ) -> Tuple[torch.Tensor, float]:
        """
        Confidence-weighted consistency loss using horizontal flip.
        """
        # Flip images
        images_flip = torch.flip(images, dims=[-1])

        # Get predictions
        pred_flip = model(images_flip)
        if pred_flip.dim() == 4:
            pred_flip = pred_flip.squeeze(1)

        # Align
        pred_flip_aligned = torch.flip(pred_flip, dims=[-1])

        # Confidence weighting
        confidence = torch.max(pred_original, 1 - pred_original)

        # Weighted MSE
        diff_sq = (pred_original - pred_flip_aligned) ** 2
        weighted_diff = confidence * diff_sq

        loss = weighted_diff.mean()
        avg_diff = diff_sq.mean().item()

        return loss, avg_diff

    def get_consistency_weight(self) -> float:
        """Ramp up consistency weight."""
        if self.current_epoch < self.consistency_rampup:
            return self.consistency_weight * (self.current_epoch / self.consistency_rampup)
        return self.consistency_weight

    def forward(
        self,
        pred: torch.Tensor,
        mask: torch.Tensor,
        model: nn.Module,
        images: torch.Tensor,
        batch_indices: List[int]
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Combined loss.
        """
        if pred.dim() == 4:
            pred_sq = pred.squeeze(1)
        else:
            pred_sq = pred

        # 1. Dynamic annotation loss
        sup_loss, stats = self.dynamic_loss(pred_sq, mask, batch_indices)

        # 2. Consistency loss
        con_loss, avg_diff = self.compute_consistency_loss(model, images, pred_sq)
        lambda_con = self.get_consistency_weight()

        # Combined
        total_loss = sup_loss + lambda_con * con_loss

        # Add to stats
        stats['supervised_loss'] = sup_loss.item()
        stats['consistency_loss'] = con_loss.item()
        stats['consistency_weight'] = lambda_con
        stats['avg_pred_diff'] = avg_diff
        stats['total_loss'] = total_loss.item()
        stats['swaps'] = self.dynamic_loss.get_swap_counts()

        return total_loss, stats

    def set_epoch(self, epoch: int):
        self.current_epoch = epoch
        self.dynamic_loss.set_epoch(epoch)
