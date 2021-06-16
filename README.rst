.. figure:: ./doc/_static/images/logo_text.png
    :align: center
    :alt: alternate text
    :figclass: align-center

.. _start-info:

:versions:      |gh-version| |rel-date| |python-ver|
:documentation: https://gearshift-calculation-tool.readthedocs.io/en/latest/ |doc|
:sources:       https://github.com/JRCSTU/gearshift_calculation_tool |pypi-ins| |codestyle|
:keywords:      automotive, car, cars, driving, engine, emissions, fuel-consumption,
                gears, gearshifts, rpm, simulation, simulator, standard, vehicle, vehicles, WLTP
:live-demo:     |binder|
:Licence:     Licensed under the EUPL, Version 1.2 or – as soon they will be approved by the European Commission – subsequent versions of the EUPL (the "Licence");
              You may not use this work except in compliance with the Licence.
              You may obtain a copy of the Licence at: |proj-lic|

              Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
              OF ANY KIND, either express or implied. See the Licence for the specific language governing permissions and limitations under the Licence.

A python-3.6+ package to generate the *gear-shifts* of Light-duty vehicles

.. _end-info:

.. contents:: Table of Contents
  :backlinks: top

.. _start-intro:

Introduction
============

The aim of the Gearshift tool is obtain the Required Engine Speeds, the Available Powers, the Required Vehicle Speeds
and the Gears for the whole WLTC based on the vehicle characteristics. The model should allow accurate calculation
of final trace and the operating conditions of the engine.

Overview
--------
The calculator accepts as input an excel file  that contains the vehicle's technical data, along with parameters for
modifying the execution WLTC cycle, and it then spits-out the gear-shifts of the vehicle and the others parameters used
during the obtaining of these. It does not calculate any |CO2| emissions.

.. _end-intro:

.. _start-installation:

Installation
============
Prerequisites
-------------
**Python-3.6+** is required and **Python-3.7** recommended.
It requires **numpy/scipy** and **pandas** libraries with native backends.

.. Tip::
    On *Windows*, it is preferable to use the `Anaconda <https://www.anaconda.com/products/individual>`__ distribution.
    To avoid possible incompatibilities with other projects

Download
--------
Download the sources,

- either with *git*, by giving this command to the terminal::

      git clone https://github.com/JRCSTU/gearshift_calculation_tool --depth=1

Install
-------
From within the project directory, run one of these commands to install it:

- for standard python, installing with ``pip`` is enough (but might)::

      pip install -e .[path_to_gearshift_calculation_tool_folder]

.. _end-installation:

.. _start-folder:

Project files and folders
-------------------------
The files and folders of the project are listed below::

    +--gearshift/                                       # main folder that contains the whole gearshift project
    |   +--cli/                                         # folder that contains all cli scripts
    |   +--core/                                        # folder that contains core packages
    |       +--load/                                    # (package) python-code of the load
    |           +--speed_phases/                        # folder that contains speed phases in ftr format
    |           +--excel.py                             # (script) load from the excel file parameters
    |       +--model/                                   # (package) python-code of the model
    |           +--calculateShiftpointsNdvFullPC/       # (package) python-code of the calculate shift points, Ndv and  FullPC
    |           +--scaleTrace/                          # (package) python-code of the calculate scale trace
    |       +--write/                                   # (package) python-code of the write
    |           +--excel.py                             # (script) write to the excel file output parameters
    |   +--demos/                                       # folder that contains demo files
    |   +--docs/                                        # folder that contains documentation
    +-- AUTHORS.rst
    +--setup.py                                         # (script) The entry point for `setuptools`, installing, testing, etc
    +--README.rst
    +--LICENSE.txt

.. _end-folder:

.. _start-usage:

Quick-Start
===========

Cmd-line usage
--------------
The command-line usage below requires the Python environment to be installed, and provides for
executing an experiment directly from the OS's shell (i.e. ``cmd`` in windows or ``bash`` in POSIX),
and in a *single* command.  To have precise control over the inputs and outputs

.. code-block:: bash

    $ gearshift --help                                                  ## to get generic help for cmd-line syntax
    $ gearshift demo                                                    ## to get demo input file
    $ gearshift run "path_input_file" -O "path_to_save_output_file"     ## to run gearshift tool
.. _end-usage:

.. _start-library:

Usage
=====

In this example we will use gearshift model in order to predict the gears.

Setup
-----
Import dispatcher(dsp) from gearshift tool that contains functions and simulation model to process vehicle data and Import also
schedula for selecting and executing functions. for more information on how to use `schedula <https://pypi.org/project/schedula/>`__

.. code-block:: python

    from gearshift.core import dsp
    import schedula as sh

Load data
---------
* Load vehicle data for a specific vehicle from `excel template <https://github.com/JRCSTU/gearshift_calculation_tool/raw/main/gearshift/demos/gs_input_demo.xlsx>`__

    .. code-block:: python

        vehData = 'gs_input_demo.xlsx'

* Define the input dictionary for the dispacher.

    .. code-block:: python

        input = dict(input_file_name=vehData)

.. _end-library:

.. _start-dispacher1:

Dispatcher
----------
* Dispatcher will select and execute the proper functions for the given inputs and the requested outputs

  .. code-block:: python

    core = dsp(input, outputs=['sol'], shrink=True)

.. _end-dispacher1:

* Plot workflow of the core model from the dispatcher

  .. code-block:: python

      core.plot()

  This will automatically open an internet browser and show the work flow of the core model as below.
  You can click all the rectangular boxes to see in detail sub models like load, model, write and plot.

    .. figure:: ./doc/_static/images/core_plot.PNG
        :align: center
        :alt: alternate text
        :figclass: align-center

  The load module

    .. figure:: ./doc/_static/images/load_core_plot.PNG
        :align: center
        :alt: alternate text
        :figclass: align-center

.. _start-dispacher2:

* Load outputs of dispatcher Select the chosen dictionary key (sol) from the given dictionary.

    .. code-block:: python

        solution = sh.selector(['sol'], sh.selector(['sol'], core))

* Select each output case

    .. code-block:: python

        # Select first case
        solution['sol'][0]

        # Select second case case
        solution['sol'][1]

        # Select gears output for different cases
        gears = {}
        for sol in solution['sol']:
            gears[f'gears_{sol["Case"]}'] = sol['GearsOutput']

.. _end-dispacher2:

© Copyright (c) 2021 European Union.

.. _start-sub:

.. |python-ver| image::  https://img.shields.io/badge/PyPi%20python-3.5%20%7C%203.6%20%7C%203.7%20%7C%203.8-informational
    :alt: Supported Python versions of latest release in PyPi

.. |gh-version| image::  https://img.shields.io/badge/GitHub%20release-1.1.3-orange
    :target: https://github.com/JRCSTU/gearshift/releases
    :alt: Latest version in GitHub

.. |rel-date| image:: https://img.shields.io/badge/rel--date-20--05--2021-orange
    :target: https://github.com/JRCSTU/gearshift/releases
    :alt: release date

.. |br| image:: https://img.shields.io/badge/docs-working%20on%20that-red
    :alt: GitHub page documentation

.. |doc| image:: https://img.shields.io/badge/docs-passing-success
    :alt: GitHub page documentation

.. |proj-lic| image:: https://img.shields.io/badge/license-European%20Union%20Public%20Licence%201.2-lightgrey
    :target:  https://joinup.ec.europa.eu/software/page/eupl
    :alt: EUPL 1.2

.. |codestyle| image:: https://img.shields.io/badge/code%20style-black-black.svg
    :target: https://github.com/ambv/black
    :alt: Code Style

.. |pypi-ins| image:: https://img.shields.io/badge/pypi-v1.1.3-informational
    :target: https://pypi.org/project/wltp-gearshift/
    :alt: pip installation

.. |binder| image:: https://mybinder.org/badge_logo.svg
    :target: https://mybinder.org/v2/gh/JRCSTU/gearshift_calculation_tool/main?urlpath=lab/tree/Notebooks/GUI_binder_interface.ipynb
    :alt: JupyterLab for Gerashift Calculation Tool (stable)

.. |CO2| replace:: CO\ :sub:`2`
.. _end-sub:
