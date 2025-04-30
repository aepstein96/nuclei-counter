# Segmentation settings
SEGMENTATION_SETTINGS = {
    'final_scale': {'default': 2, 'description': 'Scale down to (px/µm). Set to 0 to use input scale.', 'type': 'double'},
    'template_rad': {'default': 4.4, 'description': 'Template radius (µm)', 'type': 'double'},
    'min_distance': {'default': 5, 'description': 'Min distance between nuclei (µm)', 'type': 'double'},
    'threshold_abs': {'default': 0.3, 'description': 'Peak threshold (0-1)', 'type': 'double'}
}

# IO settings
IO_SETTINGS = {
    'file_code': {'default': '.tif', 'description': 'Image file code', 'type': 'string'},
    'image_labels': {'default': 'image_name', 'description': 'Numbering method', 'type': 'list', 'options': ['nums_from_file', 'image_name', 'arbitrary_nums']},
    'img_num_sep': {'default': '_', 'description': 'Image number separator', 'type': 'string'},
    'use_multithreading': {'default': False, 'description': 'Use multithreading', 'type': 'boolean'},
    'max_threads': {'default': 0, 'description': 'Max threads (0 = all)', 'type': 'int'},
    'max_depth': {'default': 3, 'description': 'Max depth of subfolders to search', 'type': 'int'}
}

# Display settings
DISPLAY_SETTINGS = {
    'marker_size': {'default': 1, 'description': 'Nuclei marker size (px)', 'type': 'double'},
    'zoom': {'default': 100, 'description': 'Zoom (%)', 'type': 'int'},
    'width': {'default': 6, 'description': 'Figure width', 'type': 'double'},
    'height': {'default': 6, 'description': 'Figure height', 'type': 'double'},
    'dpi': {'default': 180, 'description': 'Figure DPI', 'type': 'int'},
    'autosave': {'default': True, 'description': 'Autosave results', 'type': 'boolean'}
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

# Plate settings
PLATE_SETTINGS = {
    'rel_paths': {'default': True, 'description': 'Save relative file paths', 'type': 'boolean'},
    'well_area': {'default': 1, 'description': 'Well area (mm^2)', 'type': 'double'},
    'well_vol': {'default': 0.1, 'description': 'Well volume (µL)', 'type': 'double'},
    'dil_factor': {'default': 2, 'description': 'Dilution factor', 'type': 'double'}
}

# Dilution settings
DILUTION_SETTINGS = {
    'desired_conc': {'default': 250, 'description': 'Desired concentration (nuclei/µL)', 'type': 'double'},
    'desired_vol': {'default': 400, 'description': 'Desired volume (µL)', 'type': 'double'}
}

# Defaults for import
SEGMENTATION_DEFAULTS = {k: v['default'] for k, v in SEGMENTATION_SETTINGS.items()}
IO_DEFAULTS = {k: v['default'] for k, v in IO_SETTINGS.items()}
DISPLAY_DEFAULTS = {k: v['default'] for k, v in DISPLAY_SETTINGS.items()}
PLATE_DEFAULTS = {k: v['default'] for k, v in PLATE_SETTINGS.items()}
DILUTION_DEFAULTS = {k: v['default'] for k, v in DILUTION_SETTINGS.items()}