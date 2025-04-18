import pandas as pd
import numpy as np
import os
import pickle
import sys
import matplotlib.pyplot as plt
import cv2
import re
import concurrent.futures
from skimage import morphology, feature
from config import SEGMENTATION_DEFAULTS
from file_io import readSingleTiff

def findImagesRecursive(folder_path, file_code='.tif', use_img_nums=False, img_num_sep="_", parent_folders=[], **kwargs):
    """Generator that returns images along with parent folders in hemocytometer or plate"""
    img_files = sorted([file for file in os.scandir(folder_path) if re.search(file_code, file.name)], key=lambda f: f.name)
    
    i = 1
    for img_file in img_files:
        if use_img_nums:
            yield tuple(parent_folders + [img_file.name.split(img_num_sep)[0]]), img_file
        else:
            yield tuple(parent_folders + [str(i)]), img_file
            i += 1
                
    if not img_files:
        subfolders = sorted([subfolder for subfolder in os.scandir(folder_path) if subfolder.is_dir()], key=lambda f: f.name)
        
        for subfolder in subfolders:
            yield from findImagesRecursive(subfolder.path, file_code, use_img_nums, img_num_sep, parent_folders + [subfolder.name])

def readPlate(folder_path, io_settings={}, seg_settings={}, rel_paths=True, index_names=None, max_threads=None, **kwargs):
    """Read and process all images in a plate directory"""
    plate_data = pd.DataFrame(dtype='object')
    
    index_tuples, img_files = zip(*[img for img in findImagesRecursive(folder_path, **io_settings)])
    
    if rel_paths:
        paths = [os.path.join(*index_tuple[:-1], img_file.name) for index_tuple, img_file in zip(index_tuples, img_files)]
    else:
        paths = [img_file.path for img_file in img_files]

    params_list = [(img_file.path, seg_settings) for img_file in img_files]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        counts, areas, maximas = zip(*executor.map(countImageInThread, params_list))
        
    plate_data['Nuclei'] = counts
    plate_data['Area (mm2)'] = areas
    plate_data['Path'] = paths
    plate_data['Maxima'] = maximas
    
    # Set index names based on data structure
    if index_names is None:
        index_len = len(index_tuples[0])
        if index_len == 2:  # Hemocytometer
            index_names = ['Well', 'Image']
        elif index_len == 3:  # Multiple hemocytometers
            index_names = ['Slide', 'Well', 'Image']
        else:   
            index_names = [('Subfolder %d' % i) for i in range(1, index_len)] + ['Image']
        
    plate_data.index = pd.MultiIndex.from_tuples(index_tuples, names=index_names)
    return plate_data

# Functions from count.py
def countImageInThread(params):
    img_path, seg_settings = params[0], params[1]
    img, scale = readSingleTiff(img_path)
    maxima = countNuclei(img, scale, **seg_settings)
    count = np.shape(maxima)[0]
    mm_per_pixel = 1 / (scale*1000)
    area = np.size(img) * mm_per_pixel**2
    return count, area, maxima

# scale and final_scale should be provided in pixels/µm.
# threshold_abs is a number between 0 and 1.
# min_distance may need some refining
# Some tasks reassiged to OpenCV because it is far more efficient
def countNuclei(img, scale=1, template_rad=4.4, final_scale=2, min_distance=2, threshold_abs=0.3, **kwargs):
    
    # Adjusting for image scale
    if final_scale > scale: # There would be absolutely no reason to do this ever
        final_scale = scale
    
    downscale = final_scale/scale
    template_rad = template_rad * final_scale
    min_distance = round(min_distance * final_scale) # must be an integer

    # Downscaling image to final_scale pixels/µm (OpenCV)
    # Must be uint8 in order for template matching to work
    print(img.shape)
    img_downscaled = np.asarray(cv2.normalize(cv2.resize(img, (0, 0), fx=downscale, fy=downscale), None, 0, 255, cv2.NORM_MINMAX), dtype='uint8')
    
    # Template matching (OpenCV)
    template = morphology.disk(template_rad) # OpenCV's ellipse generator works terribly
    temp_match_result =  cv2.matchTemplate(img_downscaled, template, method=cv2.TM_CCOEFF_NORMED)
    
    # Padding template with zeros to match size of original image (OpenCV)
    vert_diff, horiz_diff = np.subtract(np.shape(img_downscaled), np.shape(temp_match_result))
    top_diff = bottom_diff = int(np.floor(vert_diff / 2))
    left_diff = right_diff = int(np.floor(horiz_diff / 2))
    
    if vert_diff % 2 != 0: # Sometimes due to rounding, the size difference is odd
        bottom_diff += 1
        
    if horiz_diff % 2 != 0:
        right_diff += 1
    
    temp_match_result = cv2.copyMakeBorder(temp_match_result, top_diff, bottom_diff, left_diff, right_diff, cv2.BORDER_CONSTANT, -1)
    
    # Thresholding to limit the search area for maxima (OpenCV)
    _, binary = cv2.threshold(img_downscaled, 0, 1, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    binary = np.multiply(binary, temp_match_result != -1) # Don't use the padded area of the template
    
    # Finding maxima (scikit-image. Now the slowest step, but couldn't find a replacement from OpenCV)
    maxima = feature.peak_local_max(temp_match_result, min_distance=min_distance, threshold_abs=threshold_abs, labels=binary)
    
    # Adjust for resizing of image, output maxima
    return np.round(np.divide(maxima, downscale))

def cropImg(img, zoom_percentage):
    """Crop an image for display based on zoom percentage"""
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

# Processing functions
def count_single_image(img_path, seg_params=None):
    """Count nuclei in a single image file"""
    img, scale = readSingleTiff(img_path)
    
    # Use default parameters if none provided
    if seg_params is None:
        seg_params = SEGMENTATION_DEFAULTS
        
    maxima = countNuclei(img, scale, **seg_params)
    return img, scale, maxima

def count_plate_images(plate_dir, io_dict, seg_dict, **plate_kwargs):
    """Process all images in a plate directory"""
    plate = readPlate(plate_dir, io_dict, seg_dict, **plate_kwargs)
    
    # Calculate concentrations
    plate.insert(2, 'Nuclei/µL', plate['Nuclei'] * plate_kwargs['well_area'] / 
                plate['Area (mm2)'] / plate_kwargs['well_vol'] * plate_kwargs['dil_factor'])
    return plate

def recalculate_plate_concentrations(plate, plate_dict):
    """Recalculate plate concentrations based on updated settings"""
    plate['Nuclei/µL'] = plate['Nuclei'] / plate['Area (mm2)'] * plate_dict['well_area'] / \
                         plate_dict['well_vol'] * plate_dict['dil_factor']
    return plate

def calculate_dilutions(plate_concs, desired_conc, desired_vol):
    """Calculate dilutions for desired concentration and volume"""
    dil_df = pd.DataFrame()
    dil_df['Nuclei/µL'] = plate_concs.iloc[:, -1]  # mean if there is one, no mean if there is not
    dil_df['µL sample'] = desired_conc / dil_df['Nuclei/µL'] * desired_vol
    dil_df['µL buffer'] = desired_vol - dil_df['µL sample']
    return dil_df

def format_plate_data(plate, use_img_nums):
    """Format plate data for display"""
    if use_img_nums:
        plate_counts = plate[['Nuclei']].copy()
        plate_concs = plate[['Nuclei/µL']].copy()
    else:
        plate_counts = plate['Nuclei'].unstack()
        plate_counts['Mean'] = plate_counts.mean(axis=1)

        plate_concs = plate['Nuclei/µL'].unstack()
        plate_concs['Mean'] = plate_concs.mean(axis=1)
    
    return plate_counts, plate_concs 