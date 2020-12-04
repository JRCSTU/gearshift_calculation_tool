################################################################
Python Gearshift Calculation Tool
################################################################
:versions:      |gh-version| |rel-date| |python-ver|
:documentation: https://github.com/AndresLaverdeMarin/gearshift_calculation_tool |br|
:sources:       https://github.com/AndresLaverdeMarin/gearshift_calculation_tool |br|
:keywords:      automotive, car, cars, driving, engine, emissions, fuel-consumption,
                gears, gearshifts, rpm, simulation, simulator, standard, vehicle, vehicles, WLT
:copyright:     2013-2020 European Commission (`JRC-IET <https://ec.europa.eu/jrc/en/institutes/iet>`_)
                |proj-lic|

A python-3.6+ package to generate the *gear-shifts* of Light-duty vehicles


.. Attention::
    This *wltp* python project is still in *alpha* stage, in the sense that
    its results are not "correct" by the standard, and no WLTP dyno-tests should rely
    currently on them.

.. _end-opening:
.. contents:: Table of Contents
  :backlinks: top
.. _begin-intro:

Introduction
============

The aim of the Gearshift tool is obtain the Required Engine Speeds, the Available Powers, the Required Vehicle Speeds
and the Gears for the whole WLTC based on the vehicle characteristics. The model should allow accurate calculation
of final trace and the operating conditions of the engine.

Overview
--------
The calculator accepts as input the excel file  that contains the vehicle's technical data, along with parameters for
modifying the execution WLTC cycle, and it then spits-out the gear-shifts of the vehicle and the others parameters used
during the obtaining of these. It does not calculate any |CO2| emissions.

Prerequisites:
^^^^^^^^^^^^^^
**Python-3.6+** is required and **Python-3.7** recommended.
It requires **numpy/scipy** and **pandas** libraries with native backends.

.. Tip::
    On *Windows*, it is preferable to use the `Anaconda <https://www.anaconda.com/products/individual>` distribution.
    To avoid possible incompatibilities with other projects

Download:
^^^^^^^^^
Download the sources,

- either with *git*, by giving this command to the terminal::

      git clone https://github.com/AndresLaverdeMarin/gearshift_calculation_tool --depth=1

Install:
^^^^^^^^
From within the project directory, run one of these commands to install it:

- for standard python, installing with ``pip`` is enough (but might)::

      pip install -e .[path_to_gearshift_calculation_tool_folder]


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

Usage
=====

Cmd-line usage
--------------
The command-line usage below requires the Python environment to be installed, and provides for
executing an experiment directly from the OS's shell (i.e. ``cmd`` in windows or ``bash`` in POSIX),
and in a *single* command.  To have precise control over the inputs and outputs

.. code-block:: bash

    $ gearshift --help                                                  ## to get generic help for cmd-line syntax
    $ gearshift demo                                                    ## to get demo input file
    $ gearshift run "path_input_file" -O "path_to_save_output_file"     ## to run gearshift tool



.. |python-ver| image::  https://img.shields.io/badge/PyPi%20python-3.3%20%7C%203.4%20%7C%203.5%20%7C%203.6%20%7C%203.7-informational
    :alt: Supported Python versions of latest release in PyPi

.. |gh-version| image::  https://img.shields.io/badge/GitHub%20release-1.0.0-orange
    :alt: Latest version in GitHub

.. |rel-date| image:: https://img.shields.io/badge/rel--date-03--12--2020-orange
    :alt: release date

.. |br| image:: https://img.shields.io/badge/docs-working%20on%20that-red
    :alt: GitHub page documentation

.. |proj-lic| image:: https://img.shields.io/pypi/l/wltp.svg
    :target:  https://joinup.ec.europa.eu/software/page/eupl
    :alt: EUPL 1.1+

.. |CO2| replace:: CO\ :sub:`2`
