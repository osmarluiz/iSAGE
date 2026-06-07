import torch
import torch.nn as nn

from . import base
from . import functional as F
from ..base.modules import Activation


class JaccardLoss(base.Loss):
    def __init__(self, eps=1.0, activation=None, ignore_channels=None, **kwargs):
        super().__init__(**kwargs)
        self.eps = eps
        self.activation = Activation(activation)
        self.ignore_channels = ignore_channels

    def forward(self, y_pr, y_gt):
        y_pr = self.activation(y_pr)
        return 1 - F.jaccard(
            y_pr,
            y_gt,
            eps=self.eps,
            threshold=None,
            ignore_channels=self.ignore_channels,
        )
    
class DiceLoss(base.Loss):

    def __init__(self, eps=1., beta=1., activation=None, ignore_channels=None, ignore_index=None, **kwargs):
        super().__init__(**kwargs)
        self.eps = eps
        self.beta = beta
        self.activation = Activation(activation)
        self.ignore_channels = ignore_channels
        self.ignore_index = ignore_index

    def forward(self, y_pr, y_gt):

        y_pr = self.activation(y_pr)
        # Binary single-channel: pred is (B, 1, H, W) but gt is (B, H, W).
        # Without squeeze, broadcasting expands to (B, B, H, W) and inflates tp,
        # which makes fp/fn negative and the loss go below zero (esp. for
        # high-fg classes). Squeeze to keep shapes aligned.
        if y_pr.dim() == 4 and y_pr.size(1) == 1:
            y_pr = y_pr.squeeze(1)

        if self.ignore_index is not None:
            mask = (y_gt != self.ignore_index)
            y_pr = y_pr * mask
            y_gt = y_gt * mask

        return 1 - F.f_score(
            y_pr, y_gt,
            beta=self.beta,
            eps=self.eps,
            threshold=None,
            ignore_channels=self.ignore_channels,
        )


class L1Loss(nn.L1Loss, base.Loss):
    pass


class MSELoss(nn.MSELoss, base.Loss):
    pass


class CrossEntropyLoss(nn.CrossEntropyLoss, base.Loss):
    pass


class NLLLoss(nn.NLLLoss, base.Loss):
    pass


class BCELoss(nn.BCELoss, base.Loss):
    pass


class BCEWithLogitsLoss(nn.BCEWithLogitsLoss, base.Loss):
    pass


class FocalLoss(base.Loss):
    """
    Focal Loss for multiclass semantic segmentation.

    Focal loss applies a modulating term to the cross entropy loss to focus learning
    on hard misclassified examples. It helps with class imbalance.

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    where:
    - p_t is the model's estimated probability for the true class
    - gamma is the focusing parameter (gamma > 0 reduces loss for well-classified examples)
    - alpha is the weighting factor for class imbalance
    """
    __name__ = "focal_loss"

    def __init__(self, alpha=None, gamma=2.0, ignore_index=None, **kwargs):
        """
        Args:
            alpha: Optional class weights (tensor of shape [num_classes])
            gamma: Focusing parameter (default: 2.0)
            ignore_index: Optional index to ignore in loss computation
        """
        super().__init__(**kwargs)
        self.alpha = alpha
        self.gamma = gamma
        self.ignore_index = ignore_index

    def forward(self, y_pr, y_gt):
        """
        Args:
            y_pr: (B, C, H, W) - Model predictions (logits or probabilities)
            y_gt: (B, H, W) - Ground truth labels (integer values per pixel)
        """
        # Apply softmax to get probabilities if not already applied
        if y_pr.dim() == 4:  # (B, C, H, W)
            log_probs = torch.nn.functional.log_softmax(y_pr, dim=1)
            probs = torch.nn.functional.softmax(y_pr, dim=1)
        else:
            raise ValueError(f"Expected 4D input (B, C, H, W), got {y_pr.dim()}D")

        # Handle ignore_index
        if self.ignore_index is not None:
            valid_mask = (y_gt != self.ignore_index)  # (B, H, W)
        else:
            valid_mask = torch.ones_like(y_gt, dtype=torch.bool)

        # Gather log probabilities and probabilities for the true class
        # y_gt: (B, H, W), need to unsqueeze to (B, 1, H, W) for gather
        y_gt_clamped = y_gt.clone()
        if self.ignore_index is not None:
            y_gt_clamped[~valid_mask] = 0  # Temporary value for gather

        y_gt_unsqueezed = y_gt_clamped.unsqueeze(1)  # (B, 1, H, W)

        # Gather the log_prob and prob for the true class
        log_pt = torch.gather(log_probs, dim=1, index=y_gt_unsqueezed).squeeze(1)  # (B, H, W)
        pt = torch.gather(probs, dim=1, index=y_gt_unsqueezed).squeeze(1)  # (B, H, W)

        # Compute focal term: (1 - pt)^gamma
        focal_weight = (1 - pt) ** self.gamma

        # Compute focal loss: -focal_weight * log(pt)
        focal_loss = -focal_weight * log_pt

        # Apply class weights (alpha) if provided
        if self.alpha is not None:
            if self.alpha.device != y_gt.device:
                self.alpha = self.alpha.to(y_gt.device)
            # Gather alpha for each pixel's true class
            alpha_t = torch.gather(self.alpha.unsqueeze(0).expand(y_gt.shape[0], -1),
                                   dim=1,
                                   index=y_gt_clamped.view(y_gt.shape[0], -1))
            alpha_t = alpha_t.view_as(y_gt)  # (B, H, W)
            focal_loss = alpha_t * focal_loss

        # Apply valid mask (ignore pixels)
        focal_loss = focal_loss * valid_mask.float()

        # Return mean loss
        num_valid = valid_mask.float().sum()
        if num_valid > 0:
            return focal_loss.sum() / num_valid
        else:
            return focal_loss.sum()  # Should be 0


# =============================================================================
# ERROR-WEIGHTED DICE LOSS (EWDL) - Simplified version
# =============================================================================

class EWDLBinary(base.Loss):
    """
    Error-Weighted Dice Loss (EWDL) for binary segmentation.

    A simplified approach that weights pixels based only on correctness:
    - Correct predictions: weight = 1.0
    - Wrong predictions: weight = wrong_penalty (α)

    This removes the complexity of confidence thresholds, leaving only one
    hyperparameter to tune: the penalty for errors.

    Args:
        eps: Small constant for numerical stability (default: 1.0)
        wrong_penalty: Weight multiplier for incorrect predictions (default: 10.0)
        activation: Activation function ('sigmoid' or None)
        ignore_index: Value to ignore in ground truth (default: 2 for sparse masks)
    """
    __name__ = "ewdl_binary_loss"

    def __init__(self,
                 eps=1.0,
                 wrong_penalty=10.0,
                 activation=None,
                 ignore_index=2,
                 **kwargs):
        super().__init__(**kwargs)
        self.eps = eps
        self.wrong_penalty = wrong_penalty
        self.activation = Activation(activation)
        self.ignore_index = ignore_index

    def forward(self, y_pr, y_gt):
        """
        Args:
            y_pr: (B, 1, H, W) or (B, H, W) - Model predictions
            y_gt: (B, H, W) - Ground truth (0=background, 1=foreground, ignore_index=ignore)
        """
        # Apply activation to get probabilities
        y_pr = self.activation(y_pr)
        if y_pr.dim() == 4:
            y_pr = y_pr.squeeze(1)  # (B, H, W)

        # Convert ground truth to float
        y_gt_float = y_gt.float()

        # Create valid mask (exclude ignore_index)
        if self.ignore_index is not None:
            valid_mask = (y_gt != self.ignore_index).float()
        else:
            valid_mask = torch.ones_like(y_gt, dtype=torch.float32)

        # Determine correctness: does thresholded prediction match ground truth?
        pred_class = (y_pr > 0.5).float()
        gt_class = (y_gt_float > 0.5).float()
        is_correct = (pred_class == gt_class)

        # Assign weights: 1.0 for correct, wrong_penalty for wrong
        weights = torch.ones_like(y_gt, dtype=torch.float32)
        weights[~is_correct] = self.wrong_penalty

        # Apply valid_mask
        weights = weights * valid_mask

        # Clamp y_gt to valid range for Dice computation
        y_gt_clamped = torch.clamp(y_gt_float, 0, 1) * valid_mask

        # Normalize weights to avoid instability
        weights = weights / (weights.sum() + 1e-8) * valid_mask.sum()

        # Calculate weighted Dice loss
        intersection = (weights * y_pr * y_gt_clamped).sum()
        denominator = (weights * (y_pr + y_gt_clamped)).sum()
        dice_loss = 1 - (2 * intersection + self.eps) / (denominator + self.eps)

        return dice_loss


class EWDLMulticlass(base.Loss):
    """
    Error-Weighted Dice Loss (EWDL) for multiclass segmentation.

    A simplified approach that weights pixels based only on correctness:
    - Correct predictions: weight = 1.0
    - Wrong predictions: weight = wrong_penalty (α)

    This removes the complexity of confidence thresholds, leaving only one
    hyperparameter to tune: the penalty for errors.

    Args:
        eps: Small constant for numerical stability (default: 1.0)
        wrong_penalty: Weight multiplier for incorrect predictions (default: 10.0)
        activation: Activation function ('softmax' or None)
        ignore_index: Class index to ignore in loss computation
    """
    __name__ = "ewdl_multiclass_loss"

    def __init__(self,
                 eps=1.0,
                 wrong_penalty=10.0,
                 activation="softmax",
                 ignore_index=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.eps = eps
        self.wrong_penalty = wrong_penalty
        self.activation = Activation(activation)
        self.ignore_index = ignore_index

    def forward(self, y_pr, y_gt):
        """
        Args:
            y_pr: (B, C, H, W) - Model predictions (logits)
            y_gt: (B, H, W) - Ground truth labels (integer values per pixel)
        """
        # Apply activation to obtain probabilities
        y_pr = self.activation(y_pr)  # Shape: (B, C, H, W)

        num_classes = y_pr.shape[1]

        # Create valid mask (exclude ignore_index)
        if self.ignore_index is not None:
            valid_mask = (y_gt != self.ignore_index).float()  # (B, H, W)
        else:
            valid_mask = torch.ones_like(y_gt, dtype=torch.float32)

        # Convert y_gt to one-hot encoding
        y_gt_clamped = y_gt.clone()
        if self.ignore_index is not None:
            y_gt_clamped[y_gt == self.ignore_index] = 0  # Temporary for scatter

        y_gt_onehot = torch.zeros_like(y_pr)  # (B, C, H, W)
        y_gt_onehot.scatter_(1, y_gt_clamped.unsqueeze(1), 1)

        # Determine correctness: does predicted class match ground truth?
        predicted_class = torch.argmax(y_pr, dim=1)  # (B, H, W)
        is_correct = (predicted_class == y_gt)  # (B, H, W)

        # Assign weights: 1.0 for correct, wrong_penalty for wrong
        pixel_weights = torch.ones_like(y_gt, dtype=torch.float32)  # (B, H, W)
        pixel_weights[~is_correct] = self.wrong_penalty

        # Apply valid_mask
        pixel_weights = pixel_weights * valid_mask

        # Normalize weights
        pixel_weights = pixel_weights / (pixel_weights.sum() + 1e-8) * valid_mask.sum()

        # Broadcast to (B, C, H, W)
        weights = pixel_weights.unsqueeze(1).expand_as(y_pr)

        # Apply valid_mask to y_gt_onehot
        y_gt_onehot = y_gt_onehot * valid_mask.unsqueeze(1)

        # Calculate weighted Dice loss per class
        intersection = (weights * y_pr * y_gt_onehot).sum(dim=(0, 2, 3))  # (C,)
        denominator = (weights * (y_pr + y_gt_onehot)).sum(dim=(0, 2, 3))  # (C,)

        dice_per_class = 1 - (2 * intersection + self.eps) / (denominator + self.eps)

        # Average across classes
        dice_loss = dice_per_class.mean()

        return dice_loss
