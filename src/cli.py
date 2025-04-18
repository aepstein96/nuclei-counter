#!/usr/bin/env python
"""
Command-line interface for NucleiCounter
"""
import os
import sys
import argparse
import matplotlib.pyplot as plt
import pandas as pd

from processing import count_single_image, count_plate_images, recalculate_plate_concentrations
from processing import calculate_dilutions, format_plate_data, countNuclei
from visualization import display_image
from file_io import save_results, load_results
from config import (
    SEGMENTATION_DEFAULTS, 
    IO_DEFAULTS, 
    DISPLAY_DEFAULTS, 
    PLATE_DEFAULTS,
    DILUTION_DEFAULTS
)

def parse_args():
    parser = argparse.ArgumentParser(description='Count nuclei in images')
    
    # Add GUI flag
    parser.add_argument('--gui', action='store_true', help='Launch the graphical user interface')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Single image counting
    img_parser = subparsers.add_parser('count-image', help='Count nuclei in a single image')
    img_parser.add_argument('image_path', type=str, help='Path to image file')
    img_parser.add_argument('--save', action='store_true', help='Save the output image')
    img_parser.add_argument('--output-dir', type=str, help='Directory to save output')
    img_parser.add_argument('--scale', type=float, default=SEGMENTATION_DEFAULTS['final_scale'], help='Scale down to (px/µm)')
    img_parser.add_argument('--template-rad', type=float, default=SEGMENTATION_DEFAULTS['template_rad'], help='Template radius (µm)')
    img_parser.add_argument('--min-distance', type=float, default=SEGMENTATION_DEFAULTS['min_distance'], help='Min distance between nuclei (µm)')
    img_parser.add_argument('--threshold', type=float, default=SEGMENTATION_DEFAULTS['threshold_abs'], help='Peak threshold (0-1)')
    
    # Plate counting
    plate_parser = subparsers.add_parser('count-plate', help='Count nuclei in a plate directory')
    plate_parser.add_argument('plate_dir', type=str, help='Directory containing plate images')
    plate_parser.add_argument('--file-code', type=str, default=IO_DEFAULTS['file_code'], help='Image file code')
    plate_parser.add_argument('--use-img-nums', action='store_true', default=IO_DEFAULTS['use_img_nums'], help='Only one image per well')
    plate_parser.add_argument('--img-num-sep', type=str, default=IO_DEFAULTS['img_num_sep'], help='Image number separator')
    plate_parser.add_argument('--well-area', type=float, default=PLATE_DEFAULTS['well_area'], help='Well area (mm^2)')
    plate_parser.add_argument('--well-vol', type=float, default=PLATE_DEFAULTS['well_vol'], help='Well volume (µL)')
    plate_parser.add_argument('--dil-factor', type=float, default=PLATE_DEFAULTS['dil_factor'], help='Dilution factor')
    plate_parser.add_argument('--rel-paths', action='store_true', default=PLATE_DEFAULTS['rel_paths'], help='Save relative file paths')
    plate_parser.add_argument('--desired-conc', type=float, default=DILUTION_DEFAULTS['desired_conc'], help='Desired concentration (nuclei/µL)')
    plate_parser.add_argument('--desired-vol', type=float, default=DILUTION_DEFAULTS['desired_vol'], help='Desired volume (µL)')
    
    # Load saved data
    load_parser = subparsers.add_parser('load', help='Load previously saved data')
    load_parser.add_argument('plate_dir', type=str, help='Directory containing saved data')
    load_parser.add_argument('--calculate-dilutions', action='store_true', help='Calculate dilutions')
    load_parser.add_argument('--desired-conc', type=float, default=DILUTION_DEFAULTS['desired_conc'], help='Desired concentration (nuclei/µL)')
    load_parser.add_argument('--desired-vol', type=float, default=DILUTION_DEFAULTS['desired_vol'], help='Desired volume (µL)')
    
    return parser.parse_args()

def count_image(args):
    """Process a single image"""
    print(f"Counting nuclei in {args.image_path}...")
    
    # Process the image
    img, scale, maxima = count_single_image(args.image_path)
    
    # Override with command-line parameters
    segmentation_params = {
        'final_scale': args.scale,
        'template_rad': args.template_rad,
        'min_distance': args.min_distance,
        'threshold_abs': args.threshold
    }
    
    maxima = countNuclei(img, scale, **segmentation_params)
    
    # Display or save the image
    display_settings = {
        'width': DISPLAY_DEFAULTS['width'],
        'height': DISPLAY_DEFAULTS['height'],
        'dpi': DISPLAY_DEFAULTS['dpi'],
        'marker_size': DISPLAY_DEFAULTS['marker_size'],
        'zoom': DISPLAY_DEFAULTS['zoom']
    }
    
    img_name = os.path.basename(args.image_path)
    fig = display_image(args.image_path, maxima, img_name, display_settings)
    
    if args.save:
        output_dir = args.output_dir if args.output_dir else os.path.dirname(args.image_path)
        output_path = os.path.join(output_dir, f"segmented_{img_name}.png")
        fig.savefig(output_path)
        print(f"Saved to {output_path}")
    else:
        plt.show()
    
    print(f"Found {len(maxima)} nuclei")
    return maxima

def process_plate(args):
    """Process all images in a plate directory"""
    print(f"Reading plate from {args.plate_dir}...")
    
    # Set up parameters
    io_dict = {
        'file_code': args.file_code,
        'use_img_nums': args.use_img_nums,
        'img_num_sep': args.img_num_sep
    }
    
    seg_dict = {
        'final_scale': args.scale if hasattr(args, 'scale') else SEGMENTATION_DEFAULTS['final_scale'],
        'template_rad': args.template_rad if hasattr(args, 'template_rad') else SEGMENTATION_DEFAULTS['template_rad'],
        'min_distance': args.min_distance if hasattr(args, 'min_distance') else SEGMENTATION_DEFAULTS['min_distance'],
        'threshold_abs': args.threshold if hasattr(args, 'threshold') else SEGMENTATION_DEFAULTS['threshold_abs']
    }
    
    plate_dict = {
        'well_area': args.well_area,
        'well_vol': args.well_vol,
        'dil_factor': args.dil_factor,
        'rel_paths': args.rel_paths
    }
    
    # Process plate
    plate = count_plate_images(args.plate_dir, io_dict, seg_dict, **plate_dict)
    
    # Format data
    plate_counts, plate_concs = format_plate_data(plate, io_dict['use_img_nums'])
    
    # Calculate dilutions if requested
    dil_df = None
    dil_dict = {
        'desired_conc': args.desired_conc,
        'desired_vol': args.desired_vol
    }
    
    if hasattr(args, 'calculate_dilutions') and args.calculate_dilutions:
        print("Calculating dilutions...")
        dil_df = calculate_dilutions(plate_concs, args.desired_conc, args.desired_vol)
    
    # Save results
    settings_dicts = [seg_dict, io_dict, plate_dict, dil_dict]
    save_results(args.plate_dir, plate, settings_dicts, plate_counts, plate_concs, dil_df)
    
    # Print report
    print("\nNuclei Counts:")
    print(plate_counts)
    print("\nConcentrations (nuclei/µL):")
    print(plate_concs)
    
    if dil_df is not None:
        print("\nDilution Calculations:")
        print(dil_df)
    
    print(f"\nResults saved to {args.plate_dir}")
    return plate

def load_saved_data(args):
    """Load previously saved data"""
    print(f"Loading data from {args.plate_dir}...")
    
    # Load data
    plate, settings_dicts = load_results(args.plate_dir)
    seg_dict, io_dict, plate_dict, dil_dict = settings_dicts
    
    # Format data
    plate_counts, plate_concs = format_plate_data(plate, io_dict['use_img_nums'])
    
    # Calculate dilutions if requested
    dil_df = None
    if args.calculate_dilutions:
        print("Calculating dilutions...")
        dil_df = calculate_dilutions(plate_concs, args.desired_conc, args.desired_vol)
        
        # Update dil_dict and save
        dil_dict = {
            'desired_conc': args.desired_conc,
            'desired_vol': args.desired_vol
        }
        settings_dicts[3] = dil_dict
        save_results(args.plate_dir, plate, settings_dicts, plate_counts, plate_concs, dil_df)
    
    # Print report
    print("\nNuclei Counts:")
    print(plate_counts)
    print("\nConcentrations (nuclei/µL):")
    print(plate_concs)
    
    if dil_df is not None:
        print("\nDilution Calculations:")
        print(dil_df)
    
    return plate

def launch_gui():
    """Launch the graphical user interface"""
    try:
        from gui import MainWindow
        app = MainWindow()
        app.mainloop()
    except ImportError as e:
        print(f"Error loading GUI: {e}")
        print("Make sure tkinter is installed.")
        sys.exit(1)

def main():
    args = parse_args()
    
    # Check for GUI flag first
    if args.gui:
        launch_gui()
        return
    
    if args.command == 'count-image':
        count_image(args)
    elif args.command == 'count-plate':
        process_plate(args)
    elif args.command == 'load':
        load_saved_data(args)
    else:
        print("Please specify a command. Use --help for options.")
        sys.exit(1)

if __name__ == "__main__":
    main() 