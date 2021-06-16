# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 European Union;
# Licensed under the EUPL, Version 1.2 or – as soon they will be approved by the European Commission
# – subsequent versions of the EUPL (the "Licence");
#
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
"""
Functions to write outputs on an excel file.
"""
import pandas as pd
import numpy as np
import os.path as osp
from pathlib import Path
import io
import re


def _read_project_version():
    mydir = osp.dirname(__file__)
    gsdir = Path(mydir).parent.parent.absolute()
    fglobals = {}
    with io.open(osp.join(gsdir, "_version.py")) as fd:
        exec(fd.read(), fglobals)  # To read __version__
    return fglobals["__version__"]


def _dict2dataframes(solution_case):

    principal_sheet_output = {}
    TimeSeries = pd.DataFrame()
    dict_df = {}

    length = []
    for v in solution_case.values():
        if isinstance(v, np.ndarray):
            length.append(len(v))

    length = max(length)

    for k, v in solution_case.items():
        if not isinstance(v, (list, pd.core.series.Series, np.ndarray, dict)):
            kn = re.findall("[A-Z][^A-Z]*", k)
            kn = " ".join(kn)
            principal_sheet_output[kn] = [v]
        elif isinstance(v, np.ndarray):
            kn = re.findall("[A-Z][^A-Z]*", k)
            kn = " ".join(kn)
            if len(v) == length:
                if np.shape(v) == (length, solution_case["NoOfGears"]):
                    list_col = [i for i in range(1, solution_case["NoOfGears"] + 1)]
                    df = pd.DataFrame(v, columns=list_col)
                    dict_df[kn] = df
                else:
                    df = pd.DataFrame({kn: v})
                    TimeSeries = pd.concat([TimeSeries, df], axis=1)

    dict_df["Time Series"] = TimeSeries

    if "OriginalTrace" in solution_case.keys():
        dict_OT = {
            "Trace Times": solution_case["OriginalTrace"][0],
            "Vehicle Speeds": solution_case["OriginalTrace"][1],
        }
        OriginalTrace = pd.DataFrame(dict_OT)
        dict_df["Original Trace"] = OriginalTrace

    if "ApplicableTrace" in solution_case.keys():
        dict_AT = {
            "Trace Times": solution_case["ApplicableTrace"]["compensatedTraceTimes"],
            "Vehicle Speeds": solution_case["ApplicableTrace"][
                "compensatedVehicleSpeeds"
            ],
        }
        ApplicableTrace = pd.DataFrame(dict_AT)
        dict_df["Applicable Trace"] = ApplicableTrace
    principal_sheet_output["gearshift_version"] = _read_project_version()
    dict_df["Summary"] = pd.DataFrame(principal_sheet_output)

    return dict_df


def write_to_excel(solution_case, fp):
    """
    Save output file.

    :param solution_case:
        Dictionary that contain outputs.
    :type solution_case: dict

    :param fp:
        Output path and file name.
    :type fp: str
    """

    writer = pd.ExcelWriter(fp, engine="xlsxwriter")

    dict_df = _dict2dataframes(solution_case)

    for k, v in dict_df.items():
        v.to_excel(writer, sheet_name=k, na_rep=0, index=False)

        worksheet = writer.sheets[k]

        workbook = writer.book

        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "valign": "top",
                "fg_color": "#FABF8F",
                "border": 1,
            }
        )

        for idx, col in enumerate(v):  # loop through all columns
            series = v[col]
            max_len = (
                max(
                    (
                        series.astype(str).map(len).max(),  # len of largest item
                        len(str(series.name)),  # len of column name/header
                    )
                )
                + 1
            )  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)
            worksheet.write(0, idx, col, header_format)

        new_sheet_names = [
            "Summary",
            "Time Series",
            "Required Engine Speeds Output",
            "Available Powers Output",
            "Applicable Trace",
            "Original Trace",
        ]

        workbook.worksheets_objs.sort(key=lambda x: new_sheet_names.index(x.name))

    writer.save()
