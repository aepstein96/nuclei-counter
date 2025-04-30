import pandas as pd
import numpy as np
import os
import cv2
import concurrent.futures
from skimage import morphology, feature
from .config import SEGMENTATION_DEFAULTS, IO_DEFAULTS, PLATE_DEFAULTS
from .file_io import readSingleTiff, findImagesRecursive

# Read and process all images in a plate directory
def readPlate(folder_path, io_settings=IO_DEFAULTS, seg_settings=SEGMENTATION_DEFAULTS, plate_settings=PLATE_DEFAULTS, index_names=None):
    """Read and process all images in a plate directory"""
    plate_data = pd.DataFrame(dtype='object')
    
    index_tuples, img_files = zip(*[img for img in findImagesRecursive(folder_path, **io_settings)])
    
    if plate_settings['rel_paths']:
        paths = [os.path.join(*index_tuple[:-1], img_file.name) for index_tuple, img_file in zip(index_tuples, img_files)]
    else:
        paths = [img_file.path for img_file in img_files]

    if io_settings['use_multithreading']:
        max_threads = io_settings['max_threads']
        if max_threads > len(img_files) or max_threads < 1: # don't use more threads than images or less than 1 thread
            max_threads = len(img_files)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            counts, areas, maximas = zip(*executor.map(lambda args: countImage(*args), 
                                                     [(img_file.path, seg_settings) for img_file in img_files]))
    else:
        counts, areas, maximas = zip(*[countImage(img_file.path, seg_settings) for img_file in img_files])
        
        
    plate_data['Nuclei'] = counts
    plate_data['Area (mm2)'] = areas
    plate_data['Path'] = paths
    plate_data['Maxima'] = maximas
    
    # Set index names based on data structure
    if index_names is None:
        index_len = len(index_tuples[0])
        if index_len == 1:
            index_names = ['Image']
        elif index_len == 2:  # Hemocytometer
            index_names = ['Well', 'Image']
        elif index_len == 3:  # Multiple hemocytometers
            index_names = ['Slide', 'Well', 'Image']
        else:   
            index_names = [('Subfolder %d' % i) for i in range(1, index_len)] + ['Image']
        
    plate_data.index = pd.MultiIndex.from_tuples(index_tuples, names=index_names)
    
    # Calculate concentrations if plate parameters are provided
    if all(k in plate_settings for k in ['well_area', 'well_vol', 'dil_factor']):
        plate_data.insert(2, 'Nuclei/µL', plate_data['Nuclei'] * plate_settings['well_area'] / 
                         plate_data['Area (mm2)'] / plate_settings['well_vol'] * plate_settings['dil_factor'])
    
    return plate_data


def countImage(img_path, seg_settings=SEGMENTATION_DEFAULTS):
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
    if final_scale > scale or final_scale == 0: # There would be absolutely no reason to do this ever
        print("Not downscaling image, using original scale")
        final_scale = scale
    
    # Use downscale factor to adjust other parameters
    downscale = final_scale/scale
    template_rad = template_rad * final_scale
    min_distance = round(min_distance * final_scale) # must be an integer

    # Calculate new dimensions explicitly
    new_height = int(img.shape[0] * downscale)
    new_width = int(img.shape[1] * downscale)
    
    # Downscaling image to final_scale pixels/µm (OpenCV)
    # Must be uint8 in order for template matching to work
    img_downscaled = np.asarray(cv2.normalize(cv2.resize(img, (new_width, new_height)), None, 0, 255, cv2.NORM_MINMAX), dtype='uint8')
    
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


def recalculatePlateConcentrations(plate, plate_settings=PLATE_DEFAULTS):
    plate['Nuclei/µL'] = plate['Nuclei'] / plate['Area (mm2)'] * plate_settings['well_area'] / \
                         plate_settings['well_vol'] * plate_settings['dil_factor']
    return plate

def calculateDilutions(plate_concs, desired_conc, desired_vol):
    dil_df = pd.DataFrame()
    dil_df['Nuclei/µL'] = plate_concs.iloc[:, -1]  # mean if there is one, no mean if there is not
    dil_df['µL sample'] = desired_conc / dil_df['Nuclei/µL'] * desired_vol
    dil_df['µL buffer'] = desired_vol - dil_df['µL sample']
    return dil_df

# Calculate plate
def formatPlateData(plate):
    # Check if we have a multi-level index
    if isinstance(plate.index, pd.MultiIndex) and len(plate.index.levels) > 1:
        plate_counts = plate['Nuclei'].unstack()
        plate_counts['Mean'] = plate_counts.mean(axis=1)
        plate_concs = plate['Nuclei/µL'].unstack()
        plate_concs['Mean'] = plate_concs.mean(axis=1)
    else:
        # For single-level index, create a DataFrame with a simple index
        plate_counts = pd.DataFrame({'Nuclei': plate['Nuclei'].values}, index=plate.index.get_level_values(-1))
        plate_concs = pd.DataFrame({'Nuclei/µL': plate['Nuclei/µL'].values}, index=plate.index.get_level_values(-1))
    
    return plate_counts, plate_concs 