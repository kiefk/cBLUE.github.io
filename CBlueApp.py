"""
cBLUE (comprehensive Bathymetric Lidar Uncertainty Estimator)
Copyright (C) 2019
Oregon State University (OSU)
Center for Coastal and Ocean Mapping/Joint Hydrographic Center, University of New Hampshire (CCOM/JHC, UNH)
NOAA Remote Sensing Division (NOAA RSD)

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Contact:
Christopher Parrish, PhD
School of Construction and Civil Engineering
101 Kearney Hall
Oregon State University
Corvallis, OR  97331
(541) 737-5688
christopher.parrish@oregonstate.edu

Last Edited By:
Keana Kief (OSU)
April 4th, 2023

THINGS TO DO:
Add comments
"""

# -*- coding: utf-8 -*-
import logging
# Customize logging
import utils

import tkinter as tk
from tkinter import ttk
import os
import time
import json
import webbrowser
import laspy

from Subaerial import SensorModel, Jacobian
from GuiSupport import DirectorySelectButton, RadioFrame
from Merge import Merge

from Sbet import Sbet
from Datum import Datum
from Tpu import Tpu

#Create a logging file named CBlue.log stored in the current working directory
utils.CustomLogger(filename="CBlue.log")


LARGE_FONT = ("Verdanna", 12)
NORM_FONT = ("Verdanna", 10)
NORM_FONT_BOLD = ("Verdanna", 10, "bold")
SMALL_FONT = ("Verdanna", 8)


class CBlueApp(tk.Tk):
    """Gui used to determine the total propagated
    uncertainty of Lidar Topobathymetry measurements.

    Created: 2017-12-0

    @original author: Timothy Kammerer
    @modified by: Nick Forfinski-Sarkozi
    """

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        with open("cBLUE_ASCII_splash.txt", "r") as f:
            message = f.readlines()
            print("".join(message))

        self.config_file = "cblue_configuration.json"

        print(
            "Be sure to verify the settings in {}\n"
            "(If you change a setting, restart cBLUE.)\n".format(self.config_file)
        )

        self.load_config()  # sets controller_configuration variables

        # show splash screen
        self.withdraw()
        splash = Splash(self)

        tk.Tk.wm_title(self, "cBLUE")
        tk.Tk.iconbitmap(self, "cBLUE_icon.ico")

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        menubar = tk.Menu(container)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Save settings", command=lambda: self.save_config())
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=quit)
        menubar.add_cascade(label="File", menu=filemenu)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="Documentation", command=self.show_docs)
        about_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=about_menu)

        tk.Tk.config(self, menu=menubar)

        self.frames = {}
        for F in (ControllerPanel,):  # makes it easy to add "pages" in future
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(ControllerPanel)

        # after splash screen, show main GUI
        time.sleep(1)
        splash.destroy()
        self.deiconify()

    def load_config(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file) as cf:
                self.controller_configuration = json.load(cf)
        else:
            logging.cblue("configuration file doesn't exist")

    def save_config(self):
        config = "cblue_configuration.json"

        with open(config, "w") as fp:
            json.dump(self.controller_configuration, fp)

    def show_docs(self):
        webbrowser.open(r"file://" + os.path.realpath("docs/html/index.html"), new=True)

    def show_about(self):
        about = tk.Toplevel()
        about.resizable(False, False)
        tk.Toplevel.iconbitmap(about, "cBLUE_icon.ico")
        about.wm_title("About cBLUE")

        canvas = tk.Canvas(about, width=615, height=371)
        splash_img = tk.PhotoImage(file="cBLUE_splash.gif", master=canvas)
        canvas.pack(fill="both", expand="yes")

        license_msg = r"""
        cBLUE {}
        Copyright (C) 2019
        Oregon State University (OSU)
        Center for Coastal and Ocean Mapping/Joint Hydrographic Center, University of New Hampshire (CCOM/JHC, UNH)
        NOAA Remote Sensing Division (NOAA RSD)

        This library is free software; you can redistribute it and/or
        modify it under the terms of the GNU Lesser General Public
        License as published by the Free Software Foundation; either
        version 2.1 of the License, or (at your option) any later version.

        This library is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
        Lesser General Public License for more details.
        """.format(
            self.controller_configuration["cBLUE_version"]
        )

        canvas.create_image(0, 0, image=splash_img, anchor=tk.NW)
        canvas_id = canvas.create_text(10, 10, anchor="nw")
        canvas.itemconfig(canvas_id, text=license_msg)
        canvas.itemconfig(canvas_id, font=("arial", 8))

        # label = tk.Label(about, image=splash_img, text=license_msg, compound=tk.CENTER)
        # label.pack()
        b1 = ttk.Button(about, text="Ok", command=about.destroy)
        b1.pack()
        about.mainloop()

    @staticmethod
    def popupmsg(msg):
        popup = tk.Tk()
        popup.wm_title("!")
        label = ttk.Label(popup, text=msg, font=NORM_FONT)
        label.pack(side="top", fill="x", pady=10)
        b1 = ttk.Button(popup, text="Ok", command=popup.destroy)
        b1.pack()
        popup.mainloop()

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()


class Splash(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        splash_img = tk.PhotoImage(file="cBLUE_splash.gif", master=self)
        label = tk.Label(self, image=splash_img)
        label.pack()
        self.update()


class ControllerPanel(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)

        self.lastFileLoc = os.getcwd()

        # TODO:  get from separate text file
        # WHY IS THIS An ENUMERATED DICT AND NOT JUST AN ARRAY?!?
        self.kd_vals = {
            0: ("Clear", range(6, 11)),
            1: ("Clear-Moderate", range(11, 18)),
            2: ("Moderate", range(18, 26)),
            3: ("Moderate-High", range(26, 33)),
            4: ("High", range(33, 37)),
        }

        # TODO:  get from separate text file
        # WHY IS THIS An ENUMERATED DICT AND NOT JUST AN ARRAY?!?
        self.wind_vals = {
            0: ("Calm-light air (0-2 kts)", [1]),
            1: ("Light Breeze (3-6 kts)", [2, 3]),
            2: ("Gentle Breeze (7-10 kts)", [4, 5]),
            3: ("Moderate Breeze (11-15 kts)", [6, 7]),
            4: ("Fresh Breeze (16-20 kts)", [8, 9, 10]),
        }

        self.is_sbet_dir_set = False
        self.is_las_dir_set = False
        self.is_tpu_dir_set = False
        self.is_sbet_loaded = False
        self.is_tpu_computed = False
        self.buttonEnableStage = 0  # to measure progress through button stages
        self.sbetInput = None
        self.lasInput = None
        self.tpuOutput = None
        self.sbet = None
        self.parent = parent
        self.controller = controller

        # Default region is no region
        self.mcu = 0

        #  Build the control panel
        self.control_panel_width = 30
        self.build_control_panel()
        # self.build_map_panel()

    def build_control_panel(self):
        self.controller_panel = ttk.Frame(self)
        self.controller_panel.grid(row=0, column=0, sticky=tk.EW)
        self.controller_panel.grid_rowconfigure(0, weight=1)
        self.build_directories_input()
        self.build_subaqueous_input()
        self.build_vdatum_input()
        self.build_sensor_input()
        self.build_error_type_input()
        self.build_output_csv()
        self.build_process_buttons()
        self.update_button_enable()

    def build_directories_input(self):
        """Builds the directory selection input and processing Buttons for the subaerial portion."""

        subaerial_frame = tk.Frame(self.controller_panel)
        subaerial_frame.grid(row=0)
        subaerial_frame.columnconfigure(0, weight=1)
        label = tk.Label(subaerial_frame, text="Data Directories", font=NORM_FONT_BOLD)
        label.grid(row=0, columnspan=1, pady=(10, 0), sticky=tk.EW)

        self.sbetInput = DirectorySelectButton(
            self,
            subaerial_frame,
            "Trajectory",
            self.controller.controller_configuration["directories"]["sbet"],
            self.control_panel_width,
            callback=self.update_button_enable,
        )
        self.sbetInput.grid(row=1, column=0)

        self.lasInput = DirectorySelectButton(
            self,
            subaerial_frame,
            "LAS",
            self.controller.controller_configuration["directories"]["las"],
            self.control_panel_width,
            callback=self.update_button_enable,
        )
        self.lasInput.grid(row=2, column=0)

        self.tpuOutput = DirectorySelectButton(
            self,
            subaerial_frame,
            "Output",
            self.controller.controller_configuration["directories"]["tpu"],
            self.control_panel_width,
            callback=self.update_button_enable,
        )
        self.tpuOutput.grid(row=3, column=0)

    def build_subaqueous_input(self):
        """
        This function builds the frame and tab toggle for
        selecting wind/kd ranges.
        Inputs: None
        Returns: Void
        """
        ### Frame layout (contains parameter widgets) ###
        subaqueous_frame = tk.Frame(self.controller_panel)
        subaqueous_frame.grid(row=1, sticky=tk.EW)
        subaqueous_frame.columnconfigure(0, weight=1)

        tk.Label(
            subaqueous_frame, text="Environmental Parameters", font="Helvetica 10 bold"
        ).grid(row=0, pady=(10, 0), sticky=tk.EW)

        ### Toggle between Wind and Kd panel tabs ###
        subaqueous_method_tabs = ttk.Notebook(subaqueous_frame)
        subaqueous_method_tabs.grid(row=1, column=0)

        tab1 = ttk.Frame(subaqueous_method_tabs)
        subaqueous_method_tabs.add(tab1, text="Water Surface")

        tab2 = ttk.Frame(subaqueous_method_tabs)
        subaqueous_method_tabs.add(tab2, text="Turbidity")

        water_surface_subframe = tk.Frame(tab1)
        water_surface_subframe.grid(row=1, column=0)

        ### Set wind ranges as radio buttons ###
        self.windOptions = [w[0] for w in self.wind_vals.values()]

        self.windRadio = RadioFrame(
            water_surface_subframe,
            None,
            self.windOptions,
            1,
            width=self.control_panel_width - 5,
        )
        self.windRadio.grid(row=1, column=0, sticky=tk.E)

        ### Create new frame for Kd range selection ###
        turbidity_subframe = tk.Frame(tab2)
        turbidity_subframe.grid(row=2, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        turbidity_subframe.columnconfigure(0, weight=1)
        turbidity_subframe.rowconfigure(0, weight=1)

        ### Set Kd ranges as radio buttons ###
        self.turbidityOptions = [
            "{:s} ({:.2f}-{:.2f} m^-1)".format(k[0], k[1][0] / 100.0, k[1][-1] / 100.0)
            for k in self.kd_vals.values()
        ]

        self.turbidityRadio = RadioFrame(
            turbidity_subframe,
            "Turbidity (kd_490)",
            self.turbidityOptions,
            0,
            width=self.control_panel_width,
        )
        self.turbidityRadio.grid(row=0, column=0, sticky=tk.N)

    def build_vdatum_input(self):
        datum_frame = tk.Frame(self.controller_panel)
        datum_frame.columnconfigure(0, weight=1)
        datum_frame.grid(row=3, sticky=tk.EW)
        tk.Label(datum_frame, text="VDatum Region", font="Helvetica 10 bold").grid(
            row=0, columnspan=1, pady=(10, 0), sticky=tk.EW
        )

        datum = Datum()
        regions, mcu_values, default_msg = datum.get_vdatum_region_mcus()
        self.vdatum_regions = dict(
            {(key, value) for (key, value) in zip(regions, mcu_values)}
        )
        self.vdatum_regions.update({default_msg: 0})
        self.vdatum_region = tk.StringVar(self)
        self.vdatum_region.set(default_msg)
        self.vdatum_region_option_menu = tk.OptionMenu(
            datum_frame,
            self.vdatum_region,
            *sorted(self.vdatum_regions.keys()),
            command=self.update_vdatum_mcu_value,
        )
        self.vdatum_region_option_menu.config(
            width=self.control_panel_width, anchor="w"
        )
        self.vdatum_region_option_menu.grid(sticky=tk.EW)

    def build_sensor_input(self):

        ### Names of sensors as displayed in GUI ###
        self.sensor_models = (
            "Riegl VQ-880-G (0.7 mrad)",
            "Riegl VQ-880-G (1.0 mrad)",
            "Riegl VQ-880-G (1.5 mrad)",
            "Riegl VQ-880-G (2.0 mrad)",
            "Leica Chiroptera 4X (HawkEye 4X Shallow)",
            "HawkEye 4X 400m AGL",
            "HawkEye 4X 500m AGL",
            "HawkEye 4X 600m AGL",
        )

        ### Set up frame to hold dropdown menu ###
        sensor_frame = tk.Frame(self.controller_panel)
        sensor_frame.columnconfigure(0, weight=1)
        sensor_frame.grid(row=4, sticky=tk.EW)
        tk.Label(sensor_frame, text="Sensor Model", font="Helvetica 10 bold").grid(
            row=0, columnspan=1, pady=(10, 0), sticky=tk.EW
        )

        ### Holds the names of the selected sensor ###
        self.selected_sensor = tk.StringVar(self)

        ### Add sensor dropdown menu to GUI ###
        self.sensor_option_menu = tk.OptionMenu(
            sensor_frame,
            self.selected_sensor,
            *self.sensor_models,
            command=self.update_selected_sensor,
        )

        self.sensor_option_menu.config(width=self.control_panel_width, anchor="w")
        self.sensor_option_menu.grid(sticky=tk.EW)

    def update_selected_sensor(self, sensor):
        """
        Callback function for the sensor option menu.
        Updates the controller when a new sensor is selected.
        """
        self.selected_sensor = sensor
        self.controller.controller_configuration["sensor_model"] = sensor

    def build_error_type_input(self):

        ### 95% conf or 1 sigma ###
        self.error_types = ("1-\u03c3", "95% confidence")

        ### Set up frame to hold dropdown menu ###
        error_frame = tk.Frame(self.controller_panel)
        error_frame.columnconfigure(0, weight=1)
        error_frame.grid(row=5, sticky=tk.EW)
        tk.Label(error_frame, text="TPU Metric", font="Helvetica 10 bold").grid(
            row=0, columnspan=1, pady=(10, 0), sticky=tk.EW
        )

        ### Holds the names of the selected sensor ###
        self.error_type = tk.StringVar(self)

        ### Add sensor dropdown menu to GUI ###
        self.error_option_menu = tk.OptionMenu(
            error_frame,
            self.error_type,
            *self.error_types,
            command=self.update_error_type,
        )

        self.error_option_menu.config(width=self.control_panel_width, anchor="w")
        self.error_option_menu.grid(sticky=tk.EW)

    def update_error_type(self, error_type):
        """
        Callback function for the sensor option menu.
        Updates the controller when a new sensor is selected.
        """
        self.selected_error = error_type
        self.controller.controller_configuration["error_type"] = error_type

    def build_output_csv(self):
        """
        Callback function to output points as csv_option
        """

        ### Set up frame to hold radio buttons ###
        csv_frame = tk.Frame(self.controller_panel)
        csv_frame.columnconfigure(0, weight=1)
        csv_frame.columnconfigure(1, weight=0)
        csv_frame.grid(row=6, sticky=tk.EW)
        tk.Label(csv_frame, text="Output Options", font="Helvetica 10 bold").grid(
            row=0, columnspan=2, pady=(10, 0), sticky=tk.EW
        )

        self.csv_option = tk.BooleanVar()

        self.extrabyte_button = ttk.Radiobutton(
            csv_frame, text="ExtraBytes", value=False, variable=self.csv_option
        )

        self.csv_button = ttk.Radiobutton(
            csv_frame, text="ExtraBytes + CSV", value=True, variable=self.csv_option
        )

        self.extrabyte_button.grid(row=1, column=0, sticky=tk.W, padx=30)

        self.csv_button.grid(row=2, column=0, sticky=tk.W, padx=30)

    def update_output_csv(self, csv_option):
        pass

    def build_process_buttons(self):
        process_frame = tk.Frame(self.controller_panel)
        process_frame.grid(row=7, sticky=tk.NSEW)
        process_frame.columnconfigure(0, weight=0)

        label = tk.Label(process_frame, text="Process Buttons", font=NORM_FONT_BOLD)
        label.grid(row=0, columnspan=2, pady=(10, 0), sticky=tk.EW)

        self.sbet_btn_text = tk.StringVar(self)
        self.sbet_btn_text.set("Load Trajectory File(s)")
        self.sbetProcess = tk.Button(
            process_frame,
            textvariable=self.sbet_btn_text,
            width=self.control_panel_width,
            state=tk.DISABLED,
            command=self.sbet_process_callback,
        )
        self.sbetProcess.grid(row=1, column=0, padx=(3, 0), sticky=tk.EW)

        self.tpu_btn_text = tk.StringVar(self)
        self.tpu_btn_text.set("Process TPU")
        self.tpuProcess = tk.Button(
            process_frame,
            textvar=self.tpu_btn_text,
            width=self.control_panel_width,
            state=tk.DISABLED,
            command=self.tpu_process_callback,
        )
        self.tpuProcess.grid(row=2, column=0, padx=(3, 0), sticky=tk.EW)

    def update_vdatum_mcu_value(self, region):
        self.mcu = self.vdatum_regions[region]

    def update_button_enable(self):
        if self.sbetInput.directoryName != "":
            self.is_sbet_dir_set = True
            self.sbetProcess.config(state=tk.ACTIVE)
            self.controller.controller_configuration["directories"].update(
                {"sbet": self.sbetInput.directoryName}
            )
            self.sbetInput.button.config(
                text="{} Directory Set".format("Trajectory"), fg="darkgreen"
            )

        if self.lasInput.directoryName != "":
            self.is_las_dir_set = True
            self.controller.controller_configuration["directories"].update(
                {"las": self.lasInput.directoryName}
            )
            self.lasInput.button.config(
                text="{} Directory Set".format("Las"), fg="darkgreen"
            )

        if self.tpuOutput.directoryName != "":
            self.is_tpu_dir_set = True
            self.controller.controller_configuration["directories"].update(
                {"tpu": self.tpuOutput.directoryName}
            )
            self.tpuOutput.button.config(
                text="{} Directory Set".format("TPU"), fg="darkgreen"
            )

        if self.is_las_dir_set and self.is_tpu_dir_set and self.is_sbet_loaded:
            self.tpuProcess.config(state=tk.ACTIVE)

    def sbet_process_callback(self):
        print(
            json.dumps(
                self.controller.controller_configuration, indent=1, sort_keys=True
            )
        )
        self.sbet = Sbet(self.sbetInput.directoryName)
        self.sbet.set_data()
        self.is_sbet_loaded = True
        self.sbet_btn_text.set("Trajectory Loaded")
        self.sbetProcess.config(fg="darkgreen")
        self.update_button_enable()

    def tpu_process_callback(self):
        self.verify_water_level()

    def continue_with_tpu_calc(self, wseh_popup, wseh_value):
        self.controller.controller_configuration[
            "water_surface_ellipsoid_height"
        ] = wseh_value
        self.controller.save_config()
        wseh_popup.destroy()
        self.begin_tpu_calc()

    def verify_water_level(self):
        wseh = tk.Toplevel()
        tk.Toplevel.iconbitmap(wseh, "cBLUE_icon.ico")
        wseh.resizable(False, False)
        wseh.wm_title("IMPORTANT!!!")

        msg = "Enter the nominal water-surface ellipsoid height:\n(default value read from config file)"

        label = tk.Label(wseh, text=msg)
        label.pack()

        wseh_value = tk.StringVar(self)
        wseh_value.set(
            self.controller.controller_configuration["water_surface_ellipsoid_height"]
        )

        entry = tk.Entry(wseh, textvariable=wseh_value)
        entry.pack()

        b1 = ttk.Button(
            wseh,
            text="Ok",
            command=lambda: self.continue_with_tpu_calc(wseh, float(wseh_value.get())),
        )
        b1.pack()

        wseh.mainloop()

    def begin_tpu_calc(self):

        wind_ind = self.windRadio.selection.get()
        wind_selection = self.windOptions[wind_ind]

        kd_ind = self.turbidityRadio.selection.get()
        kd_selection = self.turbidityOptions[kd_ind]

        # CREATE OBSERVATION EQUATIONS
        sensor_model = SensorModel(
            self.controller.controller_configuration["sensor_model"]
        )

        multiprocess = self.controller.controller_configuration["multiprocess"]

        if multiprocess:
            num_cores = self.controller.controller_configuration["number_cores"]
            cpu_process_info = ("multiprocess", num_cores)
        else:
            cpu_process_info = ("singleprocess",)

        tpu = Tpu(
            wind_selection,
            self.wind_vals[wind_ind][1],
            kd_selection,
            self.kd_vals[kd_ind][1],
            self.vdatum_region.get(),
            self.mcu,
            self.tpuOutput.directoryName,
            self.controller.controller_configuration["cBLUE_version"],
            self.controller.controller_configuration["sensor_model"],
            cpu_process_info,
            self.selected_sensor,
            self.controller.controller_configuration["subaqueous_LUTs"],
            self.controller.controller_configuration["water_surface_ellipsoid_height"],
            self.controller.controller_configuration["error_type"],
            self.csv_option.get(),
        )

        las_files = [
            os.path.join(self.lasInput.directoryName, l)
            for l in os.listdir(self.lasInput.directoryName)
            if l.endswith(".las") | l.endswith(".laz")
        ]

        num_las = len(las_files)

        # GENERATE JACOBIAN FOR SENSOR MODEL OBSVERVATION EQUATIONS
        jacobian = Jacobian(sensor_model)

        # CREATE OBJECT THAT PROVIDES FUNCTIONALITY TO MERGE LAS AND TRAJECTORY DATA
        merge = Merge()

        def signal_completion():
            self.tpu_btn_text.set("TPU Calculated")
            self.tpuProcess.config(fg="darkgreen")
            print("DONE!! (close cBLUE before running again)")

        def sbet_las_tiles_generator():
            """This generator is the 2nd argument for the
            run_tpu_multiprocessing method, to avoid
            passing entire sbet or list of tiled
            sbets to the calc_tpu() method
            """

            for las_file in las_files:
                logging.cblue(
                    "({}) generating SBET tile...".format(os.path.split(las_file)[-1])
                )

                inFile = laspy.read(las_file)
                west = inFile.header.x_min
                east = inFile.header.x_max
                north = inFile.header.y_max
                south = inFile.header.y_min

                yield self.sbet.get_tile_data(
                    north, south, east, west
                ), las_file, jacobian, merge

        logging.cblue(
            "processing {} las file(s) ({})...".format(num_las, cpu_process_info[0])
        )

        logging.cblue(f"multiprocessing = {multiprocess} ({type(multiprocess)})")

        if multiprocess == "True":
            p = tpu.run_tpu_multiprocess(num_las, sbet_las_tiles_generator())
            signal_completion()
            p.close()
            p.join()
        elif multiprocess == "False":
            tpu.run_tpu_singleprocess(num_las, sbet_las_tiles_generator())
            signal_completion()
        else:
            logging.cblue(
                f"multiprocessing set to {multiprocess} (Must be True or False)"
            )

    def updateRadioEnable(self):
        """Updates the state of the windRadio, depending on waterSurfaceRadio."""
        if self.waterSurfaceRadio.selection.get() == 0:
            self.windRadio.setState(tk.DISABLED)
        else:
            self.windRadio.setState(tk.ACTIVE)


if __name__ == "__main__":

    app = CBlueApp()
    app.geometry("350x650")
    app.mainloop()
