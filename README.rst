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
