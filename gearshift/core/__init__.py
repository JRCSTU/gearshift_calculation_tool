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
from .model import dsp as _model
from .write import dsp as _write

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(name="core", description="Processes a GEARSHIFT input file.")

dsp.add_dispatcher(
    dsp=_load, inputs=("input_file_name", "input_file"), outputs=("base", "dice")
)


@sh.add_function(dsp, outputs=["model"])
def register_model():
    """
    Register core model.

    :return:
        CO2MPAS core model.
    :rtype: schedula.Dispatcher
    """
    from .model import dsp

    return dsp.register(memo={})


def _obtain_inputs(case, base):
    to_del = ["case", "vehicle", "class", "merge", "m_ro", "phase"]

    case_rename = {
        "do_dsc": "ApplyDownscaling",
        "do_cap": "ApplySpeedCap",
        "do_cmp": "ApplyDistanceCompensation",
        "calc_dsc": "UseCalculatedDownscalingPercentage",
        "f_dsc": "DownscalingPercentage",
        "v_cap": "CappedSpeed",
        "n_min1": "MinDriveEngineSpeed1st",
        "n_min12": "MinDriveEngineSpeed1stTo2nd",
        "n_min2d": "MinDriveEngineSpeed2ndDecel",
        "n_min2": "MinDriveEngineSpeed2nd",
        "n_min3": "MinDriveEngineSpeedGreater2nd",
        "n_min3a": "MinDriveEngineSpeedGreater2ndAccel",
        "n_min3d": "MinDriveEngineSpeedGreater2ndDecel",
        "n_min3as": "MinDriveEngineSpeedGreater2ndAccelStartPhase",
        "n_min3ds": "MinDriveEngineSpeedGreater2ndDecelStartPhase",
        "t_start": "TimeEndOfStartPhase",
        "supp0": "SuppressGear0DuringDownshifts",
        "excl1": "ExcludeCrawlerGear",
        "autom": "AutomaticClutchOperation",
        "n_lim": "EngineSpeedLimitVMax",
        "asm_0": "AdditionalSafetyMargin0",
        "n_asm_s": "StartEngineSpeed",
        "n_asm_e": "EndEngineSpeed",
    }
    vehicle_rename = {
        "p_rated": "RatedEnginePower",
        "n_rated": "RatedEngineSpeed",
        "n_idle": "IdlingEngineSpeed",
        "n_max1": "Max95EngineSpeed",
        "#g": "NoOfGears",
        "m_test": "VehicleTestMass",
        "f_dsc": "DownscalingPercentage",
        "n_lim": "EngineSpeedLimitVMaxVehicle",
        "f0": "f0",
        "f1": "f1",
        "f2": "f2",
        "SM": "SafetyMargin",
    }

    phase_rename = {"length": "PhaseLengths"}

    gear_box_rename = {"gear": "gear_nbrs", "ndv": "Ndv"}

    scale_rename = {
        "algo": "ScalingAlgorithms",
        "t_beg": "ScalingStartTimes",
        "t_max": "ScalingCorrectionTimes",
        "t_end": "ScalingEndTimes",
        "r0": "r0",
        "a1": "a1",
        "b1": "b1",
    }

    FullPowerCurve = (
        base["engine"]
        .loc[base["engine"]["vehicle"] == case["vehicle"]]
        .drop(["vehicle"], axis=1)
        .to_numpy()
    )
    FullPowerCurve[:, 2] *= 100

    gear_box_ratios = {
        gear_box_rename[k]: v
        for k, v in base["gear_box_ratios"]
        .loc[base["gear_box_ratios"]["vehicle"] == case["vehicle"]]
        .to_dict("list")
        .items()
        if not k in to_del
    }

    Trace = (
        base["trace"]
        .loc[base["trace"]["class"] == case["class"]]
        .drop(["class"], axis=1)
        .to_numpy()
    )

    input_case = {
        case_rename[k]: v for k, v in case.to_dict().items() if not k in to_del
    }

    vehicle = {
        vehicle_rename[k]: v
        for k, v in base["vehicle"]
        .loc[base["vehicle"]["vehicle"] == case["vehicle"]]
        .to_dict("records")[0]
        .items()
        if not k in to_del
    }

    scale = {
        scale_rename[k]: v
        for k, v in base["scale"]
        .loc[base["scale"]["class"] == case["class"]]
        .to_dict("records")[0]
        .items()
        if not k in to_del
    }

    phase = {
        phase_rename[k]: v
        for k, v in base["phase"]
        .loc[base["phase"]["class"] == case["class"]]
        .to_dict("list")
        .items()
        if not k in to_del
    }

    dicts = [
        {"FullPowerCurve": FullPowerCurve, "Trace": Trace},
        gear_box_ratios,
        input_case,
        vehicle,
        scale,
        phase,
    ]

    final_dict = {k: v for d in dicts for k, v in d.items()}

    input = {"execution_case": final_dict}

    return input


@sh.add_function(dsp, outputs=["sol"])
def run_model(base, model):
    from tqdm import tqdm

    sol, input, case = [], {}, base["case"]

    with tqdm(total=len(list(case.iterrows()))) as pbar:
        for index, row in case.iterrows():
            pbar.set_description("Executing gearshift model (case %i)" % index)

            input = _obtain_inputs(row, base)

            sol_case = model(dict(input))
            dict_case = {"Case": row.to_dict()["case"], "NoOfGears": sol_case['shift_poits']['NoOfGearsFinal']}
            for k, v in sh.stack_nested_keys(sol_case.get("shift_poits", {}), depth=2):
                if len(k) >= 2:
                    dict_case[str(k[1])] = v

            sol.append(dict_case)

            pbar.update(1)

    return sol


dsp.add_dispatcher(
    dsp=_write,
    inputs=("output_folder", "sol", "timestamp", "output_format"),
    outputs=("output_file_name", sh.SINK),
)
