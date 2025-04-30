# NucleiCounter

A Python tool for automatic nuclei detection and counting in microscopy images.

## Overview

NucleiCounter is a software tool designed to streamline the process of counting DAPI-labeled cells or nuclei in microscopy images from hemocytometers or cell counting slides. It provides both a command-line interface and a graphical user interface for analyzing single images or entire plates of images. The software supports automated calculation of nuclei concentrations and can calculate dilutions as well.

The core of NucleiCounter is that it assumes nuclei are roughly circular, and performs the following steps:
* Downsizing of the input image (optional, to save on computational costs).
* Template matching of a circle to the image
* Finding peaks in the quality of template matching (which should occur at the center of the nucleus)
The result is that it can accurately count DAPI-stained nuclei. Concentrations can then be calculated if the chamber area and volume are known. TIFF metadata in input images is used to determine image scale for calculating concentrations.

<img src="docs/example_image.png" width="45%" alt="Example of nuclei detection" /> <img src="docs/example_segmented_image.png" width="45%" alt="Detected nuclei" />

NucleiCounter is intended to be used through its GUI (see below), which provides an easy way to use the software and access to dilution counting. 

![GUI](docs/nucleicounter_gui.png)

NucleiCounter can also be called from the command line or used as a Python library if desired for custom applications.

## Installation

NucleiCounter is cross-platform and can be installed on Mac, PC or Linux, as long as Python and Pip are available.

```bash
# Clone the repository
git clone https://github.com/aepstein96/nuclei-counter.git
cd nuclei-counter

# Install the package in development mode (recommended to do in a virtual environment)
pip install -e .
```

### Dependencies

- Python ≥ 3.8
- numpy
- pandas
- matplotlib
- scikit-image
- opencv-python
- tifffile
- tk (for GUI)

## Usage

NucleiCounter can be used with the following commands (run from the nuclei-counter folder in which it is installed)

### Launch the GUI (intended way to use the software)

```bash
python -m nucleicounter gui
```

### Process a single image, outputting a single image with counts

```bash
python -m nucleicounter image -i /path/to/image.tif -o /path/to/output.png
```
Note: output path is optional; if not provided, it will save the output in the input directory.

### Process all images in a plate directory, also outputting .csv results

```bash
python -m nucleicounter plate -i /path/to/plate_directory -o /path/to/output_directory
```
Note: output path is optional; if not provided, it will save the output in the input directory.

## Settings

NucleiCounter has several configurable parameters for segmentation, I/O, display, and plate analysis, which are defined in config.py. Defaults can be changed there. At the moment, the command line does not support changing the defaults, but all parameters can be edited when using the GUI.

### Segmentation settings

- `final_scale`: Resolution to scale down to (pixels/µm). Set to 0 to use input scale.
- `template_rad`: Template radius (µm)
- `min_distance`: Minimum distance between nuclei (µm)
- `threshold_abs`: Peak threshold (0-1)

### I/O settings

- `file_code`: Image file code (default: .tif)
- `image_labels`: Numbering method (options: nums_from_file, image_name, arbitrary_nums)
- `img_num_sep`: Image number separator for nums_from_file (default: '_')
- `use_multithreading`: Whether to use multithreading (default: False). *Note: this may or may not work on your system.*
- `max_threads`: Maximum number of threads (0 = all)
- `max_depth`: Maximum depth of subfolders to search (default: 3)

### Display settings

- `marker_size`: Nuclei marker size in pixels (default: 1)
- `zoom`: Zoom percentage (default: 100%)
- `width`: Figure width (default: 6)
- `height`: Figure height (default: 6)
- `dpi`: Figure DPI (default: 180)
- `autosave`: Automatically save results (default: True)

### Plate settings (for concentration calculation)

- `rel_paths`: Save relative file paths (default: True)
- `well_area`: Well area (mm²)
- `well_vol`: Well volume (µL)
- `dil_factor`: Dilution factor

### Dilution settings

- `desired_conc`: Desired concentration (nuclei/µL) (default: 250)
- `desired_vol`: Desired volume (µL) (default: 400)

### Plate presets

The software includes presets for common setups:
- `Hemocytometer`: Well area = 1 mm², well volume = 0.1 µL, dilution factor = 2

## Output

The software saves results in several formats:

- Pickle files (.pickle) containing raw data for further analysis
- CSV file with nuclei counts, concentrations, and dilution calculations
- Optional segmented images showing detected nuclei

## License: GPL-3 
