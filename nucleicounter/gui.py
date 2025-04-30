import sys
import os
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog
import pickle
import matplotlib.pyplot as plt

# Import the new modules
from .processing import countImage, readPlate, recalculatePlateConcentrations, calculateDilutions, formatPlateData
from .visualization import displayImage
from .file_io import saveResults, loadResults
from .config import (
    SEGMENTATION_SETTINGS,
    IO_SETTINGS,
    DISPLAY_SETTINGS,
    PLATE_PRESETS,
    PLATE_SETTINGS,
    DILUTION_SETTINGS
)

def makeTkVar(master, val):
    if isinstance(val, str):
        return tk.StringVar(master, value=val)
    else:
        return tk.DoubleVar(master, value=val)


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
            print("Found multi-index")
            for folder in df.index.levels[0]:
                new_parent = self.tree.insert(parent, "end", text=folder, values=['']*len(self.tree['columns']), open=True)
                self.recursiveInsert(df.loc[folder], new_parent)
        else:
            for index, row in df.iterrows():
                self.tree.insert(parent, "end", text=index, values=[round(x, self.decimals) for x in row])
    
    # Heirarchical display for additional levels of recursion
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
    
    # Add settings from a config dictionary
    def addFromConfig(self, settings_dict):
        for name, setting in settings_dict.items():
            # Convert type string to appropriate TkVar
            if setting['type'] == 'string':
                var = tk.StringVar(self, value=setting['default'])
            elif setting['type'] == 'double':
                var = tk.DoubleVar(self, value=setting['default'])
            elif setting['type'] == 'int':
                var = tk.IntVar(self, value=setting['default'])
            elif setting['type'] == 'boolean':
                var = tk.BooleanVar(self, value=setting['default'])
            elif setting['type'] == 'list':
                var = tk.StringVar(self, value=setting['default'])
            else:
                raise ValueError(f"Unknown type {setting['type']} for setting {name}")
            
            setattr(self, name, var)
            self.dict[name] = var
            
            # Grid the label and entry field
            ttk.Label(master=self, text=setting['description']).grid(row=self.row, column=0, sticky='nw')
            
            if setting['type'] == 'boolean':
                new_box = ttk.Checkbutton(self, variable=var)
            elif setting['type'] == 'list':
                new_box = ttk.OptionMenu(self, var, setting['default'], *setting['options'])
            else:
                new_box = ttk.Entry(master=self, textvariable=var, width=self.entry_width)
            
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
    
    # Returns a dictionary of the settings in the SettingsBox
    def getDict(self):
        return {name: var.get() for name, var in self.dict.items()}
    
    # Updates the values of the settings in the SettingsBox from a dictionary
    # A subset of values can be updated by passing a dictionary with only the desired values
    def setDict(self, in_dict):
        for var, val in in_dict.items():
            self.dict[var].set(val)
    
    # Updates the values of the settings in the SettingsBox from a preset
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
    def __init__(self, seg_settings=SEGMENTATION_SETTINGS, io_settings=IO_SETTINGS, plate_presets=PLATE_PRESETS, plate_settings=PLATE_SETTINGS, display_settings=DISPLAY_SETTINGS, dil_settings=DILUTION_SETTINGS):
        tk.Tk.__init__(self)
        
        # Preserving stdout and stderr from sys so they can be restored when the window is closed
        self.stdout_old = sys.stdout
        self.stderr_old = sys.stderr
        
        self.title('NucleiCounter')
        self.protocol("WM_DELETE_WINDOW", self.onClose)
        
        self.single_img_dir = None
        self.plate_dir = None
        self.cur_img_name = None
        self.plate = None
        self.plate_counts = None
        self.plate_concs = None
        self.dil_df = None
        
        self.settings_buttons = ttk.Frame(self)
        
        # Laying out settings
        self.settings = ttk.Frame(self.settings_buttons)
        
        self.seg_settings = SettingsBox(self.settings, 'Segmentation settings')
        self.seg_settings.addFromConfig(seg_settings)
        
        self.io_settings = SettingsBox(self.settings, 'Image file settings')
        self.io_settings.addFromConfig(io_settings)
        
        self.plate_settings = SettingsBox(self.settings, 'Plate/hemocytometer settings')
        self.plate_settings.addFromConfig(plate_settings)
        
        # Add presets from config
        for preset_name, preset_values in plate_presets.items():
            self.plate_settings.addPreset(preset_name, **preset_values)
        
        self.plate_settings.addPresetMenu()
        
        self.display_settings = SettingsBox(self.settings, 'Display/save settings')
        self.display_settings.addFromConfig(display_settings)
        
        self.dil_settings = SettingsBox(self.settings, 'Dilution calculation')
        self.dil_settings.addFromConfig(dil_settings)
        
        self.seg_settings.grid(row=0, column=0, sticky='nsew')
        self.plate_settings.grid(row=0, column=1, sticky='nsew')
        self.io_settings.grid(row=1, column=0, sticky='nsew')
        self.display_settings.grid(row=1, column=1, sticky='nsew')
        self.dil_settings.grid(row=2, column=0, sticky='nsew')
        
        # Laying out buttons
        self.buttons = ttk.Frame(self.settings_buttons) # top part
        self.buttons2 = ttk.Frame(self.settings_buttons) # bottom part
        
        self.count_img = ttk.Button(self.buttons, text='Count single image', command=self.segmentImage)
        self.display_img = ttk.Button(self.buttons, text='Display single image', command=self.displayImage, state='disabled')
        self.count_plate = ttk.Button(self.buttons, text='Count plate/hemocytometer', command=self.countPlate)
        self.save_plate = ttk.Button(self.buttons, text='Manual save', command=self.saveAll, state='disabled')
        self.load_plate = ttk.Button(self.buttons2, text='Load saved data', command=self.loadAll)
        self.redo_tables = ttk.Button(self.buttons2, text='Recalculate plate avgs/concentrations', command=self.recalculatePlate)
        self.calculate_dilutions = ttk.Button(self.buttons2, text='Calculate dilutions', command = self.calculateDilutions, state='disabled')
        self.save_log = ttk.Button(self.buttons2, text='Save log', command = self.saveLog)
        
        self.count_img.pack(side='left')
        self.display_img.pack(side='left')
        self.count_plate.pack(side='left')
        self.save_plate.pack(side='left')
        self.load_plate.pack(side='left')
        self.redo_tables.pack(side='left')
        self.calculate_dilutions.pack(side='left')
        self.save_log.pack(side='left')
        
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
        self.log_box = tk.Text(self, height=10, state='disabled', bg='#f0f0f0', fg='#000000')
        # Configure tag colors for stdout and stderr
        self.log_box.tag_configure("stdout", foreground="#000000")
        self.log_box.tag_configure("stderr", foreground="#CC0000")
        sys.stdout = TextRedirector(self.log_box, "stdout")
        sys.stderr = TextRedirector(self.log_box, "stderr")
        
        # Assembling window
        self.settings.pack(side='top', anchor='n', fill='none')
        ttk.Label(self.settings_buttons, text="Program log").pack(side='bottom', anchor='w')
        self.buttons2.pack(side='bottom', anchor='s')
        self.buttons.pack(side='bottom', anchor='s')
        
        # Assembling bottom labels
        ttk.Label(self, text="Alexander Epstein, Cao Laboratory, The Rockefeller University").pack(side='bottom', anchor='e')
        ttk.Label(self, text="NucleiCounter (updated 4/29/2025)").pack(side='bottom', anchor='e')
        self.log_box.pack(side='bottom', fill='x')
        
        self.settings_buttons.pack(side='left', fill='y')
        self.tables.pack(side='right')
    
    def calculateDilutions(self):
        print("Calculating dilutions...")
        self.dil_dict = self.dil_settings.getDict()
        
        self.dil_df = calculateDilutions(
            self.plate_concs, 
            self.dil_dict['desired_conc'], 
            self.dil_dict['desired_vol']
        )
        self.dilution_table.display(self.dil_df)
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")
       
  
    def segmentImage(self):
        
        # Get image path and name
        img_path = filedialog.askopenfilename(initialdir=self.single_img_dir, initialfile=self.cur_img_name, title="Select image", filetypes = [("TIFF", "*.tiff *.tif")])
        if not img_path:
            return
        
        self.update()
        self.img_path = img_path
        self.single_img_dir, self.cur_img_name = os.path.split(self.img_path)
        print("Counting nuclei in %s..." % self.cur_img_name)
        
        # Use the new function from processing.py
        img, area, self.maxima = countImage(self.img_path, self.seg_settings.getDict())
        
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
        
        display_settings = {
            'width': self.display_settings.width.get(),
            'height': self.display_settings.height.get(),
            'dpi': self.display_settings.dpi.get(),
            'marker_size': self.display_settings.marker_size.get(),
            'zoom': self.display_settings.zoom.get()
        }
        
        img_fig = displayImage(img_path, maxima, img_name, display_settings)
        img_fig.show()
        
        if self.display_settings.autosave.get():
            img_fig.savefig(os.path.join(os.path.dirname(img_path), img_name + "_segmented.png"))
            
        print("Done")
        
        
    def countPlate(self):
        
        # Get plate path
        plate_dir = filedialog.askdirectory(initialdir=self.plate_dir, title="Select parent folder for plate images")
        
        if not plate_dir:
            return
        
        self.plate_dir = plate_dir
        print("Reading %s..." % self.plate_dir)
        self.update()
        
        self.io_dict = self.io_settings.getDict()
        self.seg_dict = self.seg_settings.getDict()
        self.plate_dict = self.plate_settings.getDict()
        
        self.plate = readPlate(
            self.plate_dir, 
            self.io_dict, 
            self.seg_dict, 
            self.plate_dict
        )
        
        self.displayPlate()
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")
    
    
    def recalculatePlate(self):
        print('Recalculating plate averages/concentrations...')
        self.plate_dict = self.plate_settings.getDict()
        
        # Use the new function from processing.py
        self.plate = recalculatePlateConcentrations(self.plate, self.plate_dict)
        
        self.displayPlate()
        
        if self.display_settings.autosave.get():
            self.saveAll()
        else:
            print("Done")

    
    def displayPlate(self):
        print("Making table for %s..." % self.plate_dir)
        
        # Use the new function from processing.py
        self.plate_counts, self.plate_concs = formatPlateData(self.plate)
        
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
        
    
    def saveAll(self):
        print("Saving results...")
        settings_dicts = [self.seg_dict, self.io_dict, self.plate_dict, self.dil_dict]
        saveResults(
            self.plate_dir,
            self.plate,
            self.plate_counts,
            self.plate_concs,
            settings_dicts,
            self.dil_df
        )
        
        # Save log
        with open(os.path.join(self.plate_dir, "log.txt"), 'w') as logfile:
            logfile.write(self.log_box.get("1.0",'end-1c'))
            
        print("Done")
    
    def loadAll(self):
        plate_dir = filedialog.askdirectory(initialdir=self.plate_dir, title="Select plate directory")
        
        if not plate_dir:
            return
        
        self.plate_dir = plate_dir
        print("Loading %s..." % self.plate_dir)
        
        # Use the new function from data_io.py
        self.plate, settings_dicts = loadResults(self.plate_dir)
        self.seg_dict, self.io_dict, self.plate_dict, self.dil_dict = settings_dicts
        
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
        
    def saveLog(self):
        log_file = filedialog.asksaveasfilename(
            initialdir=self.plate_dir if self.plate_dir else os.getcwd(),
            title="Save Log File",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not log_file:
            return
            
        print(f"Saving log to {log_file}...")
        with open(log_file, 'w') as logfile:
            logfile.write(self.log_box.get("1.0", 'end-1c'))
        print("Log saved successfully")