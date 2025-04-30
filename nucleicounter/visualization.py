import matplotlib.pyplot as plt
import numpy as np
import os
from .file_io import readSingleTiff
from .config import DISPLAY_DEFAULTS


# Crop image for display based on zoom percentage
def cropImg(img, zoom_percentage):
    h, w = img.shape[0:2]
    
    # Calculate new width and height based on zoom percentage
    new_w = w * 100 / zoom_percentage
    new_h = h * 100 / zoom_percentage
    
    # Calculate the center point
    center_x = w // 2
    center_y = h // 2
    
    # Calculate the new boundaries
    x_min = max(0, int(center_x - new_w // 2))
    x_max = min(w, int(center_x + new_w // 2))
    y_min = max(0, int(center_y - new_h // 2))
    y_max = min(h, int(center_y + new_h // 2))
    
    return (x_min, x_max), (y_min, y_max)

# Display image with maxima points
# Note: the image may be flipped vertically relative to the original image. This should not change any results.
def displayImage(img_path, maxima, img_name=None, display_settings=DISPLAY_DEFAULTS):
    if img_name is None:
        img_name = os.path.basename(img_path)
    
    img, _ = readSingleTiff(img_path)
    
    # Create figure
    img_fig = plt.figure(figsize=(display_settings['width'], display_settings['height']), 
                        dpi=display_settings['dpi'])
    img_fig.suptitle(f'Segmentation of {img_name}: {np.shape(maxima)[0]} nuclei')
    
    # Plot image with maxima points
    img_plot = img_fig.add_subplot(111)
    img_plot.imshow(img)
    img_plot.plot(maxima[:,1], maxima[:,0], '.r', markersize=display_settings['marker_size'])
    
    # Apply zoom
    xlim, ylim = cropImg(img, display_settings['zoom'])
    img_plot.set_xlim(xlim)
    img_plot.set_ylim(ylim)
    
    return img_fig 