import torch
import matplotlib.pyplot as plt
import numpy as np

def visualize_predictions(model, data_loader, device, num_images=5, figsize=(15, 5), binary=False, threshold=0.5):
    """
    Visualize input images, model predictions, and ground truth labels side by side.
    
    Parameters:
        model (torch.nn.Module): Trained model for generating predictions.
        data_loader (torch.utils.data.DataLoader): DataLoader containing validation or test data.
        device (torch.device): Device on which the model and data are running (e.g., 'cuda' or 'cpu').
        num_images (int): Number of images to display. Default is 5.
        figsize (tuple): Size of the figure for displaying images. Default is (15, 5).
        binary (bool): If True, handles binary segmentation. If False, handles multiclass segmentation. Default is False.
        threshold (float): Threshold for binary segmentation. Default is 0.5.
    """
    model.eval()  # Set the model to evaluation mode
    actual_img_count = 0

    # No need for gradient calculations
    with torch.no_grad():
        for inp, lab in data_loader:
            inp, lab = inp.to(device).detach(), lab.to(device).detach()
            pred = model(inp).detach()

            current_batch_size = len(inp)

            for i in range(current_batch_size):
                # Convert input, prediction, and ground truth to numpy arrays for visualization
                lab_unit = lab[i].cpu().numpy()
                inp_unit = np.transpose(inp[i].cpu().numpy(), (1, 2, 0))  # Convert input to (H, W, C) format
                
                # Handling binary and multiclass segmentation
                if binary:
                    # Binary: Apply threshold to convert probabilities into binary mask (0 or 1)
                    pred_img = pred[i].cpu().numpy()[0]  # Single-channel output for binary segmentation
                    pred_img = (pred_img > threshold).astype(np.uint8)  # Threshold to get binary mask
                else:
                    # Multiclass: Use argmax to get the class with the highest probability
                    pred_img = pred[i].cpu().numpy()
                    pred_img = np.argmax(pred_img, 0)

                # Plot the original image, prediction, and ground truth
                f, ax = plt.subplots(1, 3, figsize=figsize)
                
                # Visualization
                ax[0].imshow(inp_unit[:, :, 0])  # Assuming the input is normalized, visualize only one channel
                ax[1].imshow(pred_img)
                ax[2].imshow(lab_unit)

                # Set titles
                ax[0].set_title(f'Original Image | {actual_img_count + 1}')
                ax[1].set_title(f'Prediction | {actual_img_count + 1}')
                ax[2].set_title(f'Ground Truth | {actual_img_count + 1}')

                # Remove axis ticks
                for a in ax:
                    a.set_xticks([])
                    a.set_yticks([])

                plt.tight_layout()
                plt.show()

                actual_img_count += 1

                # Stop after displaying the specified number of images
                if actual_img_count >= num_images:
                    return