# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Functions to read inputs from dice excel template.
"""

import pandas as pd
import logging
import schedula as sh
from co2mpas.core.load import dsp as _load

log = logging.getLogger(__name__)


def _mergeDict(dict1, dict2):
    """ Merge dictionaries and keep values of common keys in list"""
    for key in dict2.keys():
        if key in dict1:
            dict1[key].update(dict2[key])
        else:
            dict1[key] = dict2[key]

    return dict1


def _get_class(vehicle_data):
    class_dict = {}
    for k, v in vehicle_data.items():
        try:
            if "vehicle_mass_running_order" in v:
                pmr = (v["engine_max_power"] * 1000) / (
                    v["vehicle_mass_running_order"] - 75
                )
            elif "vehicle_mass" in v:
                pmr = (v["engine_max_power"] * 1000) / (v["vehicle_mass"] - 75)

            if pmr <= 22:
                veh_class = "class 1"
            if 22 < pmr <= 34:
                veh_class = "class 2"
            if pmr > 34:
                if v["maximum_velocity"] < 120:
                    veh_class = "class 3a"
                if v["maximum_velocity"] >= 120:
                    veh_class = "class 3a"

            class_dict[k] = veh_class
        except:
            log.warning(
                "In the %s cycle can't be obtained the vehicle class, please check that you have Rated engine power "
                "and Mass of the vehicle in running order or Test mass as a input" % (k)
            )

    return class_dict


def _load_excel_file(input_file_name):

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

    final_input = _mergeDict(input_data, target_data)
    veh_class = _get_class(final_input)
    differences = set(final_input.keys()) ^ set(veh_class.keys())

    for k in differences:
        del final_input[k]

    for k, v in veh_class.items():
        final_input[k]["class"] = v

    keys_vehicle = (
        "engine_max_power",
        "engine_speed_at_max_power",
        "idle_engine_speed_median",
        "vehicle_mass_running_order",
        "vehicle_mass",
        "maximum_velocity",
        "idle_engine_speed_median",
        "f0",
        "f1",
        "f2",
    )

    vehicle = {
        cycle: sh.selector(keys_vehicle, d, allow_miss=True)
        for cycle, d in final_input.items()
    }
    vehicle = dict(filter(lambda x: bool(x[1]) != False, vehicle.items()))

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
        "class",
    )
    case = {
        cycle: sh.selector(keys_case, d, allow_miss=True)
        for cycle, d in final_input.items()
    }
    case = dict(filter(lambda x: bool(x[1]) != False, case.items()))

    keys_engine = {
        "full_load_speeds",
        "full_load_powers",
    }
    engine = {
        cycle: sh.selector(keys_engine, d, allow_miss=True)
        for cycle, d in final_input.items()
    }
    engine = dict(filter(lambda x: bool(x[1]) != False, engine.items()))

    keys_speed_phase_data = {"times", "obd_velocities"}
    speed_phase_data = {
        cycle: sh.selector(keys_speed_phase_data, d, allow_miss=True)
        for cycle, d in final_input.items()
    }
    speed_phase_data = dict(
        filter(lambda x: bool(x[1]) != False, speed_phase_data.items())
    )

    gbr_keys = {"final_drive_ratios", "gear_box_ratios", "tyre_code"}
    gear_box_ratios = {
        cycle: sh.selector(gbr_keys, d, allow_miss=True)
        for cycle, d in final_input.items()
    }
    gear_box_ratios = dict(
        filter(lambda x: bool(x[1]) != False, gear_box_ratios.items())
    )

    return case, vehicle, engine, speed_phase_data, gear_box_ratios


def _transform_vehicle_data(vehicle, gear_box_ratios, type_cols):

    vehicle_keys = {
        "engine_max_power": "p_rated",
        "engine_speed_at_max_power": "n_rated",
        "idle_engine_speed_median": "n_idle",
        "vehicle_mass": "m_test",
    }

    vehicle_calc = {
        "n_max1": 0.0,
        "SM": 0.1,
    }

    frames = []

    for k, v in vehicle.items():
        vehicle_dict = {
            (vehicle_keys[ki] if ki in vehicle_keys else ki): vi for ki, vi in v.items()
        }
        vehicle_dict = {
            **vehicle_calc,
            **{"#g": len(gear_box_ratios[k]["gear_box_ratios"]), "vehicle": k},
            **vehicle_dict,
        }

        df = pd.DataFrame.from_dict(vehicle_dict, orient="index").T

        frames.append(df)

    vehicle_df = pd.concat(frames, ignore_index=True)

    vehicle_df = vehicle_df.astype(type_cols)

    return vehicle_df


def _transform_engine_data(engine, type_cols):

    engine_keys = {
        "full_load_speeds": "n",
        "full_load_powers": "p",
    }

    engine_calc = {"ASM": 0.0}

    frames = []

    for k, v in engine.items():
        engine_dict = {
            (engine_keys[ki] if ki in engine_keys else ki): vi for ki, vi in v.items()
        }
        engine_dict = {
            **engine_calc,
            **{"vehicle": k},
            **engine_dict,
        }
        df = pd.DataFrame.from_dict(engine_dict)
        frames.append(df)

    engine_df = pd.concat(frames, ignore_index=True)

    engine_df = engine_df[["vehicle", "n", "p", "ASM"]]

    engine_df = engine_df.astype(type_cols)

    return engine_df


def _transform_speed_phase_data(speed_phase_data, case, type_cols):

    speed_phase_data_keys = {
        "times": "t",
        "obd_velocities": "v",
    }

    classes = list(map(lambda x: x.get("class"), case.values()))

    i = 0

    frames = []

    for k, v in speed_phase_data.items():
        speed_phase_data_dict = {
            (speed_phase_data_keys[ki] if ki in speed_phase_data_keys else ki): vi
            for ki, vi in v.items()
        }
        if len(list(set(classes))) != len(classes):
            speed_phase_data_dict["class"] = case[k].get("class") + str(i)
            case[k]["class"] = case[k].get("class") + str(i)
        else:
            speed_phase_data_dict["class"] = case[k].get("class")

        i += 1

        df = pd.DataFrame.from_dict(speed_phase_data_dict)

        frames.append(df)

    speed_phase_data_df = pd.concat(frames, ignore_index=True)

    speed_phase_data_df = speed_phase_data_df[["t", "v", "class"]]

    speed_phase_data_df = speed_phase_data_df.astype(type_cols)

    return speed_phase_data_df, case


def _transform_gear_box_ratios(gear_box_ratios, type_cols):

    from co2mpas.core.model.physical import dsp

    inputs = ["final_drive_ratio", "gear_box_ratios", "tyre_code"]
    outputs = ["r_dynamic"]
    dsp = dsp.register().shrink_dsp(inputs=inputs, outputs=outputs)
    func = sh.SubDispatchFunction(
        dsp, "get_gear_box_ratios", inputs=inputs, outputs=outputs
    )

    frames = []

    for k, v in gear_box_ratios.items():
        gear_box_ratios_dict = {
            "ndv": func(
                final_drive_ratio=gear_box_ratios[k]["final_drive_ratios"],
                gear_box_ratios=gear_box_ratios[k]["gear_box_ratios"],
                tyre_code=gear_box_ratios[k]["tyre_code"],
            ),
        }

        df = pd.DataFrame.from_dict(gear_box_ratios_dict)

        frames.append(df)

    gear_box_ratios_df = pd.concat(frames, ignore_index=True)

    gear_box_ratios_df = gear_box_ratios_df[["vehicle", "gear", "ndv"]]

    gear_box_ratios_df = gear_box_ratios_df.astype(type_cols)

    return gear_box_ratios_df


def _transform_case(case, speed_phase_data, vehicle, engine, type_cols):

    case_keys = {
        "hs_n_min1": "n_min1",
        "hs_n_min12": "n_min12",
        "hs_n_min2d": "n_min2d",
        "hs_n_min2": "n_min2",
        "hs_n_min3": "n_min3",
        "hs_n_min3a": "n_min3a",
        "hs_n_min3d": "n_min3d",
        "hs_n_min3as": "n_min3as",
        "hs_n_min3ds": "n_min3ds",
        "hs_t_start": "t_start",
        "hs_supp0": "supp0",
        "hs_excl1": "excl1",
        "hs_autom": "autom",
        "hs_n_lim": "n_lim",
        "capped_velocity": "v_cap",
    }

    frames = []

    for k, v in case.items():
        case_dict = {
            (case_keys[ki] if ki in case_keys else ki): vi for ki, vi in v.items()
        }

        case_default = {"v_cap": 0.0}

        case_dict = {**case_default, **case_dict}

        case_calc = {
            "do_dsc": (
                True
                if vehicle[k]["maximum_velocity"]
                < max(speed_phase_data[k]["obd_velocities"])
                or 0 != case_dict["v_cap"] < max(speed_phase_data[k]["obd_velocities"])
                else False
            ),
            "do_cap": True if case_dict["v_cap"] != 0.0 else False,
            "do_cmp": (
                True
                if vehicle[k]["maximum_velocity"]
                < max(speed_phase_data[k]["obd_velocities"])
                or 0 != case_dict["v_cap"] < max(speed_phase_data[k]["obd_velocities"])
                else False
            ),
            "case": k,
            "vehicle": k,
            "calc_dsc": False,
            "f_dsc": 0,
            "n_min1": 0,
            "n_min12": 0,
            "n_min2d": 0,
            "n_min2": 0,
            "n_min3": vehicle[k]["idle_engine_speed_median"]
            + 0.125
            * (
                max(engine[k]["full_load_speeds"])
                - vehicle[k]["idle_engine_speed_median"]
            ),
            "n_min3a": 0,
            "n_min3d": 0,
            "n_min3as": 0,
            "n_min3ds": 0,
            "t_start": 0,
            "supp0": False,
            "excl1": False,
            "autom": False,
            "n_lim": 0,
            "asm_0": 0,
            "n_asm_s": 0,
            "n_asm_e": 0,
        }

        case_dict = {**case_calc, **case_dict}

        df = pd.DataFrame.from_dict(case_dict, orient="index").T

        frames.append(df)

    case_df = pd.concat(frames, ignore_index=True)

    case_df = case_df.astype(type_cols)

    return case_df


def load_dice_file(input_file_name):
    """
    Reads cycle's data and simulation plans from DICE template.

    :param input_file_name:
        Input file name.
    :type input_file_name: str

    :return:
        Raw input data.
    :rtype: dict
    """

    type_cols = {
        "case": {
            "case": "str",
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
        "engine": {
            "vehicle": "str",
            "n": "float64",
            "p": "float64",
            "ASM": "float64",
        },
        "gearbox_ratios": {"vehicle": "str", "gear": "int32", "ndv": "float64"},
        "speed_phase": {"class": "str", "t": "float64", "v": "float"},
    }

    case, vehicle, engine, speed_phase_data, gear_box_ratios = _load_excel_file(
        input_file_name
    )

    vehicle_df = _transform_vehicle_data(vehicle, gear_box_ratios, type_cols["vehicle"])
    engine_df = _transform_engine_data(engine, type_cols["engine"])
    speed_phase_data_df, case = _transform_speed_phase_data(
        speed_phase_data, case, type_cols["speed_phase"]
    )
    gear_box_ratios_df = _transform_gear_box_ratios(
        gear_box_ratios, type_cols["gearbox_ratios"]
    )
    case_df = _transform_case(
        case, speed_phase_data, vehicle, engine, type_cols["case"]
    )

    raw_data = {
        "vehicle": vehicle_df,
        "engine": engine_df,
        "trace": speed_phase_data_df,
        "gearbox_ratios": gear_box_ratios_df,
        "case": case_df,
    }

    return raw_data
