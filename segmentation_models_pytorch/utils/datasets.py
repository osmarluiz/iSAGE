import torch
from torch.utils import data
import numpy as np
import imageio
import random

class Dataset2D(data.Dataset):
    def __init__(self, image_paths, target_paths, transform=None, transform_label=None):
        """
        Custom dataset to load images and masks with optional transformations.
        
        Parameters:
            image_paths (list): List of file paths to images.
            target_paths (list): List of file paths to masks.
            transform (callable, optional): Transformations to apply to the images.
            transform_label (callable, optional): Transformations to apply to the masks.
        """
        self.image_paths = image_paths
        self.target_paths = target_paths
        self.transform = transform
        self.transform_label = transform_label

    def __getitem__(self, index):
        # Load image and mask
        image = imageio.imread(self.image_paths[index])
        image = np.asarray(image, dtype='float32')
        
        mask = imageio.imread(self.target_paths[index])
        mask = np.asarray(mask, dtype='int64')
        
        # Ensure consistent random transformations for both image and mask
        seed = np.random.randint(2147483647)
        random.seed(seed)
        torch.manual_seed(seed)

        if self.transform:
            image = self.transform(image)
        
        random.seed(seed)
        torch.manual_seed(seed)

        if self.transform_label:
            mask = self.transform_label(mask)
            mask = mask.squeeze(0)  # Squeeze if mask has extra dimension after transformation

        return image, mask

    def __len__(self):
        return len(self.image_paths)
    

class Dataset3D(data.Dataset):
    def __init__(self, image_paths, target_paths, num_channels=4, num_times=12, selected_frames=None, 
                 transform=None, transform_label=None):
        """
        Custom dataset to load multitemporal and multispectral images and masks with optional transformations.
        
        Parameters:
            image_paths (list): List of file paths to images.
            target_paths (list): List of file paths to masks.
            num_channels (int): Number of channels per time frame (default: 4).
            num_times (int): Number of time frames per image (default: 12).
            selected_frames (list, optional): List of time frames to select. If None, use all time frames.
            transform (callable, optional): Transformations to apply to the images.
            transform_label (callable, optional): Transformations to apply to the masks.
        """
        self.image_paths = image_paths
        self.target_paths = target_paths
        self.num_channels = num_channels
        self.num_times = num_times
        self.selected_frames = selected_frames if selected_frames is not None else list(range(num_times))  # Default: all frames
        self.transform = transform
        self.transform_label = transform_label

    def __getitem__(self, index):
        # Load image and mask
        image = imageio.imread(self.image_paths[index])
        image = np.asarray(image, dtype='float32')

        # Reshape the image to (H, W, num_times, num_channels) to separate time frames and channels
        height, width = image.shape[0], image.shape[1]
        image = image.reshape(height, width, self.num_times, self.num_channels)
        
        # Select the specified time frames
        image = image[:, :, self.selected_frames, :]

        # Reshape back to (H, W, selected_frames * num_channels) to flatten the selected frames and channels
        image = image.reshape(height, width, -1)
        
        mask = imageio.imread(self.target_paths[index])
        mask = np.asarray(mask, dtype='int64')
        
        # Ensure consistent random transformations for both image and mask
        seed = np.random.randint(2147483647)
        random.seed(seed)
        torch.manual_seed(seed)

        if self.transform:
            image = self.transform(image)
        
        random.seed(seed)
        torch.manual_seed(seed)

        if self.transform_label:
            mask = self.transform_label(mask)
            mask = mask.squeeze(0)  # Squeeze if mask has extra dimension after transformation

        return image, mask

    def __len__(self):
        return len(self.image_paths)