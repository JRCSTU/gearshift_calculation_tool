# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Functions and `dsp` model to load data from a GEARSHIFT input file.

Sub-Modules:

.. currentmodule:: gearshift.core.load

.. autosummary::
    :nosignatures:
    :toctree: load/

    excel
"""

import io
import os
import logging
import pandas as pd
import schedula as sh
from .excel import parse_excel_file

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="load_inputs",
    description="Loads from files the inputs for the GEARSHIFT model.",
)


# noinspection PyUnusedLocal
def check_file_format(input_file_name, *args, ext=(".xlsx",)):
    """
    Check file format extension.

    :param input_file_name:
        Input file name.
    :type input_file_name: str

    :param ext:
        Allowed extensions.
    :type ext: tuple[str]

    :return:
        If the extension of the input file is within the allowed extensions.
    :rtype: bool
    """
    import pandas as pd

    f = input_file_name
    xl = pd.ExcelFile(f)
    l = len(xl.sheet_names)
    if l < 6:
        return input_file_name.lower().endswith(ext)


@sh.add_function(dsp, outputs=["input_file"], input_domain=check_file_format)
def open_input_file(input_file_name):
    """
    Open the input file.

    :param input_file_name:
        Input file name.
    :type input_file_name: str

    :return:
        Input file.
    :rtype: io.BytesIO
    """
    with open(input_file_name, "rb") as file:
        return io.BytesIO(file.read())


dsp.add_function(
    function=parse_excel_file,
    inputs=["input_file_name", "input_file"],
    outputs=["raw_data"],
    input_domain=check_file_format,
)


# noinspection PyUnusedLocal
def check_file_format_co2mpas(input_file_name, *args, ext=(".xlsx",)):
    """
    Check file format extension.

    :param input_file_name:
        Input file name.
    :type input_file_name: str

    :param ext:
        Allowed extensions.
    :type ext: tuple[str]

    :return:
        If the extension of the input file is within the allowed extensions.
    :rtype: bool
    """
    import pandas as pd

    f = input_file_name
    xl = pd.ExcelFile(f)
    l = len(xl.sheet_names)
    if l > 6:
        return input_file_name.lower().endswith(ext)


def _mergeDict(dict1, dict2):
    """ Merge dictionaries and keep values of common keys in list"""
    for key in dict2.keys():
        if key in dict1:
            dict1[key].update(dict2[key])
        else:
            dict1[key] = dict2[key]

    return dict1


@sh.add_function(
    dsp,
    inputs_kwargs=True,
    outputs=["raw_data"],
    input_domain=check_file_format_co2mpas,
)
def load_excel_file(input_file_name):
    from co2mpas.core.load import dsp as _load

    data = _load({"input_file_name": input_file_name})

    input_data = sh.get_nested_dicts(
        data,
        "raw_data",
        "base",
        "input",
        "calibration",
    )

    target_data = sh.get_nested_dicts(
        data,
        "raw_data",
        "base",
        "target",
        "calibration",
    )

    keys_case = (
        "capped_velocity",
        "hs_n_min1",
        "hs_n_min12",
        "hs_n_min2d",
        "hs_n_min2",
        "hs_n_min3",
        "hs_n_min3a",
        "hs_n_min3d",
        "hs_n_min3as",
        "hs_n_min3ds",
        "hs_t_start",
        "hs_supp0",
        "hs_excl1",
        "hs_autom",
        "hs_n_lim",
        "asm_margin",
    )

    final_input = _mergeDict(input_data, target_data)

    case = {
        cycle: sh.selector(keys_case, d, allow_miss=True) for cycle, d in final_input.items()
    }
    case = dict(filter(lambda x: bool(x[1]) != False, case.items()))

    keys_vehicle = (
        "engine_max_power",
        "engine_speed_at_max_power",
        "idle_engine_speed_median",
        "vehicle_mass",
        "f0",
        "f1",
        "f2",
    )
    vehicle = {
        cycle: sh.selector(keys_vehicle, d, allow_miss=True) for cycle, d in final_input.items()
    }
    vehicle = dict(filter(lambda x: bool(x[1]) != False, vehicle.items()))

    keys_engine = {
        "full_load_speeds",
        "full_load_powers",
    }
    engine = {
        cycle: sh.selector(keys_engine, d, allow_miss=True) for cycle, d in final_input.items()
    }
    engine = dict(filter(lambda x: bool(x[1]) != False, engine.items()))

    keys_speed_phase_data = {
        "times",
        "obd_velocities"
    }
    speed_phase_data = {
        cycle: sh.selector(keys_speed_phase_data, d, allow_miss=True) for cycle, d in final_input.items()
    }
    speed_phase_data = dict(filter(lambda x: bool(x[1]) != False, speed_phase_data.items()))

    raw_data = {
        "case": case,
        "vehicle": vehicle,
        "engine": engine,
        "speed_phase_data": speed_phase_data
    }

    return raw_data


def _load_speed_phase_data():
    """
    Load speed phase data
    :return:
        Speed phase data dict
    :rtype: dict
    """
    dir = os.path.dirname(__file__) + "/speed_phases/"

    speed_phases_dict = {}

    for file in os.listdir(dir):
        name = file.split(".")[0]
        data = pd.read_feather(dir + file, columns=None, use_threads=True)
        speed_phases_dict[name] = data

    return speed_phases_dict


@sh.add_function(dsp, inputs_kwargs=True, outputs=["data"])
def merge_data(raw_data):
    """
    Merge raw data with the speed phases data

    :param raw_data:
        Raw input data.
    :type raw_data: dict
    :return:
        Merged raw data
    :rtype: dict
    """
    speed_phase_data = _load_speed_phase_data()
    data = {**speed_phase_data, **raw_data}
    return data


@sh.add_function(dsp, inputs_kwargs=True, outputs=["base"])
def _validation(data):
    base = data
    return base
