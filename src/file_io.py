import os
import pickle
import pandas as pd
import tifffile as tf

def readSingleTiff(img_path):
    """Read a TIFF image and return image data and scale"""
    with tf.TiffFile(img_path) as tif:
        img = tif.asarray()
        metadata = tif.pages[0].tags
        scale = metadata['XResolution'].value[0]/metadata['XResolution'].value[1]
        units = str(metadata['ResolutionUnit'].value)
        
        if units=="RESUNIT.INCH":
            scale /= 25400
        elif units=="RESUNIT.CENTIMETER":
            scale /= 10000
    
    return img, scale

def save_results(plate_dir, plate, settings_dicts, plate_counts, plate_concs, dil_df=None):
    """Save analysis results to files"""
    plate.to_pickle(os.path.join(plate_dir, "all_data.pickle"))
    pickle.dump(settings_dicts, open(os.path.join(plate_dir, "settings.pickle"), 'wb'))
    
    # Make human-readable csv file
    pd_csv_args = {'encoding':'utf-8', 'line_terminator':'\n'}
    with open(os.path.join(plate_dir, "count_data.csv"), 'w') as f:
        f.write(f"Folder path,{plate_dir}\n\n")
        
        f.write("Nuclei counts\n")
        f.write(plate_counts.to_csv(**pd_csv_args) + "\n")
        f.write("Nuclei/µL\n")
        f.write(plate_concs.to_csv(**pd_csv_args) + "\n")
        
        if dil_df is not None:
            f.write("Dilution calculations\n")
            for key, val in settings_dicts[3].items():
                f.write(f"{key},{val}\n")
                
            f.write(dil_df.to_csv(**pd_csv_args) + "\n")
        
        f.write("Segmentation settings\n")
        for key, val in settings_dicts[0].items():
            f.write(f"{key},{val}\n")
            
        f.write("\nI/O settings\n")
        for key, val in settings_dicts[1].items():
            f.write(f"{key},{val}\n")
                    
        f.write("\nPlate settings\n")
        for key, val in settings_dicts[2].items():
            f.write(f"{key},{val}\n")

def load_results(plate_dir):
    """Load previously saved results"""
    plate = pd.read_pickle(os.path.join(plate_dir, "all_data.pickle"))
    settings_dicts = pickle.load(open(os.path.join(plate_dir, "settings.pickle"), 'rb'))
    return plate, settings_dicts 