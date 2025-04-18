import matplotlib.pyplot as plt
import numpy as np
import os
from file_io import readSingleTiff
from processing import cropImg
from config import DISPLAY_DEFAULTS

def display_image(img_path, maxima, img_name=None, display_settings=None):
    """Display an image with nuclei marked and zoom applied"""
    if img_name is None:
        img_name = os.path.basename(img_path)
    
    img, _ = readSingleTiff(img_path)
    
    # Default settings if none provided
    if display_settings is None:
        display_settings = DISPLAY_DEFAULTS
    
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