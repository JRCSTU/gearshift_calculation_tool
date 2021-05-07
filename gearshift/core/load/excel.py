# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Functions to read inputs from excel.
"""

import pandas as pd


def _read_columns(input_data):

    col_names = ["case", "vehicle", "engine", "gearbox_ratios"]

    columns = [x.lower().strip() for x in input_data.sheet_names]

    return [x for x in columns if x in col_names]


def _read_dataframe(col, dataframe):

    if col == "case":
        dataframe = dataframe.fillna(0)
        dataframe["do_dsc"] = 1
        dataframe["calc_dsc"] = 1
        dataframe["f_dsc"] = 0

    if col == "vehicle":
        dataframe["SM"] = 0.100

    type_cols = {
        "case": {
            "case": "int32",
            "vehicle": "str",
            "do_dsc": "int32",
            "do_cap": "int32",
            "do_cmp": "int32",
            "calc_dsc": "int32",
            "f_dsc": "float64",
            "v_cap": "float64",
            "class": "str",
            "n_min1": "float64",
            "n_min12": "float64",
            "n_min2d": "float64",
            "n_min2": "float64",
            "n_min3": "float64",
            "n_min3a": "float64",
            "n_min3d": "float64",
            "n_min3as": "float64",
            "n_min3ds": "float64",
            "t_start": "int32",
            "supp0": "int32",
            "excl1": "int32",
            "autom": "int32",
            "n_lim": "float64",
            "asm_0": "float64",
            "n_asm_s": "float64",
            "n_asm_e": "float64",
        },
        "vehicle": {
            "vehicle": "str",
            "p_rated": "float64",
            "n_rated": "float64",
            "n_idle": "float64",
            "n_max1": "float64",
            "#g": "int32",
            "m_test": "float64",
            "f0": "float64",
            "f1": "float64",
            "f2": "float64",
            "SM": "float64",
        },
        "engine": {"vehicle": "str", "n": "float64", "p": "float64", "ASM": "float64"},
        "gearbox_ratios": {"vehicle": "str", "gear": "int32", "ndv": "float64"},
    }

    caseDict = {
        "case": "int32",
        "vehicle": "str",
        "do_dsc": "bool",
        "do_cap": "bool",
        "do_cmp": "bool",
        "calc_dsc": "bool",
        "f_dsc": "float64",
        "v_cap": "float64",
        "class": "str",
        "n_min1": "float64",
        "n_min12": "float64",
        "n_min2d": "float64",
        "n_min2": "float64",
        "n_min3": "float64",
        "n_min3a": "float64",
        "n_min3d": "float64",
        "n_min3as": "float64",
        "n_min3ds": "float64",
        "t_start": "int32",
        "supp0": "bool",
        "excl1": "bool",
        "autom": "bool",
        "n_lim": "float64",
        "asm_0": "float64",
        "n_asm_s": "float64",
        "n_asm_e": "float64",
    }

    dataframe = dataframe.drop([0], axis=0)

    dataframe.columns = dataframe.columns.str.replace(" ", "")

    dataframe = dataframe.astype(type_cols[col])

    if col == "case":
        dataframe = dataframe.astype(caseDict)

    for string_column in dataframe.select_dtypes(include="object"):
        dataframe[string_column] = dataframe[string_column].str.replace(" ", "")

    return dataframe.reset_index(drop=True)


def parse_excel_file(input_file_name, input_file):
    """
    Reads cycle's data and simulation plans.

    :param input_file_name:
        Input file name.
    :type input_file_name: str

    :param input_file:
        Input file.
    :type input_file: io.BytesIO

    :return:
        Raw input data.
    :rtype: dict
    """
    raw_data = {}
    input_data = pd.ExcelFile(input_file, engine="openpyxl")
    columns = _read_columns(input_data)
    for col in columns:
        raw_data[col] = _read_dataframe(col, input_data.parse(col))
    raw_data["input_file"] = input_file_name
    return raw_data
