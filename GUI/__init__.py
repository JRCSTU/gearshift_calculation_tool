# Copyright 2015-2021 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
GEARSHIFT GUI.
"""
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import scrolledtext
from pathlib import Path
import threading
import subprocess
import os.path as osp
import os


def canvas_gui(root):

    root.title("Gearshift calculation tool")
    root.geometry("1800x750")
    root.resizable(0, 0)

    canvas1 = tk.Canvas(root, width=1800, height=750)
    mydir = osp.dirname(osp.dirname(__file__))
    filepath = Path(mydir, "doc", "_static", "images", "gs_logo_name_tool.png")
    canvas1.pack()

    bg = tk.PhotoImage(file=filepath)
    background = tk.Label(root, image=bg)
    background.place(x=0, y=0)

    # Select Label
    selectLabel = tk.Label(
        root, text="Select input file:", font=("Arial", 11, "bold"), bg="white"
    )
    canvas1.create_window(580, 155, window=selectLabel)

    button3 = tk.Button(
        root,
        text="Exit Application",
        command=root.destroy,
        bg="tomato2",
        font=("Arial", 11, "bold"),
    )
    canvas1.create_window(1720, 40, window=button3)

    # Define functions that are going to be used
    def browse_input_file():
        """
        Browse input file function

        This function open a window and you can select the input file
        """
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Select a File",
            filetypes=(("Excel files", "*.xlsx*"), ("all files", "*.*")),
        )

        # Change entry contents
        inputEntry.delete(0, tk.END)  # deletes the current value
        inputEntry.insert(0, filename)

    def browse_output_folder():
        folderpath = filedialog.askdirectory(
            initialdir="/", title="Select an Output Folder"
        )

        outputEntry.delete(0, tk.END)
        outputEntry.insert(0, folderpath)

    def demo_output_folder():
        folderpath = filedialog.askdirectory(
            initialdir="/", title="Select an Output Folder"
        )

        demoEntry.delete(0, tk.END)
        demoEntry.insert(0, folderpath)

    # Here we are going to create a buttons to run the gearshift tool
    def get_demo_file():
        demoPath = Path(demoEntry.get())

        if osp.isdir(demoPath) is False:
            failDemoMessage = b"The demo folder path cannot be created or opened please check it and run again \n"
            logText.insert("end", failDemoMessage, "error")
        else:
            demoExe = subprocess.check_output(
                f'cmd /c "gearshift demo "{demoPath}"',
                stderr=subprocess.STDOUT,
                shell=True,
            )
            logText.insert("end", demoExe, "info")

    # Definition of scrolling text to log
    logText = scrolledtext.ScrolledText(
        wrap=tk.WORD, width=107, height=20, font=("Fixedsys", 10), bg="black"
    )
    logText.place(x=520, y=370)

    logText.tag_configure("error", justify="left", foreground="red")
    logText.tag_configure("info", justify="left", foreground="green")
    logText.tag_configure("warning", justify="left", foreground="orange")

    # Define or label
    orLabel = tk.Label(root, text="or:", font=("Arial", 11, "bold"), bg="white")
    canvas1.create_window(530, 240, window=orLabel)

    # Define the default text of the Entry
    inputText = tk.StringVar(root, value="Path")
    inputEntry = tk.Entry(root, textvariable=inputText, width=80, bd=5)
    canvas1.create_window(930, 270, window=inputEntry)

    # Create a button to read input file
    button_explore = tk.Button(
        root,
        text="Browse Input File",
        command=browse_input_file,
        bg="lightsteelblue2",
        font=("Arial", 11, "bold"),
    )
    canvas1.create_window(590, 270, window=button_explore)

    fileLabel = tk.Label(
        root,
        text="Insert output path or select Output Folder:",
        font=("Arial", 11, "bold"),
        bg="white",
    )
    canvas1.create_window(670, 306, window=fileLabel)

    # Define the default value of the output Entry
    outputText = tk.StringVar(root, value="Path")
    outputEntry = tk.Entry(root, textvariable=outputText, width=80, bd=5)
    canvas1.create_window(917, 340, window=outputEntry)

    # Create a button to read output file
    button_output_explore = tk.Button(
        root,
        text="Output Folder",
        command=browse_output_folder,
        bg="lightsteelblue2",
        font=("Arial", 11, "bold"),
    )
    canvas1.create_window(576, 340, window=button_output_explore)

    # Define download demo file
    demoText = tk.StringVar(root, value="Path")
    demoEntry = tk.Entry(root, textvariable=demoText, width=80, bd=5)
    canvas1.create_window(1300, 200, window=demoEntry)

    # Create a button to save the demo file
    button_demo_explore = tk.Button(
        root,
        text="Demo Folder",
        command=demo_output_folder,
        bg="lightsteelblue2",
        font=("Arial", 11, "bold"),
    )
    canvas1.create_window(972, 200, window=button_demo_explore)

    # Label in between button and entry
    inLabel = tk.Label(root, text="in", font=("Arial", 11, "bold"), bg="white")
    canvas1.create_window(885, 200, window=inLabel)

    # Create a button to save the demo file
    button_demo_run = tk.Button(
        root,
        text="Download Demo File",
        command=get_demo_file,
        bg="DarkSeaGreen3",
        font=("Arial", 11, "bold"),
        width=35,
        height=2,
    )
    canvas1.create_window(684, 200, window=button_demo_run)

    def progres_bar_start(interval):
        logText.insert(
            "end",
            b"\n SIMULATION IN PROGRESS, YOU WILL RECEIVE THE RESULTS IN A FEW SECONDS \n",
            "warning",
        )
        progBar.start(interval=interval)

    def run_command(inputPath, outputPath):
        runExe = subprocess.check_output(
            f'cmd /c "gearshift run "{inputPath}" -O "{outputPath}"',
            stderr=subprocess.STDOUT,
            shell=True,
        )

        logText.insert("end", runExe, "info")

        progBar.stop()

    def run_gearshift():
        progBarT = threading.Thread(target=progres_bar_start, args=(20,))
        progBarT.start()
        inputPath = Path(inputEntry.get())
        outputPath = Path(outputEntry.get())

        if osp.isfile(inputPath) is False:
            logText.insert(
                "end", b"The input file doesn't exists, please check it \n", "error"
            )
            progBar.stop()

        else:
            os.makedirs(osp.dirname(outputPath), exist_ok=True)
            runGS = threading.Thread(target=run_command, args=(inputPath, outputPath))
            runGS.start()

    # Create a button to save the demo file
    button_demo_run = tk.Button(
        root,
        text="Run Gearshift",
        command=run_gearshift,
        bg="yellow green",
        font=("Arial", 11, "bold"),
        width=35,
        height=4,
    )
    canvas1.create_window(1370, 295, window=button_demo_run)

    progBar = ttk.Progressbar(
        root, orient=tk.HORIZONTAL, length=320, mode="indeterminate"
    )
    canvas1.create_window(1370, 355, window=progBar)

    root.mainloop()


def Main() -> None:

    root = tk.Tk()

    canvas_gui(root)


# Now just run the functions by calling our Main() function,
if __name__ == "__main__":
    Main()
