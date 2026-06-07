import numpy as np
import torch
import pandas as pd
from sklearn.metrics import confusion_matrix

# Helper function to calculate confusion matrix
def get_confusion_matrix(predictions, labels, num_classes):
    """
    Calculate the confusion matrix for the predictions and labels.
    
    Parameters:
        predictions (torch.Tensor): Predicted classes or thresholds.
        labels (torch.Tensor): Ground truth labels.
        num_classes (int): Number of classes.
    
    Returns:
        np.ndarray: Confusion matrix of shape (num_classes, num_classes).
    """
    pred_flat = predictions.view(-1).cpu().numpy()
    lab_flat = labels.view(-1).cpu().numpy()
    
    return confusion_matrix(lab_flat, pred_flat, labels=range(num_classes))


# Binary Metrics Calculation
def calculate_binary_metrics(conf_matrix):
    """
    Calculate binary metrics (accuracy, precision, recall, F1-score, IoU) from the confusion matrix.
    
    Parameters:
        conf_matrix (np.ndarray): Confusion matrix of shape (2, 2).
    
    Returns:
        dict: Dictionary of calculated metrics.
    """
    TN, FP, FN, TP = conf_matrix.ravel()
    
    accuracy = (TP + TN) / (TP + TN + FP + FN)
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    iou = TP / (TP + FP + FN) if (TP + FP + FN) > 0 else 0
    
    return {
        'accuracy': round(accuracy * 100, 2),
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1_score': round(f1_score * 100, 2),
        'iou': round(iou * 100, 2)
    }


# Multiclass Metrics Calculation
def calculate_multiclass_metrics(conf_matrix, num_classes):
    """
    Calculate mIoU, fwIoU, accuracy, macro precision, recall, F1-score for multiclass problems.
    Also calculates per-class (micro) metrics.
    
    Parameters:
        conf_matrix (np.ndarray): Confusion matrix of shape (num_classes, num_classes).
        num_classes (int): Number of classes.
    
    Returns:
        dict: Dictionary containing macro and micro metrics.
    """
    ious, precisions, recalls, f1_scores = [], [], [], []
    for i in range(num_classes):
        TP = conf_matrix[i, i]
        FP = np.sum(conf_matrix[:, i]) - TP
        FN = np.sum(conf_matrix[i, :]) - TP
        TN = np.sum(conf_matrix) - (TP + FP + FN)

        IoU = TP / float(TP + FP + FN) if (TP + FP + FN) > 0 else 0
        precision = TP / (TP + FP) if (TP + FP) > 0 else 0
        recall = TP / (TP + FN) if (TP + FN) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        ious.append(IoU)
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1_score)

    # Macro Metrics (averaged over classes)
    mIoU = np.mean(ious)
    fwIoU = np.sum(np.sum(conf_matrix, axis=1) / np.sum(conf_matrix) * ious)
    macro_precision = np.mean(precisions)
    macro_recall = np.mean(recalls)
    macro_f1_score = np.mean(f1_scores)
    
    # Accuracy calculation
    accuracy = np.trace(conf_matrix) / np.sum(conf_matrix)

    # Convert metrics to percentages for macro metrics
    macro_results = {
        'accuracy': round(accuracy * 100, 2),
        'mIoU': round(mIoU * 100, 2),
        'fwmIoU': round(fwIoU * 100, 2),
        'precision': round(macro_precision * 100, 2),
        'recall': round(macro_recall * 100, 2),
        'f_score': round(macro_f1_score * 100, 2)
    }

    # Micro Metrics (per class)
    micro_metrics = {
        'iou': ious,
        'precision': precisions,
        'recall': recalls,
        'f1_score': f1_scores
    }
    
    return macro_results, micro_metrics


# Binary Metrics Display Function
def display_binary_metrics(model, data_loader, device, threshold=0.5,
                           show_accuracy=True, show_precision=True, show_recall=True, show_f1_score=True, show_iou=True):
    """
    Evaluate a binary classification model and display selected metrics.
    
    Parameters:
        model (torch.nn.Module): The PyTorch model to evaluate.
        data_loader (torch.utils.data.DataLoader): DataLoader for the dataset.
        device (torch.device): Device to perform calculations (e.g., 'cuda' or 'cpu').
        threshold (float): Threshold for binary classification. Default is 0.5.
        show_accuracy (bool): Whether to display accuracy. Default is True.
        show_precision (bool): Whether to display precision. Default is True.
        show_recall (bool): Whether to display recall. Default is True.
        show_f1_score (bool): Whether to display F1-score. Default is True.
        show_iou (bool): Whether to display IoU. Default is True.
    
    Returns:
        pd.DataFrame: A DataFrame containing the selected binary metrics.
    """
    model.eval()
    total_conf_matrix = np.zeros((2, 2), dtype=np.int64)  # Binary case

    with torch.no_grad():
        for inp, lab in data_loader:
            inp, lab = inp.to(device), lab.to(device)
            outputs = model(inp)
            
            # Binary: Apply threshold
            predictions = (torch.sigmoid(outputs) > threshold).long()
            
            # Update confusion matrix
            total_conf_matrix += get_confusion_matrix(predictions, lab, num_classes=2)
    
    # Calculate binary metrics
    binary_metrics = calculate_binary_metrics(total_conf_matrix)
    
    # Filter metrics based on flags
    filtered_metrics = {}
    if show_accuracy:
        filtered_metrics['accuracy'] = binary_metrics['accuracy']
    if show_precision:
        filtered_metrics['precision'] = binary_metrics['precision']
    if show_recall:
        filtered_metrics['recall'] = binary_metrics['recall']
    if show_f1_score:
        filtered_metrics['f1_score'] = binary_metrics['f1_score']
    if show_iou:
        filtered_metrics['iou'] = binary_metrics['iou']

    # Return the filtered metrics in a DataFrame
    return pd.DataFrame([filtered_metrics])


# Multiclass Metrics Display Function with Improved Visualization
def display_multiclass_metrics(model, data_loader, device, num_classes=4, threshold=0.5, 
                               show_iou=True, show_precision=True, show_recall=True, show_f1_score=True):
    """
    Evaluate a multiclass classification model and display selected metrics in a structured DataFrame.
    
    Parameters:
        model (torch.nn.Module): The PyTorch model to evaluate.
        data_loader (torch.utils.data.DataLoader): DataLoader for the dataset.
        device (torch.device): Device to perform calculations (e.g., 'cuda' or 'cpu').
        num_classes (int): The number of classes in the dataset.
        threshold (float): Threshold for binary classification. Default is 0.5.
        show_iou (bool): Whether to display IoU for each class. Default is True.
        show_precision (bool): Whether to display Precision for each class. Default is True.
        show_recall (bool): Whether to display Recall for each class. Default is True.
        show_f1_score (bool): Whether to display F1-score for each class. Default is True.
    
    Returns:
        tuple: A tuple containing macro metrics DataFrame and a combined micro metrics DataFrame.
    """
    model.eval()
    total_conf_matrix = np.zeros((num_classes, num_classes), dtype=np.int64)

    with torch.no_grad():
        for inp, lab in data_loader:
            inp, lab = inp.to(device), lab.to(device)
            outputs = model(inp)
            
            # Multiclass: Use argmax
            _, predictions = torch.max(outputs, dim=1)
            
            # Update confusion matrix
            total_conf_matrix += get_confusion_matrix(predictions, lab, num_classes)
    
    # Calculate metrics
    macro_metrics, micro_metrics = calculate_multiclass_metrics(total_conf_matrix, num_classes)
    
    # Macro metrics in one DataFrame
    macro_df = pd.DataFrame([macro_metrics])
    
    # Create a combined DataFrame for micro metrics
    micro_df = pd.DataFrame(index=[f'class_{i}' for i in range(num_classes)])

    if show_iou:
        micro_df['IoU'] = [round(value * 100, 2) for value in micro_metrics['iou']]

    if show_precision:
        micro_df['Precision'] = [round(value * 100, 2) for value in micro_metrics['precision']]

    if show_recall:
        micro_df['Recall'] = [round(value * 100, 2) for value in micro_metrics['recall']]

    if show_f1_score:
        micro_df['F1-Score'] = [round(value * 100, 2) for value in micro_metrics['f1_score']]

    return macro_df, micro_df

