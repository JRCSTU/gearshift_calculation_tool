# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
It provides GEARSHIFT model `dsp` to obtain the speed trace following Sub-Annex 1 of the Annex XXI from the
COMMISSION REGULATION (EU) 2017/1151.

Docstrings should provide sufficient understanding for any individual function.

Sub-Modules:

.. currentmodule:: gearshift.core.model.physical

.. autosummary::
    :nosignatures:
    :toctree: calculateShiftpointsNdvFullPC/
"""

import schedula as sh
import sys
import logging
import numpy as np

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="GEARSHIFT calculateShiftpointsNdvFullPC model",
    description="This function calibrates the speed trance, following the Sub-Annex 2",
)


@sh.add_function(dsp, outputs=["TraceTimesInput", "RequiredVehicleSpeedsInput"])
def parse_speed_trace(speed_trace):
    TraceTimesInput = speed_trace["ApplicableTrace"]["compensatedTraceTimes"]
    RequiredVehicleSpeedsInput = speed_trace["ApplicableTrace"][
        "compensatedVehicleSpeeds"
    ]
    return TraceTimesInput, RequiredVehicleSpeedsInput


@sh.add_function(
    dsp, outputs=["TraceTimes", "RequiredVehicleSpeeds", "TraceTimesCount"],
)
def resample_trace(TraceTimesInput, RequiredVehicleSpeedsInput):
    from scipy.interpolate import interp1d

    TraceTimes = np.arange(int(TraceTimesInput[-1] + 1)).astype(int)
    RequiredVehicleSpeeds = np.around(
        interp1d(TraceTimesInput.astype(int), RequiredVehicleSpeedsInput)(TraceTimes), 4
    )
    TraceTimesCount = len(TraceTimes)
    return TraceTimes, RequiredVehicleSpeeds, TraceTimesCount


@sh.add_function(dsp, outputs=["Phases", "InDecelerationToStandstill"])
def identify_phases(TraceTimesCount, RequiredVehicleSpeeds):
    PHASE_TOO_SHORT = 0
    PHASE_STANDSTILL = 1
    PHASE_ACCELERATION = 2
    PHASE_ACCELERATION_FROM_STANDSTILL = 3
    PHASE_DECELERATION = 4
    PHASE_DECELERATION_TO_STANDSTILL = 5
    PHASE_CONSTANT_SPEED = 6

    Phases = np.zeros(TraceTimesCount)

    dif_RequiredVehicleSpeeds = np.copy(RequiredVehicleSpeeds)
    dif_RequiredVehicleSpeeds = np.insert(dif_RequiredVehicleSpeeds, 0, 0)

    np.put(Phases, np.where(RequiredVehicleSpeeds < 1), PHASE_STANDSTILL)
    np.put(
        Phases,
        np.intersect1d(
            np.where(RequiredVehicleSpeeds >= 1),
            np.where(np.diff(dif_RequiredVehicleSpeeds) > 0)[0] - 1,
        ),
        PHASE_ACCELERATION,
    )
    np.put(
        Phases,
        np.intersect1d(
            np.where(RequiredVehicleSpeeds >= 1),
            np.where(np.diff(dif_RequiredVehicleSpeeds) <= 0)[0] - 1,
        ),
        PHASE_DECELERATION,
    )
    np.put(
        Phases,
        np.intersect1d(
            np.where(RequiredVehicleSpeeds >= 1),
            np.where(np.abs(np.diff(dif_RequiredVehicleSpeeds)) <= 0)[0] - 1,
        ),
        PHASE_CONSTANT_SPEED,
    )

    InAccelerationAnyDuration = np.zeros(TraceTimesCount)
    np.put(
        InAccelerationAnyDuration,
        np.where(Phases == PHASE_ACCELERATION),
        PHASE_STANDSTILL,
    )

    PhaseEnds = np.append(np.where(Phases[0:-1] - Phases[1:] != 0)[0], len(Phases) - 1)
    PhaseLengths = np.diff(np.insert(PhaseEnds, 0, 0))
    PhaseValues = Phases[PhaseEnds]
    PreviousPhaseValues = np.insert(PhaseValues[:-1], 0, 0)
    NextPhaseValues = np.append(PhaseValues[1:], 0)

    np.put(
        PhaseValues,
        np.intersect1d(
            np.where(PhaseValues == PHASE_ACCELERATION),
            np.where(PreviousPhaseValues == PHASE_STANDSTILL),
        ),
        PHASE_ACCELERATION_FROM_STANDSTILL,
    )

    np.put(
        PhaseValues,
        np.intersect1d(
            np.where(PhaseValues == PHASE_DECELERATION),
            np.where(NextPhaseValues == PHASE_STANDSTILL),
        ),
        PHASE_DECELERATION_TO_STANDSTILL,
    )

    np.put(
        PhaseValues,
        np.intersect1d(
            np.where(PhaseLengths <= 2),
            np.where(PhaseValues != PHASE_CONSTANT_SPEED),
            np.where(PhaseValues != PHASE_STANDSTILL),
        ),
        PHASE_TOO_SHORT,
    )

    PhaseStarts = np.cumsum(np.insert(PhaseLengths[:-1], 0, 1))
    PhaseStarts[0] = 0
    PhaseChanges = np.zeros(TraceTimesCount)
    PhaseChanges[PhaseStarts] = 1
    Phases = PhaseValues[np.cumsum(PhaseChanges).astype(int) - 1]

    InStandStill, InAcceleration = np.zeros(len(Phases)), np.zeros(len(Phases))
    np.put(InStandStill, np.where(Phases == PHASE_STANDSTILL), 1)
    np.put(InAcceleration, np.where(Phases == PHASE_ACCELERATION), 1)
    np.put(InAcceleration, np.where(Phases == PHASE_ACCELERATION_FROM_STANDSTILL), 1)

    InAccelerationFromStandstill, InDeceleration = (
        np.zeros(len(Phases)),
        np.zeros(len(Phases)),
    )
    np.put(
        InAccelerationFromStandstill,
        np.where(Phases == PHASE_ACCELERATION_FROM_STANDSTILL),
        1,
    )
    np.put(InDeceleration, np.where(Phases == PHASE_DECELERATION), 1)
    np.put(InDeceleration, np.where(Phases == PHASE_DECELERATION_TO_STANDSTILL), 1)

    InDecelerationToStandstill, InConstantSpeed = (
        np.zeros(len(Phases)),
        np.zeros(len(Phases)),
    )
    np.put(
        InDecelerationToStandstill,
        np.where(Phases == PHASE_DECELERATION_TO_STANDSTILL),
        1,
    )
    np.put(InConstantSpeed, np.where(Phases == PHASE_CONSTANT_SPEED), 1)

    return Phases, InDecelerationToStandstill


def _ExponentialDecayingASM(
    EngineSpeed, AdditionalSafetyMargin0, StartEngineSpeed, EndEngineSpeed
):
    if AdditionalSafetyMargin0 == 0:
        ASM = 0
    elif EndEngineSpeed <= StartEngineSpeed:
        ASM = AdditionalSafetyMargin0
    else:
        ASM = AdditionalSafetyMargin0 * np.exp(
            np.log(0.5 / AdditionalSafetyMargin0)
            * (EngineSpeed - StartEngineSpeed)
            / (EngineSpeed - StartEngineSpeed)
        )
    return ASM


@sh.add_function(
    dsp, outputs=["PowerCurveEngineSpeeds", "PowerCurvePowers", "PowerCurveASM"]
)
def load_full_power_curve(
    FullPowerCurve, AdditionalSafetyMargin0, StartEngineSpeed, EndEngineSpeed
):
    if np.shape(FullPowerCurve)[1] == 2:
        ASM = []
        for i in range(np.shape(FullPowerCurve)[0]):
            ASM[i] = (
                np.round(
                    _ExponentialDecayingASM(
                        FullPowerCurve[0][i],
                        AdditionalSafetyMargin0,
                        StartEngineSpeed,
                        EndEngineSpeed,
                    )
                    * 10
                )
                / 10
            )

        FullPowerCurve = np.append(FullPowerCurve, ASM, axis=1)

    PowerCurveEngineSpeeds = FullPowerCurve[:, 0]
    PowerCurvePowers = FullPowerCurve[:, 1]
    PowerCurveASM = FullPowerCurve[:, 2]

    return PowerCurveEngineSpeeds, PowerCurvePowers, PowerCurveASM


@sh.add_function(dsp, outputs=["RatedEnginePower", "RatedEngineSpeed"])
def determine_rated_engine_power(
    RatedEnginePower, RatedEngineSpeed, PowerCurvePowers, PowerCurveEngineSpeeds
):
    if (RatedEnginePower is None or RatedEnginePower <= 0) and (
        RatedEngineSpeed is None or RatedEngineSpeed <= 0
    ):
        RatedEnginePower = np.max(PowerCurvePowers)
        idx = np.min(np.where(PowerCurvePowers == RatedEnginePower)[0])
        RatedEngineSpeed = PowerCurveEngineSpeeds[idx]
    return RatedEnginePower, RatedEngineSpeed


@sh.add_function(dsp, outputs=["Max95EngineSpeed"])
def determine_maximum_engine_speed_95(
    Max95EngineSpeed, PowerCurvePowers, PowerCurveEngineSpeeds
):
    if Max95EngineSpeed <= 0 or np.isnan(Max95EngineSpeed):
        PowerCurvePowerMax95 = 0.95 * np.max(PowerCurvePowers)
        if PowerCurvePowers[-1] >= PowerCurvePowerMax95:
            Max95EngineSpeed = PowerCurveEngineSpeeds[-1]
        else:
            logical = [1 if i >= PowerCurvePowerMax95 else 0 for i in PowerCurvePowers]
            idx = np.max(np.where(np.diff(logical) != 0)[0])
            if idx == 0:
                logging.error(
                    "Max95EngineSpeed can not be calculated from FullPowerCurve"
                )
            else:
                Max95EngineSpeed = PowerCurveEngineSpeeds[idx] + (
                    PowerCurvePowerMax95 - PowerCurvePowers[idx]
                ) / (PowerCurvePowers[idx + 1] - PowerCurvePowers[idx]) * (
                    PowerCurveEngineSpeeds[idx + 1] - PowerCurveEngineSpeeds[idx]
                )
    return Max95EngineSpeed


@sh.add_function(dsp, outputs=["MinDrivesI", "CalculatedMinDriveEngineSpeedGreater2nd"])
def minimum_engine_speed_in_motion(
    IdlingEngineSpeed,
    RatedEngineSpeed,
    MinDriveEngineSpeed1st,
    MinDriveEngineSpeed1stTo2nd,
    MinDriveEngineSpeed2ndDecel,
    MinDriveEngineSpeed2nd,
    MinDriveEngineSpeedGreater2nd,
    TraceTimesCount,
    NoOfGears,
    InDecelerationToStandstill,
):
    CalculatedMinDriveEngineSpeed1st = IdlingEngineSpeed
    CalculatedMinDriveEngineSpeed1stTo2nd = np.round(1.15 * IdlingEngineSpeed)
    CalculatedMinDriveEngineSpeed2ndDecel = IdlingEngineSpeed
    CalculatedMinDriveEngineSpeed2nd = 0.9 * IdlingEngineSpeed
    CalculatedMinDriveEngineSpeedGreater2nd = IdlingEngineSpeed + 0.125 * (
        RatedEngineSpeed - IdlingEngineSpeed
    )

    MinDrive1st = np.round(
        max(CalculatedMinDriveEngineSpeed1st, MinDriveEngineSpeed1st)
    )
    MinDrive1stTo2nd = np.round(
        max(CalculatedMinDriveEngineSpeed1stTo2nd, MinDriveEngineSpeed1stTo2nd)
    )
    MinDrive2ndDecel = np.round(
        max(CalculatedMinDriveEngineSpeed2ndDecel, MinDriveEngineSpeed2ndDecel)
    )
    MinDrive2nd = np.round(
        max(CalculatedMinDriveEngineSpeed2nd, MinDriveEngineSpeed2nd)
    )
    MinDriveGreater2nd = np.round(
        max(CalculatedMinDriveEngineSpeedGreater2nd, MinDriveEngineSpeedGreater2nd)
    )

    MinDrivesI = np.zeros((TraceTimesCount, NoOfGears))
    MinDrivesI[:, 0] = MinDrive1st
    MinDrivesI[:, 1] = MinDrive2nd
    MinDrivesI[:, 2:NoOfGears] = MinDriveGreater2nd
    np.put(
        MinDrivesI[:, 1], np.where(InDecelerationToStandstill != 0), MinDrive2ndDecel
    )

    return MinDrivesI, CalculatedMinDriveEngineSpeedGreater2nd


def check_minimum_engine_speed(
    MinDrivesI,
    CalculatedMinDriveEngineSpeedGreater2nd,
    MinDriveEngineSpeedGreater2ndAccel,
    MinDriveEngineSpeedGreater2ndDecel,
    MinDriveEngineSpeedGreater2ndAccelStartPhase,
    MinDriveEngineSpeedGreater2ndDecelStartPhase,
    RequiredVehicleSpeeds,
    TimeEndOfStartPhase,
    TraceTimes,
    NoOfGears,
):
    check = []
    if MinDriveEngineSpeedGreater2ndAccel > 2 * CalculatedMinDriveEngineSpeedGreater2nd:
        logging.error(
            "MinDriveEngineSpeedGreater2ndAccel value %f must be less or equal "
            "2 * m_min_drive_set = %f"
            % (
                MinDriveEngineSpeedGreater2ndAccel,
                2 * CalculatedMinDriveEngineSpeedGreater2nd,
            )
        )
        check.append(False)
    else:
        check.append(True)

    if MinDriveEngineSpeedGreater2ndDecel > 2 * CalculatedMinDriveEngineSpeedGreater2nd:
        logging.error(
            "MinDriveEngineSpeedGreater2ndDecel value %f must be less or equal "
            "2 * m_min_drive_set = %f"
            % (
                MinDriveEngineSpeedGreater2ndDecel,
                2 * CalculatedMinDriveEngineSpeedGreater2nd,
            )
        )
        check.append(False)
    else:
        check.append(True)

    if MinDriveEngineSpeedGreater2ndDecelStartPhase > 2 * CalculatedMinDriveEngineSpeedGreater2nd:
        logging.error(
            "MinDriveEngineSpeedGreater2ndDecel value %f must be less or equal "
            "2 * m_min_drive_set = %f"
            % (
                MinDriveEngineSpeedGreater2ndDecelStartPhase,
                2 * CalculatedMinDriveEngineSpeedGreater2nd,
            )
        )
        check.append(False)
    else:
        check.append(True)

    if (
        MinDriveEngineSpeedGreater2ndAccelStartPhase
        > 2 * CalculatedMinDriveEngineSpeedGreater2nd
    ):
        logging.error(
            "MinDriveEngineSpeedGreater2ndDecel value %f must be less or equal "
            "2 * m_min_drive_set = %f"
            % (
                MinDriveEngineSpeedGreater2ndDecel,
                2 * CalculatedMinDriveEngineSpeedGreater2nd,
            )
        )
        check.append(False)
    else:
        check.append(True)

    InStandstillMinDrive = np.zeros(len(RequiredVehicleSpeeds))
    np.put(InStandstillMinDrive, np.where(RequiredVehicleSpeeds == 0), 1)

    if TimeEndOfStartPhase >= 0 and not bool(
        InStandstillMinDrive[TimeEndOfStartPhase + 1]
    ):
        logging.error("Vehicle speed at end of start phase must be zero")
        check.append(False)
    else:
        check.append(True)

    return all(check)


@sh.add_function(dsp, outputs=["MinDrives"], input_domain=check_minimum_engine_speed)
def define_minimum_engine_speed_in_motion(
    MinDrivesI,
    CalculatedMinDriveEngineSpeedGreater2nd,
    MinDriveEngineSpeedGreater2ndAccel,
    MinDriveEngineSpeedGreater2ndDecel,
    MinDriveEngineSpeedGreater2ndAccelStartPhase,
    MinDriveEngineSpeedGreater2ndDecelStartPhase,
    RequiredVehicleSpeeds,
    TimeEndOfStartPhase,
    TraceTimes,
    NoOfGears,
):
    accelerations = np.around(
        np.append(np.diff(RequiredVehicleSpeeds) / (3.6 * np.diff(TraceTimes)), 0), 4,
    )

    InAccelerationMinDrive = np.full(len(accelerations), 0)
    np.put(InAccelerationMinDrive, np.where(accelerations >= -0.1389), 1)
    InDecelerationMinDrive = np.full(len(accelerations), 1)
    np.put(InDecelerationMinDrive, np.where(accelerations >= -0.1389), 0)

    MinDrives = np.copy(MinDrivesI)
    np.put(
        MinDrives[:, 2:NoOfGears],
        np.where(InAccelerationMinDrive == 1),
        np.max(
            MinDrives[np.where(InAccelerationMinDrive == 1), 2:NoOfGears],
            initial=MinDriveEngineSpeedGreater2ndAccel,
        ),
    )
    np.put(
        MinDrives[:, 2:NoOfGears],
        np.where(InDecelerationMinDrive == 1),
        np.max(
            MinDrives[np.where(InDecelerationMinDrive == 1), 2:NoOfGears],
            initial=MinDriveEngineSpeedGreater2ndDecel,
        ),
    )

    InAccelerationMinDriveStartPhase = np.zeros(len(InAccelerationMinDrive))
    np.put(InAccelerationMinDriveStartPhase, np.intersect1d(np.where(TraceTimes <= TimeEndOfStartPhase),
                                                            np.where(InAccelerationMinDrive == 1)), 1)
    np.put(
        MinDrives[:, 2:NoOfGears],
        np.where(InAccelerationMinDriveStartPhase == 1),
        np.max(
            MinDrives[np.where(InAccelerationMinDriveStartPhase == 1), 2:NoOfGears],
            initial=MinDriveEngineSpeedGreater2ndAccelStartPhase,
        ),
    )

    InDecelerationMinDriveStartPhase = np.zeros(len(InAccelerationMinDrive))
    np.put(InDecelerationMinDriveStartPhase, np.intersect1d(np.where(TraceTimes <= TimeEndOfStartPhase),
                                                            np.where(InDecelerationMinDrive == 1)), 1)
    np.put(
        MinDrives[:, 2:NoOfGears],
        np.where(InDecelerationMinDriveStartPhase == 1),
        np.max(
            MinDrives[np.where(InDecelerationMinDriveStartPhase == 1), 2:NoOfGears],
            initial=MinDriveEngineSpeedGreater2ndDecelStartPhase,
        ),
    )
    MinDrives = np.rint(MinDrives)

    return MinDrives

@sh.add_function(dsp, outputs=["GearAtMaxVehicleSpeed"])
def determine_gear_in_maximum_vehicle_speed(PowerCurveEngineSpeeds, f0, f1, f2):

    RoadLoadSpeeds = np.arange(0.1, 500.1, 0.1)
    RoadLoadPowers = np.round((
        f0 * RoadLoadSpeeds
        + f1 * np.power(RoadLoadSpeeds, 2)
        + f2 * np.power(RoadLoadSpeeds, 3)
    )/3600, 4)


@sh.add_function(dsp, outputs=["a"])
def generate_gears(Phases):
    a = Phases
    return a
