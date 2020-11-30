# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Functions and `dsp` model to load data from a GEARSHIFT input file.

Sub-Modules:

.. currentmodule:: gearshift.core.write

.. autosummary::
    :nosignatures:
    :toctree: write/

    excel
    schema
    validate
"""
import os
import os.path as osp
import logging
from .excel import write_to_excel
import pandas as pd
import numpy as np
import schedula as sh

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="write",
    description="Produces a vehicle report from GEARSHIFT outputs.",
)


@sh.add_function(dsp, outputs=["fp"])
def default_output_file_name(output_folder, timestamp, case, output_format):
    """
    Returns the output file name.

    :param output_folder:
        Output folder.
    :type output_folder: str

    :param vehicle_name:
        Vehicle name.
    :type vehicle_name: str

    :param timestamp:
        Run timestamp.
    :type timestamp: str

    :param ext:
        File extension.
    :type ext: str | None

    :return:
        Output file name.
    :rtype: str

    """
    fp = osp.join(output_folder, "%s-%s" % (timestamp, case))
    if output_format is not None:
        fp = "%s.%s" % (fp, output_format)
    return fp


@sh.add_function(dsp, outputs=["case"])
def get_case(sol):
    if len(sol) == 1:
        case = "case-" + str(sol[0]["Case"])
    else:
        case = "multiple-cases"
    return case


@sh.add_function(dsp)
def save_output_file(sol, fp, output_folder):
    os.makedirs(osp.dirname(output_folder), exist_ok=True)
    for case in sol:
        dict_df = write_to_excel(case, fp)
