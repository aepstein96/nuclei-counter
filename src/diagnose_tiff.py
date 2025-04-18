import tifffile as tf
import numpy as np
import sys
import os

def diagnose_tiff(file_path):
    """Diagnose TIFF file properties and metadata"""
    print(f"\nDiagnosing file: {file_path}")
    print("-" * 50)
    
    try:
        with tf.TiffFile(file_path) as tif:
            # Basic file info
            print(f"Number of pages: {len(tif.pages)}")
            print(f"Series count: {len(tif.series)}")
            
            # Image data properties
            img = tif.asarray()
            print("\nImage properties:")
            print(f"Shape: {img.shape}")
            print(f"Data type: {img.dtype}")
            print(f"Min value: {np.min(img)}")
            print(f"Max value: {np.max(img)}")
            
            # Metadata
            print("\nMetadata:")
            page = tif.pages[0]
            for tag in page.tags:
                try:
                    print(f"{tag.name}: {tag.value}")
                except:
                    print(f"{tag.name}: [Error reading value]")
            
            # Resolution info
            print("\nResolution info:")
            if 'XResolution' in page.tags:
                xres = page.tags['XResolution'].value
                print(f"XResolution: {xres}")
            else:
                print("XResolution: Not found")
                
            if 'YResolution' in page.tags:
                yres = page.tags['YResolution'].value
                print(f"YResolution: {yres}")
            else:
                print("YResolution: Not found")
                
            if 'ResolutionUnit' in page.tags:
                res_unit = str(page.tags['ResolutionUnit'].value)
                print(f"ResolutionUnit: {res_unit}")
            else:
                print("ResolutionUnit: Not found")
                
            # Calculate scale
            if 'XResolution' in page.tags and 'YResolution' in page.tags:
                scale = xres[0]/xres[1]
                print(f"\nCalculated scale: {scale}")
                print(f"Scale * 100 (pixels_per_um): {scale * 100}")
                print(f"Downscale factor (1/(scale*100)): {1/(scale*100)}")
            
    except Exception as e:
        print(f"Error analyzing file: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python diagnose_tiff.py <path_to_tiff_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
        
    diagnose_tiff(file_path) 