import os
import pickle
import pandas as pd
import tifffile as tf
import re

# Recursively find all images in a folder and return their paths/positions
def findImagesRecursive(folder_path, file_code='.tif', image_labels='nums_from_file', img_num_sep="_", parent_folders=[], max_depth=3, **kwargs):
    img_files = sorted([file for file in os.scandir(folder_path) if re.search(file_code, file.name)], key=lambda f: f.name)
    
    i = 1
    for img_file in img_files:
        if image_labels == 'nums_from_file': # Extract numbers from file name
            label = img_file.name.split(img_num_sep)[0]
        elif image_labels == 'image_name': # Use file name without extension
            label = os.path.splitext(img_file.name)[0]
        elif image_labels == 'arbitrary_nums': # Use arbitrary numbers
            label = str(i)
        
        yield tuple(parent_folders + [label]), img_file
        i += 1
                
    if not img_files and max_depth > 0:
        subfolders = sorted([subfolder for subfolder in os.scandir(folder_path) if subfolder.is_dir()], key=lambda f: f.name)
        
        for subfolder in subfolders:
            yield from findImagesRecursive(subfolder.path, file_code, image_labels, img_num_sep, 
                                         parent_folders + [subfolder.name], max_depth - 1)

# Read a TIFF image and return image data and scale
def readSingleTiff(img_path):
    with tf.TiffFile(img_path) as tif:
        img = tif.asarray()
        metadata = tif.pages[0].tags
        scale = metadata['XResolution'].value[0]/metadata['XResolution'].value[1]
        units = str(metadata['ResolutionUnit'].value)
        
        if units in ['2', 'RESUNIT.INCH']:
            scale /= 25400
        elif units in ['3', 'RESUNIT.CENTIMETER']:
            scale /= 10000
    
    return img, scale

# Save results to files
def saveResults(plate_dir, plate, plate_counts, plate_concs, settings_dicts=None, dil_df=None):
    plate.to_pickle(os.path.join(plate_dir, "all_data.pickle"))
    
    if settings_dicts is not None:
        pickle.dump(settings_dicts, open(os.path.join(plate_dir, "settings.pickle"), 'wb'))
    
    # Make human-readable csv file
    pd_csv_args = {'encoding':'utf-8', 'lineterminator':'\n'}
    with open(os.path.join(plate_dir, "count_data.csv"), 'w') as f:
        f.write(f"Folder path,{plate_dir}\n\n")
        
        f.write("Nuclei counts\n")
        f.write(plate_counts.to_csv(**pd_csv_args) + "\n")
        f.write("Nuclei/µL\n")
        f.write(plate_concs.to_csv(**pd_csv_args) + "\n")
        
        if dil_df is not None:
            if settings_dicts is not None:
                f.write("Dilution calculations\n")
                for key, val in settings_dicts[3].items():
                    f.write(f"{key},{val}\n")
                
            f.write(dil_df.to_csv(**pd_csv_args) + "\n")
        
        if settings_dicts is not None:
            f.write("Segmentation settings\n")
            for key, val in settings_dicts[0].items():
                f.write(f"{key},{val}\n")
            
            f.write("\nI/O settings\n")
            for key, val in settings_dicts[1].items():
                f.write(f"{key},{val}\n")
                        
            f.write("\nPlate settings\n")
            for key, val in settings_dicts[2].items():
                f.write(f"{key},{val}\n")

# Load previously saved results
def loadResults(plate_dir):
    plate = pd.read_pickle(os.path.join(plate_dir, "all_data.pickle"))
    settings_dicts = pickle.load(open(os.path.join(plate_dir, "settings.pickle"), 'rb'))
    return plate, settings_dicts 