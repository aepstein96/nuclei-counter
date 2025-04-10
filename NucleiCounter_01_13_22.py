#!/usr/bin/env python
# coding: utf-8


import matplotlib
matplotlib.use('TkAgg') #Removes the need to actually use FigureCanvasTkAgg or any of this.

from skimage import morphology, feature
import cv2
import matplotlib.pyplot as plt
import os
import numpy as np
import re
import pandas as pd
import tifffile as tf
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import sys
import concurrent.futures
import pickle
import itertools


# Returns scale in pixels/µm
def readSingleTiff(img_path):
    
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


# Generator that returns images along with parent folders in hemocytometer or plate
# Use_img_nums should be True if there is only one img per well (i.e. row numbers are stored in the image)
# extra kwargs catches random extra dictionary args that are not wanted/used
def findImagesRecursive(folder_path, file_code='.tif', use_img_nums = False, img_num_sep="_", parent_folders=[], **kwargs):
    
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
    
    # Eventually the GUI should provide those bsed on the preset
    if index_names is None:
        index_len = len(index_tuples[0])
        if index_len == 2: # Hemocytometer
            index_names = ['Well', 'Image']
        elif index_len == 3: # Multiple hemocytometers; may eventually be a plate
            index_names = ['Slide', 'Well', 'Image']
        else:   
            index_names = [('Subfolder %d' % i) for i in range(1, index_len)] + ['Image']
        
    plate_data.index = pd.MultiIndex.from_tuples(index_tuples, names=index_names)
    return plate_data

# For multi-threaded counting
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
# extra kwargs catches random extra dictionary args that are not wanted/used
def countNuclei(img, scale=1, template_rad=4.4, final_scale=2, min_distance=2, threshold_abs=0.3, **kwargs):
    
    # Adjusting for image scale
    if final_scale > scale: # There would be absolutely no reason to do this ever
        final_scale = scale
    
    downscale = final_scale/scale
    template_rad = template_rad * final_scale
    min_distance = round(min_distance * final_scale) # must be an integer

    # Downscaling image to final_scale pixels/µm (OpenCV)
    # Must be uint8 in order for template matching to work
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
    

def cropImg(img, zoom):
    scale_factor = max(1, zoom/100) # will not use zoom < 100%
    center = np.round(np.divide(img.shape, 2))
    shift = np.round(np.divide(img.shape, 2*scale_factor))
    ylim = [center[0]-shift[0], center[0]+shift[0]]
    xlim = [center[1]-shift[1], center[1]+shift[1]]

    return xlim, ylim


def makeTkVar(master, val):
    if isinstance(val, str):
        return tk.StringVar(master, value=val)
    else:
        return tk.DoubleVar(master, value=val)


def dfFromCSV(csv_string, header=0, **kwargs):
    return pd.read_csv(io.StringIO(csv_string), header=header, **kwargs)


## GUI



class ImageSelector(ttk.Frame):
    def __init__(self, parent, button_command, button_text="Display"):
        ttk.Frame.__init__(self, parent, borderwidth=2)
        self.parent=parent
        self.menu_frame = ttk.Frame(self)
        self.menu_frame.grid(row=0, column=0)
        self.button = ttk.Button(self, text=button_text, command=button_command, state='disabled')
        self.button.grid(row=0, column=1, sticky='se')
       
        self.menus = []
        self.menu_texts = []
        self.menu_col=0
        self.menu_var_list = []
    
    def addMenu(self, name, options, title=None):
        
        if title is None:
            title = name
        
        menu_text = tk.Label(master=self.menu_frame, text=title)
        menu_text.grid(row=0, column=self.menu_col, sticky='nsew')
        self.menu_texts.append(menu_text)
        
        var = tk.StringVar(self)
        setattr(self, name, var)
        self.menu_var_list.append(var)
        
        new_menu = ttk.OptionMenu(self.menu_frame, var, options[0], *options)
        new_menu.grid(row=1, column=self.menu_col, sticky='nsew')
        self.menus.append(new_menu)
        self.menu_col += 1
        
    
    def clearMenus(self):
        for menu in self.menus:
            menu.grid_forget()
            menu.destroy()
        
        self.menus = []
        self.menu_texts = []
        self.menu_var_list = []
        self.menu_col = 0
    
    
    def activate(self):
        self.button['state'] = 'normal'
        
    def getImgLocation(self):
        return tuple([var.get() for var in self.menu_var_list])


class Table(ttk.Frame):
   
    def __init__(self, parent, title, decimals=1, box_width=70):
        ttk.Frame.__init__(self, parent, borderwidth=2)
        self.parent = parent
        self.decimals = decimals
        self.box_width = box_width
        self.title = tk.Label(master=self, text=title)
        self.title.pack()
        self.tree = ttk.Treeview(self)
        self.tree.pack()
        
    def recursiveInsert(self, df, parent=''):
        if isinstance(df.index, pd.MultiIndex):
            for folder in df.index.levels[0]:
                new_parent = self.tree.insert(parent, "end", text=folder, values=['']*len(self.tree['columns']), open=True)
                self.recursiveInsert(df.loc[folder], new_parent)
        else:
            for index, row in df.iterrows():
                self.tree.insert(parent, "end", text=index, values=[round(x, self.decimals) for x in row])
    
    # NEW: heirarchical display
    def display(self, data):
        self.tree.delete(*self.tree.get_children())
        colnames = data.columns.values
        num_cols = len(colnames)
        colnums = list(range(num_cols))
        self.tree["columns"] = colnums
        self.tree.column("#0", minwidth=0, width=200, stretch=False)
        self.tree.heading("#0",text="Sample",anchor=tk.W)
        
        for colnum in colnums:
            self.tree.heading(colnum, text=colnames[colnum])
            self.tree.column(colnum, minwidth=0, width=self.box_width, stretch=False)
            
        self.recursiveInsert(data)
        
        # Refresh tree
        self.tree.event_generate("<<ThemeChanged>>")
        
    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.event_generate("<<ThemeChanged>>")
        

class SettingsBox(ttk.Frame):
    
    def __init__(self, parent, title=None, entry_width=5):
        ttk.Frame.__init__(self, parent, borderwidth=2)
        
        if title is not None:
            tk.Label(master=self, text=title).grid(row=0, column=0, columnspan=2, sticky='n')
            self.row = 1
        else:
            self.row = 0

        self.entry_width = entry_width
        self.dict = {}
        self.presets_dict = {}
                
    def add(self, name, default, text=None, createVar=makeTkVar, kind='Entry', options=None, **kwargs):
        
        # Create TkVar and append to self
        var = createVar(self, default)
        setattr(self, name, var)
        
        self.dict[name] = var
    
        # Grid the label and entry field
        if text is None:
            text = name
        
        ttk.Label(master=self, text=text).grid(row=self.row, column=0, sticky='nw')
        
        if kind == 'Entry':
            new_box = ttk.Entry(master=self, textvariable=var, width=self.entry_width, **kwargs)
            
        elif kind == 'OptionMenu':
            new_box = ttk.OptionMenu(self, var, default, *options, **kwargs)
            
        elif kind == 'Checkbutton':
            new_box = ttk.Checkbutton(self, variable=var, **kwargs)
            
        new_box.grid(row=self.row, column=1, sticky='ne')
        self.row += 1
    
    
    def addButton(self, *args, **kwargs):
        ttk.Button(master=self, *args, **kwargs).grid(row=self.row, column=0, columnspan=2, sticky='nsew')
        self.row += 1
    

    def addPreset(self, name, **preset_dict):
        self.presets_dict[name] = preset_dict
        
    
    def addPresetMenu(self, text='Presets', options=None, default=None, **kwargs):
        
        if options is None:
            options = list(self.presets_dict.keys())
            
        if default is None:
            default = options[0]
        
        ttk.Label(master=self, text=text).grid(row=self.row, column=0, sticky='nw')
        
        var = tk.StringVar(self, default)
        preset_menu = ttk.OptionMenu(self, var, default, *list(self.presets_dict.keys()), command=self.updateFromPreset, **kwargs)
        preset_menu.grid(row=self.row, column=1, sticky='ne')
        self.row += 1
        
    def getDict(self):
        return {name: var.get() for name, var in self.dict.items()}
    
    def setDict(self, in_dict):
        for var, val in in_dict.items():
            self.dict[var].set(val)
            
    def updateFromPreset(self, preset):
        self.setDict(self.presets_dict[preset])

    
# Redirects stdout, stderr to Tkinter text box. Source: https://stackoverflow.com/questions/12351786/how-to-redirect-print-statements-to-tkinter-text-widget
class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, string):
        self.widget.configure(state="normal")
        self.widget.insert("end", string, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")





class MainWindow(tk.Tk):
    
    
    def __init__(self):
        tk.Tk.__init__(self)
        
        # Preserving stdout and stderr from sys so they can be restored when the window is closed
        self.stdout_old = sys.stdout
        self.stderr_old = sys.stderr
        
        self.title('NucleiCounter')
        self.protocol("WM_DELETE_WINDOW", self.onClose)
        
        self.single_img_dir = None
        self.plate_dir = None
        
        self.plate = None
        self.plate_counts = None
        self.plate_concs = None
        self.dil_df = None
        
        self.settings_buttons = ttk.Frame(self)
        
        # Laying out settings
        self.settings = ttk.Frame(self.settings_buttons)
        
        self.seg_settings = SettingsBox(self.settings, 'Segmentation settings')
        self.seg_settings.add('final_scale', 2, 'Scale down to (px/µm)', tk.DoubleVar)
        self.seg_settings.add('template_rad', 4.4, 'Template radius (µm)', tk.DoubleVar)
        self.seg_settings.add('min_distance', 5, 'Min distance between nuclei (µm)', tk.DoubleVar)
        self.seg_settings.add('threshold_abs', 0.3, 'Peak threshold (0-1)', tk.DoubleVar)
        
        self.io_settings = SettingsBox(self.settings, 'Image file settings')
        self.io_settings.add('file_code', '.tif', 'Image file code', tk.StringVar)
        self.io_settings.add('use_img_nums', False, 'Only one image per well', tk.BooleanVar, kind='Checkbutton')
        self.io_settings.add('img_num_sep', '_', 'Image number separator', tk.StringVar)
        
        well_area_urinalysis = 0.111
        well_area_hemo = 1
        well_area_96 = np.pi*(6.42/2)**2
        well_area_384 = 10
        well_area_96_half = np.pi*(4.4958/2)**2
        
        well_vol_urinalysis = 0.011
        well_vol_hemo = 0.1
        
        self.plate_settings = SettingsBox(self.settings, 'Plate/hemocytometer settings')
        self.plate_settings.add('rel_paths', True, 'Save relative file paths', tk.BooleanVar, kind='Checkbutton')
        self.plate_settings.add('well_area', well_area_hemo, 'Well area (mm^2)', tk.DoubleVar)
        self.plate_settings.add('well_vol', well_vol_hemo, 'Well volume (µL)', tk.DoubleVar)
        self.plate_settings.add('dil_factor', 2, 'Dilution factor', tk.DoubleVar)
        
        self.plate_settings.addPreset('Hemocytometer', well_area=well_area_hemo, well_vol=well_vol_hemo)
        self.plate_settings.addPreset('Urinalysis slide', well_area = well_area_urinalysis, well_vol=well_vol_urinalysis)
        self.plate_settings.addPreset('96-well plate', well_area=well_area_96, well_vol=100)
        self.plate_settings.addPreset('384-well plate', well_area=well_area_384, well_vol=30)
        self.plate_settings.addPreset('96-well (half area)', well_area=well_area_96_half, well_vol=50)
        self.plate_settings.addPresetMenu()
        
        self.display_settings = SettingsBox(self.settings, 'Display/save settings')
        self.display_settings.add('marker_size', 1, 'Nuclei marker size (px)', tk.DoubleVar)
        self.display_settings.add('zoom', 100, 'Zoom (%)', tk.IntVar)
        self.display_settings.add('width', 6, 'Figure width', tk.DoubleVar)
        self.display_settings.add('height', 6, 'Figure height', tk.DoubleVar)
        self.display_settings.add('dpi', 180, 'Figure DPI', tk.IntVar)
        self.display_settings.add('autosave', True, 'Autosave results', tk.BooleanVar, kind='Checkbutton')
        
        self.dil_settings = SettingsBox(self.settings, 'Dilution calculation')
        self.dil_settings.add('desired_conc', 250, 'Desired concentration (nuclei/µL)', tk.DoubleVar)
        self.dil_settings.add('desired_vol', 400, 'Desired volume (µL)', tk.DoubleVar)
        
        self.seg_settings.grid(row=0, column=0, sticky='nsew')
        self.plate_settings.grid(row=0, column=1, sticky='nsew')
        self.io_settings.grid(row=1, column=0, sticky='nsew')
        self.display_settings.grid(row=1, column=1, sticky='nsew')
        self.dil_settings.grid(row=2, column=0, sticky='nsew')
        
        # Laying out buttons
        self.buttons = ttk.Frame(self.settings_buttons)
        self.buttons2 = ttk.Frame(self.settings_buttons)
        
        self.count_img = ttk.Button(self.buttons, text='Count single image', command=self.segmentImage)
        self.display_img = ttk.Button(self.buttons, text='Display single image', command=self.displayImage, state='disabled')
        self.count_plate = ttk.Button(self.buttons, text='Count plate/hemocytometer', command=self.countPlate)
        self.save_plate = ttk.Button(self.buttons, text='Manual save', command=self.saveAll, state='disabled')
        self.load_plate = ttk.Button(self.buttons2, text='Load saved data', command=self.loadAll)
        self.redo_tables = ttk.Button(self.buttons2, text='Recalculate plate avgs/concentrations', command=self.recalculatePlate)
        self.calculate_dilutions = ttk.Button(self.buttons2, text='Calculate dilutions', command = self.calculateDilutions, state='disabled')
        #self.save_log = ttk.Button(self.buttons2, text='Save log', command = self.saveLog)
        
        self.count_img.pack(side='left')
        self.display_img.pack(side='left')
        self.count_plate.pack(side='left')
        self.save_plate.pack(side='left')
        self.load_plate.pack(side='left')
        self.redo_tables.pack(side='left')
        self.calculate_dilutions.pack(side='left')
        #self.save_log.pack(side='left')
        
        # Laying out tables  
        
        self.tables = ttk.Frame(self, borderwidth=2)
        
        self.counts_table = Table(self.tables, title='Nuclei counts')
        self.concs_table = Table(self.tables, title='Concentrations (nuclei/µL)')
        self.dilution_table = Table(self.tables, title='Dilution calculations')
        self.image_selector = ImageSelector(self.tables, button_command=self.selectDisplayImage)
        
        self.counts_table.pack()
        self.image_selector.pack()
        self.concs_table.pack()
        self.dilution_table.pack()

        # Laying out message box
        self.log_box = tk.Text(self, height=10, state='disabled', bg='white smoke')
        sys.stdout = TextRedirector(self.log_box, "stdout")
        sys.stderr = TextRedirector(self.log_box, "stderr")
        
        # Assembling window
        self.settings.pack(side='top', anchor='n', fill='none')
        ttk.Label(self.settings_buttons, text="Program log").pack(side='bottom', anchor='w')
        self.buttons2.pack(side='bottom', anchor='s')
        self.buttons.pack(side='bottom', anchor='s')
        

        ttk.Label(self, text="Alexander Epstein, Cao Laboratory, The Rockefeller University").pack(side='bottom', anchor='e')
        ttk.Label(self, text="NucleiCounter (updated 1/13/2022)").pack(side='bottom', anchor='e')
        self.log_box.pack(side='bottom', fill='x')
        
        self.settings_buttons.pack(side='left', fill='y')
        self.tables.pack(side='right')
    
    def calculateDilutions(self):
        print("Calculating dilutions...")
        self.dil_dict = self.dil_settings.getDict()
        
        self.dil_df = pd.DataFrame()
        self.dil_df['Nuclei/µL'] = self.plate_concs.iloc[:, -1] #mean if there is one, no mean if there is not
        self.dil_df['µL sample'] = self.dil_dict['desired_conc'] / self.dil_df['Nuclei/µL'] * self.dil_dict['desired_vol']
        self.dil_df['µL buffer'] = self.dil_dict['desired_vol'] - self.dil_df['µL sample']
        self.dilution_table.display(self.dil_df)
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")
       
  
    def segmentImage(self):
        
        # Get image path and name
        img_path = filedialog.askopenfilename(initialdir=self.single_img_dir, initialfile=self.cur_img_name, title="Select image", filetypes = [("TIFF", "*.tiff *.tif")])

        self.update()
        if not img_path:
            return 0
        
        self.img_path = img_path
        self.single_img_dir, self.cur_img_name = os.path.split(self.img_path)
        print("Counting nuclei in %s..." % self.cur_img_name)
        
        # Run segmentation
        img, scale = readSingleTiff(self.img_path)
        self.maxima = countNuclei(img, scale, **self.seg_settings.getDict())
        
        self.displayImage()
        self.display_img['state'] = 'normal'


    def displayImage(self, img_path=None, maxima=None, img_name=None):
        
        if img_path is None: #workaround for the problem of "self" being undefined if I set img_path=self.img_path above
            img_path = self.img_path
        if maxima is None:
            maxima = self.maxima  
        if img_name is None:
            img_name = self.cur_img_name
        
        print("Displaying %s..." % img_name)
        img, _ = readSingleTiff(img_path)
        img_fig = plt.figure(figsize=(self.display_settings.width.get(),self.display_settings.height.get()), dpi=self.display_settings.dpi.get())
        img_fig.suptitle('Segmentation of %s: %d nuclei' % (img_name, np.shape(maxima)[0]))
        
        img_plot = img_fig.add_subplot(111)
        img_plot.imshow(img)
        img_plot.plot(maxima[:,1], maxima[:,0], '.r', markersize=self.display_settings.marker_size.get())
        
        xlim, ylim = cropImg(img, self.display_settings.zoom.get())
        img_plot.set_xlim(xlim)
        img_plot.set_ylim(ylim)
        img_fig.show()
        
        print("Done")
        
        
    def countPlate(self):
        
        # Get plate path
        plate_dir = filedialog.askdirectory(initialdir=self.plate_dir, title="Select parent folder for plate images")
        
        if not plate_dir:
            return 0
        
        self.plate_dir = plate_dir
        print("Reading %s..." % self.plate_dir)
        self.update()
        
        self.io_dict = self.io_settings.getDict()
        self.seg_dict = self.seg_settings.getDict()
        self.plate_dict = self.plate_settings.getDict()
        self.plate = readPlate(self.plate_dir, self.io_settings.getDict(), self.seg_settings.getDict(), **self.plate_settings.getDict())
        
        # Calculate concentrations
        self.plate.insert(2, 'Nuclei/µL', self.plate['Nuclei'] * self.plate_dict['well_area'] / self.plate['Area (mm2)'] / self.plate_dict['well_vol'] * self.plate_dict['dil_factor'])
        self.displayPlate()
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")
    
    
    def recalculatePlate(self):
        print('Recalculating plate averages/concentrations...')
        self.plate_dict = self.plate_settings.getDict()
        self.plate['Nuclei/µL'] = self.plate['Nuclei'] / self.plate['Area (mm2)']  * self.plate_dict['well_area'] / self.plate_dict['well_vol'] * self.plate_dict['dil_factor']
        self.displayPlate()
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")

    
    def displayPlate(self):
        print("Making table for %s..." % self.plate_dir)
        
        if self.io_dict['use_img_nums']:
            self.plate_counts = self.plate[['Nuclei']].copy() #not sure if the copy is needed
            self.plate_concs = self.plate[['Nuclei/µL']].copy()
            
        else: # normally what happens
            self.plate_counts = self.plate['Nuclei'].unstack()
            self.plate_counts['Mean'] = self.plate_counts.mean(axis=1)

            self.plate_concs = self.plate['Nuclei/µL'].unstack()
            self.plate_concs['Mean'] = self.plate_concs.mean(axis=1)
        
        # Enable saving plate and calculating dilutions
        self.save_plate["state"] = "normal"
        self.calculate_dilutions["state"] = "normal"
        
        # Enable displaying image from plate
        self.image_selector.clearMenus()
        
        for cur_index in self.plate.index.names:
            self.image_selector.addMenu(cur_index, self.plate.index.get_level_values(cur_index).unique().tolist())
            
        self.image_selector.activate()
        
        self.counts_table.title.config(text="Nuclei counts for %s" % os.path.split(self.plate_dir)[1])
        self.counts_table.display(self.plate_counts)
        self.concs_table.display(self.plate_concs)
        
        # Clear dilution table and save results
        self.dil_dict = self.dil_settings.getDict() #fixes issue with saving pickle if dilution hasn't been done
        self.dilution_table.clear()
        
    
    # NEW: saves all relevant files and info to pickle and CSV
    def saveAll(self):
        print("Saving results...")
        self.plate.to_pickle(os.path.join(self.plate_dir, "all_data.pickle"))
        all_dicts = [self.seg_dict, self.io_dict, self.plate_dict, self.dil_dict]
        pickle.dump(all_dicts, open(os.path.join(self.plate_dir, "settings.pickle"), 'wb'))
        
        # Make human-readable csv file
        pd_csv_args = {'encoding':'utf-8', 'line_terminator':'\n'}
        with open(os.path.join(self.plate_dir, "count_data.csv"), 'w') as f:
            f.write("Folder path,%s\n\n" % self.plate_dir)
            
            f.write("Nuclei counts\n")
            f.write(self.plate_counts.to_csv(**pd_csv_args) + "\n")
            f.write("Nuclei/µL\n")
            f.write(self.plate_concs.to_csv(**pd_csv_args) + "\n")
            
            if self.dil_df is not None:
                f.write("Dilution calculations\n")
                for key, val in self.dil_dict.items():
                    f.write("%s,%s\n" % (key, val))
                    
                f.write(self.dil_df.to_csv(**pd_csv_args) + "\n")
            
            f.write("Segmentation settings\n")
            for key, val in self.seg_dict.items():
                f.write("%s,%s\n" % (key, val))
                
            f.write("\nI/O settings\n")
            for key, val in self.io_dict.items():
                f.write("%s,%s\n" % (key, val))
                        
            f.write("\nPlate settings\n")
            for key, val in self.plate_dict.items():
                f.write("%s,%s\n" % (key, val))
                
            if self.dil_df is not None:            
                f.write("\nDilution settings\n")
                
                    
        # Save log
        with open(os.path.join(self.plate_dir, "log.txt"), 'w') as logfile:
            logfile.write(self.log_box.get("1.0",'end-1c'))
            
        print("Done")
    
    def loadAll(self):
        plate_dir = filedialog.askdirectory(initialdir=self.plate_dir, title="Select plate directory")
        
        if not plate_dir:
            return 0
        
        self.plate_dir = plate_dir
        print("Loading %s..." % self.plate_dir)
        self.plate = pd.read_pickle(os.path.join(self.plate_dir, "all_data.pickle"))
        self.seg_dict, self.io_dict, self.plate_dict, self.dil_dict = pickle.load(open(os.path.join(self.plate_dir,"settings.pickle"), 'rb'))
        
        self.seg_settings.setDict(self.seg_dict)
        self.io_settings.setDict(self.io_dict)
        self.plate_settings.setDict(self.plate_dict)
        self.dil_settings.setDict(self.dil_dict)
        self.displayPlate()
        print("Done")
       

    def selectDisplayImage(self):
        img_index = self.image_selector.getImgLocation()
        img_path = self.plate.at[img_index, 'Path']
        maxima = self.plate.at[img_index, 'Maxima']
        img_name = "_".join(img_index)
        
        if self.plate_dict['rel_paths']:
            img_path = os.path.join(self.plate_dir, img_path)
        
        self.displayImage(img_path, maxima, img_name)
        
    
    def onClose(self):
        plt.close('all')
        sys.stdout = self.stdout_old
        sys.stderr = self.stderr_old
        self.destroy()
        self.quit()

        
app = MainWindow()
app.mainloop()