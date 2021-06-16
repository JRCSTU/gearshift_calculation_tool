# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 European Union;
# Licensed under the EUPL, Version 1.2 or – as soon they will be approved by the European Commission
# – subsequent versions of the EUPL (the "Licence");
#
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
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


@sh.add_function(dsp, outputs=["input_file"])
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
    f = input_file_name
    return input_file_name.lower().endswith(ext)


dsp.add_function(
    function=parse_excel_file,
    inputs=["input_file_name", "input_file"],
    outputs=["raw_data"],
    input_domain=check_file_format,
)


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
