import os
import argparse
from nucleicounter.processing import countImage, readPlate, formatPlateData
from nucleicounter.file_io import saveResults
from nucleicounter.visualization import displayImage
from nucleicounter.gui import MainWindow

# Run GUI
def gui(args):
    app = MainWindow()
    app.mainloop()

# Count single image
def processImage(args):
    if args.output_path is None:
        img_name = os.path.basename(args.image_path)
        args.output_path = os.path.join(os.path.dirname(args.image_path), "%s_segmented.png" % img_name)
    
    _, _, maxima = countImage(args.image_path)
    fig = displayImage(args.image_path, maxima)
    fig.savefig(args.output_path)

# Count images from plate
def processPlate(args):
    if args.output_dir is None:
        args.output_dir = args.input_dir
    
    plate = readPlate(args.input_dir)
    plate_counts, plate_concs = formatPlateData(plate)
    saveResults(args.output_dir, plate, plate_counts, plate_concs)


if __name__ == "__main__":
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Nuclei Counter')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create the parser for the "gui" command
    gui_parser = subparsers.add_parser('gui', help='Run the graphical user interface')
    gui_parser.set_defaults(func=gui)
    
    # Create the parser for the "count-image" command
    image_parser = subparsers.add_parser('image', help='Count nuclei in a single image')
    image_parser.add_argument('-i', '--image_path', type=str, required=True, help='Path to image file')
    image_parser.add_argument('-o', '--output_path', type=str, help='Segmented image save path', default=None)
    image_parser.set_defaults(func=processImage)
    
    # Create the parser for the "count-plate" command
    plate_parser = subparsers.add_parser('plate', help='Count nuclei in a plate directory')
    plate_parser.add_argument('-i', '--input_dir', type=str, required=True, help='Directory containing plate images')
    plate_parser.add_argument('-o', '--output_dir', type=str, help='Plate save directory', default=None)
    plate_parser.set_defaults(func=processPlate)
    
    # Parse arguments and execute the appropriate function
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()