# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Functions and `dsp` model to processes a CO2MPAS input file.

Sub-Modules:

.. currentmodule:: co2mpas.core

.. autosummary::
    :nosignatures:
    :toctree: core/

    load
    model
    report
    write
"""
import logging
import schedula as sh
import os.path as osp
from .load import dsp as _load

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(name="core", description="Processes a GEARSHIFT input file.")

dsp.add_dispatcher(
    dsp=_load,
    inputs=("input_file_name", "input_file"),
    outputs=("base", "dice")
)


@sh.add_function(dsp, outputs=['solution'])
def run_model(base, dice):
    solution = base
    sol = dice
    return solution
