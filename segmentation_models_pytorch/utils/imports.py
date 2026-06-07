
# System
import sys
import os

# PyTorch-related imports
import torch
import torch.nn as nn
import torch.utils.data as data
import torch.nn.functional as F
from torch.utils.data import DataLoader

# General Python libraries
import os
import numpy as np
from glob import glob
import random
import imageio

# Torchvision for data transformations
from torchvision import transforms

# Utilities
from collections import defaultdict
from PIL import Image
from tqdm.notebook import tqdm

# Metrics and visualization
from sklearn.metrics import *
import matplotlib.pyplot as plt

# Geometry-related imports
from shapely.geometry import Polygon, shape

# GIS
import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
from rasterio.crs import CRS
from rasterio.features import shapes

# Basic
import math

# models
import segmentation_models_pytorch as smp
from segmentation_models_pytorch.utils.datasets import *
from segmentation_models_pytorch.utils.data_loader import *
from segmentation_models_pytorch.utils.train import *

#dataframes
import pandas as pd

def print_versions():
    """Prints versions of essential libraries for debugging and documentation."""
    print(f"Torch Version: {torch.__version__}")