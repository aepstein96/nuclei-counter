"""
Configuration parameters for NucleiCounter
"""

# Segmentation defaults
SEGMENTATION_DEFAULTS = {
    'final_scale': 2,
    'template_rad': 4.4,
    'min_distance': 5,
    'threshold_abs': 0.3
}

# IO settings defaults
IO_DEFAULTS = {
    'file_code': '.tif',
    'use_img_nums': False,
    'img_num_sep': '_'
}

# Display settings defaults
DISPLAY_DEFAULTS = {
    'marker_size': 1,
    'zoom': 100,
    'width': 6,
    'height': 6,
    'dpi': 180,
    'autosave': True
}

# Plate/hemocytometer presets
PLATE_PRESETS = {
    'Hemocytometer': {
        'well_area': 1,
        'well_vol': 0.1,
        'dil_factor': 2,
        'rel_paths': True
    }
}

# Default plate settings (using Hemocytometer as default)
PLATE_DEFAULTS = PLATE_PRESETS['Hemocytometer'].copy()

# Dilution defaults
DILUTION_DEFAULTS = {
    'desired_conc': 250,
    'desired_vol': 400
} 