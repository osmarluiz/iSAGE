import os
import math
import rasterio
import torch
from rasterio.merge import merge
from rasterio.io import MemoryFile
from tqdm.notebook import tqdm
from itertools import product
import contextlib  # Add this line to import contextlib
import numpy as np
#import geopandas as gpd
#import fiona
from shapely.geometry import shape
from rasterio.crs import CRS

def read_chunk(img_path, x_start, y_start, x_size, y_size):
    """
    Reads a specified chunk from a geospatial raster file.

    This function opens a raster file, reads a specified window or chunk of the image, and returns both the chunk and its corresponding transform. 

    Parameters:
    - img_path (str): File path to the raster image.
    - x_start (int): The x-coordinate of the starting point of the chunk in pixel units.
    - y_start (int): The y-coordinate of the starting point of the chunk in pixel units.
    - x_size (int): The width of the chunk in pixels.
    - y_size (int): The height of the chunk in pixels.

    Returns:
    - chunk (numpy.ndarray): The extracted image chunk as a numpy array.
    - transform (affine.Affine): The affine transform corresponding to the extracted chunk.
    """
    
    with rasterio.open(img_path) as src:
        chunk = src.read(window=rasterio.windows.Window(x_start, y_start, x_size, y_size)).astype('float32')
        transform = src.window_transform(rasterio.windows.Window(x_start, y_start, x_size, y_size))
    return chunk, transform

def process_batch(batch, model, DEVICE):
    """
    Processes a batch of image chunks using a deep learning model.

    The function converts a batch of image chunks into a tensor, transfers it to the specified device, and then feeds it to the provided model for prediction.

    Parameters:
    - batch (list): A list of image chunks (numpy.ndarray) to be processed.
    - model (torch.nn.Module): The deep learning model to be used for processing.
    - DEVICE (str): The device (e.g., 'cuda' or 'cpu') on which the computation is to be performed.

    Returns:
    - preds (numpy.ndarray): The predictions made by the model for each image chunk in the batch.
    """
    
    with torch.no_grad():
        batch_tensor = torch.from_numpy(np.stack(batch)).to(DEVICE).float()
        preds = model(batch_tensor).cpu().numpy()
    return preds

def sliding_window(chunk, transform, stride, window, model, DEVICE, batch_size=32, threshold=0.5, num_classes=4):
    """
    Applies a sliding window approach for image processing with a deep learning model.

    This function slides a window across an image chunk, processes each windowed section with the model, and compiles the results into a final image.

    Parameters:
    - chunk (numpy.ndarray): The image chunk to be processed.
    - transform (affine.Affine): The affine transform corresponding to the chunk.
    - stride (int): The stride with which the window moves across the image.
    - window (int): The size of the window (assumed to be square).
    - model (torch.nn.Module): The deep learning model used for processing.
    - DEVICE (str): The device (e.g., 'cuda' or 'cpu') on which the computation is to be performed.
    - batch_size (int, optional): The number of windows to process at once. Defaults to 32.
    - threshold (float, optional): The threshold for binary classification. Defaults to 0.5.
    - num_classes (int, optional): The number of classes for classification. Defaults to 1 for binary classification.

    Returns:
    - img_final (numpy.ndarray): The final processed image.
    - transform (affine.Affine): The affine transform corresponding to the final image.
    """
    
    _, height, width = chunk.shape
    
    # Initialize the final image array based on the number of classes
    if num_classes == 1:  # Binary classification
        img_final = np.zeros((height, width), dtype="float32")
        img_cont = np.zeros((height, width), dtype="int32")  # Only needed for binary classification
    else:  # Multiclass classification
        img_final = np.zeros((num_classes, height, width), dtype="float32")
    
    model.eval()
    
    batch = []
    batch_coords = []
    
    for row in tqdm(range(0, height - window + 1, stride), desc='Sliding Window', leave=False):
        for col in range(0, width - window + 1, stride):
            actual_img = chunk[:, row:row+window, col:col+window]
            batch.append(actual_img)
            batch_coords.append((row, col))
            
            if len(batch) == batch_size:
                preds = process_batch(batch, model, DEVICE)
                for (r, c), pred in zip(batch_coords, preds):
                    if num_classes == 1:  # Binary classification
                        img_final[r:r+window, c:c+window] += pred.squeeze()
                        img_cont[r:r+window, c:c+window] += 1
                    else:  # Multiclass classification
                        img_final[:, r:r+window, c:c+window] += pred
                batch.clear()
                batch_coords.clear()
    
    if batch:
        preds = process_batch(batch, model, DEVICE)
        for (r, c), pred in zip(batch_coords, preds):
            if num_classes == 1:  # Binary classification
                img_final[r:r+window, c:c+window] += pred.squeeze()
                img_cont[r:r+window, c:c+window] += 1
            else:  # Multiclass classification
                img_final[:, r:r+window, c:c+window] += pred
    
    # Normalize and threshold or argmax depending on the number of classes
    if num_classes == 1:  # Binary classification
        img_final = np.where(img_final / img_cont > threshold, 1, 0)
    else:  # Multiclass classification
        img_final = np.argmax(img_final, axis=0)
        
    img_final = img_final.astype(np.uint8)
    
    return img_final, transform

def merge_chunks(processed_chunks, meta):
    """
    Merges multiple processed image chunks into a single mosaic image.

    This function takes a list of processed image chunks (with their corresponding transforms) and merges them into a single image, preserving the georeferencing.

    Parameters:
    - processed_chunks (list of tuples): A list where each tuple contains a processed chunk (numpy.ndarray) and its affine transform.
    - meta (dict): Metadata dictionary containing raster information such as driver, count, dtype, etc.

    Returns:
    - mosaic (numpy.ndarray): The merged mosaic image.
    - mosaic_transform (affine.Affine): The affine transform corresponding to the mosaic image.
    """
    
    memfiles = []
    datasets = []

    # First, create MemoryFiles for all chunks
    for data, transform in processed_chunks:
        if data.ndim == 2:
            data = data[np.newaxis, :, :]
        
        meta.update({
            "driver": "GTiff",
            "height": data.shape[1],
            "width": data.shape[2],
            "transform": transform,
            "count": data.shape[0],
            "dtype": data.dtype
        })
        
        memfile = MemoryFile()
        dataset = memfile.open(**meta)
        dataset.write(data)
        memfiles.append(memfile)
        datasets.append(dataset)
    
    # Now merge using the datasets
    with contextlib.ExitStack() as stack:
        # Ensure datasets are kept open for the duration of the merge
        for ds in datasets:
            stack.enter_context(ds)
        
        mosaic, mosaic_transform = merge(datasets)
    
    # Close MemoryFiles
    for memfile in memfiles:
        memfile.close()
    
    return mosaic, mosaic_transform

def process_large_image(img_path, stride, window, model, DEVICE, batch_size=32, chunk_size=(8192, 6528)):
    """
    Processes a large image in chunks using a sliding window approach.

    This function divides a large image into smaller chunks, processes each chunk using a sliding window approach, and then merges the results into a final mosaic image.

    Parameters:
    - img_path (str): Path to the large image file.
    - stride (int): The stride of the sliding window.
    - window (int): The size of the sliding window.
    - model (torch.nn.Module): The deep learning model used for processing.
    - DEVICE (str): The device (e.g., 'cuda' or 'cpu') for computation.
    - batch_size (int, optional): The batch size for processing. Defaults to 128.
    - chunk_size (tuple, optional): The size (width, height) of each chunk. Defaults to (10624, 14464).

    Returns:
    - mosaic (numpy.ndarray): The final processed mosaic image.
    - mosaic_transform (affine.Affine): The affine transform corresponding to the mosaic image.
    """
    
    with rasterio.open(img_path) as src:
        width, height = src.width, src.height
        meta = src.meta.copy()

    num_chunks_x = math.floor(width / chunk_size[0])
    num_chunks_y = math.floor(height / chunk_size[1])

    processed_chunks = []

    total_chunks = num_chunks_x * num_chunks_y
    for i, j in tqdm(product(range(num_chunks_x), range(num_chunks_y)), desc="Processing Chunks", total=total_chunks):
        x_start = i * chunk_size[0]
        y_start = j * chunk_size[1]
        x_end = min(x_start + chunk_size[0], width)
        y_end = min(y_start + chunk_size[1], height)

        chunk, transform = read_chunk(img_path, x_start, y_start, x_end - x_start, y_end - y_start)
        processed_chunk, processed_transform = sliding_window(chunk, transform, stride, window, model, DEVICE, batch_size, num_classes=4)
        processed_chunks.append((processed_chunk, processed_transform))
    
    # Before calling merge_chunks, let's check the processed_chunks
    for idx, (chunk_data, chunk_transform) in enumerate(processed_chunks):
        print(f"Chunk {idx}: Data shape = {chunk_data.shape}, Transform = {chunk_transform}")

    # Now call merge_chunks
    mosaic, mosaic_transform = merge_chunks(processed_chunks, meta)

    return mosaic, mosaic_transform


def save_mosaic(mosaic, mosaic_transform, original_img_path, save_folder, save_name, compression='LZW', dtype='uint8'):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    
    with rasterio.open(original_img_path) as src:
        meta = src.meta.copy()
        crs = src.crs

    # Update metadata for mosaic
    meta.update({
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": mosaic_transform,
        "crs": crs,
        "count": 1,  # Adjust if your mosaic has more bands
        "dtype": dtype,
        "compress": compression
    })

    save_path = os.path.join(save_folder, save_name)
    with rasterio.open(save_path, 'w', **meta) as dst:
        if mosaic.ndim == 2:
            dst.write(mosaic[np.newaxis, :, :], 1)
        else:
            for i in range(mosaic.shape[0]):
                dst.write(mosaic[i, :, :], i+1)