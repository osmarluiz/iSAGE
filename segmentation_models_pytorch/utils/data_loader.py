import os
from glob import glob
import numpy as np
import imageio

def get_dataset_paths(base_dir, split='train', img_ext='tiff', mask_ext='png', img_subdir='img', mask_subdir='label'):
    """
    Get image and mask paths for a given dataset split.
    
    Parameters:
        base_dir (str): The base directory where the dataset is stored.
        split (str): The dataset split ('train', 'val', 'test').
        img_ext (str): The file extension for the image files (default is 'tiff').
        mask_ext (str): The file extension for the mask files (default is 'png').
        img_subdir (str): The subdirectory where the images are located (default is 'img').
        mask_subdir (str): The subdirectory where the masks are located (default is 'label').

    Returns:
        tuple: (list of image paths, list of mask paths)
    """
    img_paths = glob(os.path.join(base_dir, split, img_subdir, f"*.{img_ext}"))
    mask_paths = glob(os.path.join(base_dir, split, mask_subdir, f"*.{mask_ext}"))
    return img_paths, mask_paths


def calculate_class_weights(train_masks):
    """
    Function to calculate class weights based on pixel distribution in mask images.
    
    Args:
        train_masks (list): List of file paths to the mask images.
        
    Returns:
        weights (list): List of class weights calculated from the pixel distributions.
    """
    # Dictionary to store pixel counts for each class
    class_counts = {}

    for msk_img in train_masks:
        actual_image = imageio.imread(msk_img)
        
        # Get unique classes and their counts in the current image
        unique_classes, counts = np.unique(actual_image, return_counts=True)
        
        for cls, count in zip(unique_classes, counts):
            if cls in class_counts:
                class_counts[cls] += count
            else:
                class_counts[cls] = count

    # Get the maximum count for normalization
    max_val = max(class_counts.values())
    
    # Calculate the weights for each class
    weights = {cls: round(max_val / count, 1) for cls, count in class_counts.items()}
    
    return weights