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
import logging
from .corrections import *
import numpy as np


log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="GEARSHIFT calculateShiftpointsNdvFullPC model",
    description="This function calibrates the speed trance, following the Sub-Annex 2",
)


@sh.add_function(dsp, outputs=["NoOfGearsFinal", "Gears", "NdvRatios"])
def check_gears(NoOfGears, gear_nbrs, Ndv, ExcludeCrawlerGear):

    if ExcludeCrawlerGear:
        Gears = gear_nbrs[1:, :]
        NdvRatios = np.array(Ndv[1:])
        NoOfGearsFinal = NoOfGears - 1
    else:
        Gears = gear_nbrs
        NdvRatios = np.array(Ndv)
        NoOfGearsFinal = NoOfGears

    return NoOfGearsFinal, Gears, NdvRatios


@sh.add_function(dsp, outputs=["TraceTimesInput", "RequiredVehicleSpeedsInput"])
def parse_speed_trace(speed_trace):
    TraceTimesInput = speed_trace["ApplicableTrace"]["compensatedTraceTimes"]
    RequiredVehicleSpeedsInput = speed_trace["ApplicableTrace"][
        "compensatedVehicleSpeeds"
    ]
    return TraceTimesInput, RequiredVehicleSpeedsInput


@sh.add_function(
    dsp,
    outputs=["TraceTimes", "RequiredVehicleSpeeds", "TraceTimesCount"],
)
def resample_trace(TraceTimesInput, RequiredVehicleSpeedsInput):
    from scipy.interpolate import interp1d

    TraceTimes = np.arange(int(TraceTimesInput[-1] + 1)).astype(int)
    RequiredVehicleSpeeds = np.around(
        interp1d(TraceTimesInput.astype(int), RequiredVehicleSpeedsInput)(TraceTimes), 4
    )
    TraceTimesCount = len(TraceTimes)
    return TraceTimes, RequiredVehicleSpeeds, TraceTimesCount


@sh.add_function(
    dsp,
    outputs=[
        "Phases",
        "InDecelerationToStandstill",
        "PhaseValues",
        "InStandStill",
        "PhaseStarts",
        "PhaseEnds",
        "PHASE_ACCELERATION_FROM_STANDSTILL",
        "PHASE_ACCELERATION",
        "InAcceleration",
        "InConstantSpeed",
        "InAccelerationAnyDuration",
        "PHASE_DECELERATION",
        "PHASE_DECELERATION_TO_STANDSTILL",
        "InDeceleration",
        "PHASE_STANDSTILL",
    ],
)
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

    return (
        Phases,
        InDecelerationToStandstill,
        PhaseValues,
        InStandStill,
        PhaseStarts,
        PhaseEnds,
        PHASE_ACCELERATION_FROM_STANDSTILL,
        PHASE_ACCELERATION,
        InAcceleration,
        InConstantSpeed,
        InAccelerationAnyDuration,
        PHASE_DECELERATION,
        PHASE_DECELERATION_TO_STANDSTILL,
        InDeceleration,
        PHASE_STANDSTILL,
    )


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
    dsp,
    outputs=[
        "PowerCurveEngineSpeeds",
        "PowerCurvePowers",
        "PowerCurveASM",
        "DefinedPowerCurveAdditionalSafetyMargins",
    ],
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
    DefinedPowerCurveAdditionalSafetyMargins = True

    return (
        PowerCurveEngineSpeeds,
        PowerCurvePowers,
        PowerCurveASM,
        DefinedPowerCurveAdditionalSafetyMargins,
    )


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


@sh.add_function(dsp, outputs=["Max95EngineSpeedFinal"])
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
    Max95EngineSpeedFinal = Max95EngineSpeed

    return Max95EngineSpeedFinal


@sh.add_function(
    dsp,
    outputs=[
        "MinDrivesI",
        "CalculatedMinDriveEngineSpeedGreater2nd",
        "MinDrive1stTo2nd",
        "MinDrive1st",
        "MinDrive2ndDecel",
        "MinDrive2nd",
        "MinDriveGreater2nd",
    ],
)
def minimum_engine_speed_in_motion(
    IdlingEngineSpeed,
    RatedEngineSpeed,
    MinDriveEngineSpeed1st,
    MinDriveEngineSpeed1stTo2nd,
    MinDriveEngineSpeed2ndDecel,
    MinDriveEngineSpeed2nd,
    MinDriveEngineSpeedGreater2nd,
    TraceTimesCount,
    NoOfGearsFinal,
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

    NoOfGears = NoOfGearsFinal

    MinDrivesI = np.zeros((TraceTimesCount, NoOfGears))
    MinDrivesI[:, 0] = MinDrive1st
    MinDrivesI[:, 1] = MinDrive2nd
    MinDrivesI[:, 2:NoOfGears] = MinDriveGreater2nd
    np.put(
        MinDrivesI[:, 1], np.where(InDecelerationToStandstill != 0), MinDrive2ndDecel
    )

    return (
        MinDrivesI,
        CalculatedMinDriveEngineSpeedGreater2nd,
        MinDrive1stTo2nd,
        MinDrive1st,
        MinDrive2ndDecel,
        MinDrive2nd,
        MinDriveGreater2nd,
    )


@sh.add_function(dsp, outputs=["Accelerations"])
def get_accelerations(RequiredVehicleSpeeds, TraceTimes):
    a = RequiredVehicleSpeeds
    Accelerations = np.around(
        np.append(np.diff(RequiredVehicleSpeeds) / (3.6 * np.diff(TraceTimes)), 0),
        4,
    )

    return Accelerations


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
    NoOfGearsFinal,
    Accelerations,
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

    if (
        MinDriveEngineSpeedGreater2ndDecelStartPhase
        > 2 * CalculatedMinDriveEngineSpeedGreater2nd
    ):
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
    NoOfGearsFinal,
    Accelerations,
):

    NoOfGears = NoOfGearsFinal

    InAccelerationMinDrive = np.full(len(Accelerations), 0)
    np.put(InAccelerationMinDrive, np.where(Accelerations >= -0.1389), 1)
    InDecelerationMinDrive = np.full(len(Accelerations), 1)
    np.put(InDecelerationMinDrive, np.where(Accelerations >= -0.1389), 0)

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
    np.put(
        InAccelerationMinDriveStartPhase,
        np.intersect1d(
            np.where(TraceTimes <= TimeEndOfStartPhase),
            np.where(InAccelerationMinDrive == 1),
        ),
        1,
    )
    np.put(
        MinDrives[:, 2:NoOfGears],
        np.where(InAccelerationMinDriveStartPhase == 1),
        np.max(
            MinDrives[np.where(InAccelerationMinDriveStartPhase == 1), 2:NoOfGears],
            initial=MinDriveEngineSpeedGreater2ndAccelStartPhase,
        ),
    )

    InDecelerationMinDriveStartPhase = np.zeros(len(InAccelerationMinDrive))
    np.put(
        InDecelerationMinDriveStartPhase,
        np.intersect1d(
            np.where(TraceTimes <= TimeEndOfStartPhase),
            np.where(InDecelerationMinDrive == 1),
        ),
        1,
    )
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


@sh.add_function(dsp, outputs=["GearAtMaxVehicleSpeed", "MaxVehicleSpeed"])
def determine_gear_in_maximum_vehicle_speed(
    PowerCurveEngineSpeeds,
    f0,
    f1,
    f2,
    NdvRatios,
    NoOfGearsFinal,
    PowerCurvePowers,
):
    from scipy.interpolate import interp1d

    RoadLoadSpeeds = np.arange(0.1, 500.1, 0.1)
    RoadLoadPowers = np.round(
        (
            f0 * RoadLoadSpeeds
            + f1 * np.power(RoadLoadSpeeds, 2)
            + f2 * np.power(RoadLoadSpeeds, 3)
        )
        / 3600,
        4,
    )

    NoOfGears = NoOfGearsFinal

    PowerCurveVehicleSpeedsPerGear = np.outer(PowerCurveEngineSpeeds, (1 / NdvRatios.T))

    # Reduce the values of the power curve by 10%
    AvailablePowersPerGear = np.zeros((NoOfGears, len(RoadLoadSpeeds)))
    for gear in range(0, NoOfGears):
        AvailablePowersPerGear[gear, :] = 0.9 * interp1d(
            PowerCurveVehicleSpeedsPerGear[:, gear],
            PowerCurvePowers,
            bounds_error=False,
            fill_value=np.nan,
        )(RoadLoadSpeeds.T)

    NextRoadLoadPowers = np.append(RoadLoadPowers[1:], 0)
    NextAvailablePowersPerGear = np.append(
        AvailablePowersPerGear[:, 1:], np.zeros((NoOfGears, 1)), axis=1
    )

    VehicleSpeedsPerGear = np.zeros((NoOfGears, 2))

    for gear in range(0, NoOfGears):
        VehicleSpeedsPerGear[gear, :] = RoadLoadSpeeds[
            np.setxor1d(
                np.where(RoadLoadPowers < AvailablePowersPerGear[gear, :]),
                np.where(NextRoadLoadPowers < NextAvailablePowersPerGear[gear, :]),
            )
        ]

    GearAtMaxVehicleSpeed = 0

    for gear in range(NoOfGears - 1, 0, -1):
        if (
            VehicleSpeedsPerGear[gear, :].size != 0
            and VehicleSpeedsPerGear[gear - 1, :].size != 0
            and np.max(VehicleSpeedsPerGear[gear, :])
            >= np.max(VehicleSpeedsPerGear[gear - 1, :])
        ):
            GearAtMaxVehicleSpeed = gear
            MaxVehicleSpeed = np.max(VehicleSpeedsPerGear[gear, :])
            break

    return GearAtMaxVehicleSpeed, MaxVehicleSpeed


def check_gear_max_vehicle_speed(
    EngineSpeedLimitVMax,
    Max95EngineSpeedFinal,
    PowerCurveEngineSpeeds,
    PowerCurvePowers,
    RatedEnginePower,
    NdvRatios,
    GearAtMaxVehicleSpeed,
    RequiredVehicleSpeeds,
    MaxVehicleSpeed,
    NoOfGearsFinal,
):
    if GearAtMaxVehicleSpeed == 0:
        logging.error(
            "Gear to be used at maximum vehicle speed could not be determined"
        )
        return False
    else:
        return True


@sh.add_function(
    dsp,
    outputs=[
        "MaxEngineSpeed",
        "GearAtMaxVehicleSpeedFinal",
        "MaxVehicleSpeedFinal",
        "EngineSpeedAtGearAtMaxRequiredSpeed",
        "EngineSpeedAtGearAtMaxVehicleSpeed",
    ],
    input_domain=check_gear_max_vehicle_speed,
)
def determine_maximum_engine_speed(
    EngineSpeedLimitVMax,
    Max95EngineSpeedFinal,
    PowerCurveEngineSpeeds,
    PowerCurvePowers,
    RatedEnginePower,
    NdvRatios,
    GearAtMaxVehicleSpeed,
    RequiredVehicleSpeeds,
    MaxVehicleSpeed,
    NoOfGearsFinal,
):

    NoOfGears = NoOfGearsFinal

    if EngineSpeedLimitVMax > 0 and EngineSpeedLimitVMax < Max95EngineSpeedFinal:
        from scipy.interpolate import interp1d

        PowerAtEngineSpeedLimitVMax = interp1d(
            PowerCurveEngineSpeeds, PowerCurvePowers
        )(EngineSpeedLimitVMax)
        if PowerAtEngineSpeedLimitVMax > 0.95 * RatedEnginePower:
            Max95EngineSpeedFinal = EngineSpeedLimitVMax

    EngineSpeedAtGearAtMaxRequiredSpeed = NdvRatios[GearAtMaxVehicleSpeed] * np.max(
        RequiredVehicleSpeeds
    )

    if (
        EngineSpeedLimitVMax > 0
        and EngineSpeedLimitVMax < EngineSpeedAtGearAtMaxRequiredSpeed
    ):
        EngineSpeedAtGearAtMaxRequiredSpeed = EngineSpeedLimitVMax

    EngineSpeedAtGearAtMaxVehicleSpeed = (
        NdvRatios[GearAtMaxVehicleSpeed] * MaxVehicleSpeed
    )

    if (
        EngineSpeedLimitVMax > 0
        and EngineSpeedLimitVMax < EngineSpeedAtGearAtMaxVehicleSpeed
    ):
        EngineSpeedAtGearAtMaxVehicleSpeed = EngineSpeedLimitVMax
        GearAtMaxVehicleSpeed = NoOfGears
        MaxVehicleSpeed = EngineSpeedLimitVMax / NdvRatios(NoOfGears)

    MaxEngineSpeed = np.max(
        [
            Max95EngineSpeedFinal,
            EngineSpeedAtGearAtMaxRequiredSpeed,
            EngineSpeedAtGearAtMaxVehicleSpeed,
        ]
    )

    GearAtMaxVehicleSpeedFinal = GearAtMaxVehicleSpeed

    MaxVehicleSpeedFinal = MaxVehicleSpeed

    return (
        MaxEngineSpeed,
        GearAtMaxVehicleSpeedFinal,
        MaxVehicleSpeedFinal,
        EngineSpeedAtGearAtMaxRequiredSpeed,
        EngineSpeedAtGearAtMaxVehicleSpeed,
    )


@sh.add_function(dsp, outputs=["requiredPowersF"])
def calculate_required_powers(
    RequiredVehicleSpeeds, Accelerations, f0, f1, f2, VehicleTestMass
):
    requiredPowers = (
        f0 * RequiredVehicleSpeeds
        + f1 * np.power(RequiredVehicleSpeeds, 2)
        + f2 * np.power(RequiredVehicleSpeeds, 3)
        + 1.03 * Accelerations * RequiredVehicleSpeeds * VehicleTestMass
    )
    requiredPowersF = np.around(requiredPowers / 3600, 4)
    return requiredPowersF


@sh.add_function(
    dsp,
    outputs=[
        "RequiredEngineSpeeds",
        "InitialRequiredEngineSpeeds",
        "PossibleGearsByEngineSpeed",
        "AccelerationFromStandstillStarts",
        "ClutchDisengagedByGear",
        "ClutchUndefinedByGear",
        "ClutchDisengaged",
        "ClutchUndefined",
        "AdvancedClutchDisengage",
    ],
)
def determine_possible_gears(
    RequiredVehicleSpeeds,
    NdvRatios,
    TraceTimesCount,
    NoOfGearsFinal,
    PhaseValues,
    InStandStill,
    IdlingEngineSpeed,
    PhaseStarts,
    PHASE_ACCELERATION_FROM_STANDSTILL,
    Accelerations,
    MinDrives,
    GearAtMaxVehicleSpeedFinal,
    Max95EngineSpeedFinal,
    EngineSpeedAtGearAtMaxRequiredSpeed,
    PowerCurveEngineSpeeds,
    InDecelerationToStandstill,
):
    from functools import reduce

    RequiredEngineSpeeds = NdvRatios * np.transpose(
        np.array(
            [
                RequiredVehicleSpeeds,
            ]
        )
    )
    InitialRequiredEngineSpeeds = np.copy(RequiredEngineSpeeds)

    PossibleGearsByEngineSpeed = np.empty((TraceTimesCount, NoOfGearsFinal))
    PossibleGearsByEngineSpeed[:] = np.nan

    ClutchDisengaged = np.zeros(TraceTimesCount)
    ClutchUndefined = np.zeros(TraceTimesCount)

    for gear in range(0, np.shape(RequiredEngineSpeeds)[1]):
        np.put(
            RequiredEngineSpeeds[:, gear],
            np.where(InStandStill == 1),
            IdlingEngineSpeed,
        )
        np.put(
            PossibleGearsByEngineSpeed[:, gear],
            np.where(InStandStill == 1),
            0,
        )

    AccelerationFromStandstillStarts = PhaseStarts[
        np.where(PhaseValues == PHASE_ACCELERATION_FROM_STANDSTILL)
    ]
    BeforeAccelerationStarts = AccelerationFromStandstillStarts - 1
    for i in range(0, len(BeforeAccelerationStarts)):
        while (
            BeforeAccelerationStarts[i] >= 3
            and Accelerations[BeforeAccelerationStarts[i]] > 0
        ):
            BeforeAccelerationStarts[i] = BeforeAccelerationStarts[i] - 1

    AdvancedFirstGearEngage = []
    for i in range(0, len(AccelerationFromStandstillStarts)):
        AdvancedFirstGearEngage.append(
            np.arange(
                BeforeAccelerationStarts[i], AccelerationFromStandstillStarts[i], 1
            )
        )

    AdvancedClutchDisengage = []
    for i in range(0, len(BeforeAccelerationStarts)):
        AdvancedClutchDisengage.append(
            np.arange(BeforeAccelerationStarts[i] - 1, BeforeAccelerationStarts[i], 1)
        )

    for first_gear in AdvancedFirstGearEngage:
        np.put(PossibleGearsByEngineSpeed[:, 0], np.asarray(first_gear), 1)
        np.put(ClutchDisengaged, np.asarray(first_gear), 1)

    for gear in range(0, NoOfGearsFinal):
        if gear < GearAtMaxVehicleSpeedFinal:
            # 3.3a
            np.put(
                PossibleGearsByEngineSpeed[:, gear],
                reduce(
                    np.intersect1d,
                    (
                        np.where(InStandStill == 0),
                        np.where(MinDrives[:, gear] <= RequiredEngineSpeeds[:, gear]),
                        np.where(
                            RequiredEngineSpeeds[:, gear] <= Max95EngineSpeedFinal
                        ),
                    ),
                ),
                1,
            )
        else:
            # 3.3b
            np.put(
                PossibleGearsByEngineSpeed[:, gear],
                reduce(
                    np.intersect1d,
                    (
                        np.where(InStandStill == 0),
                        np.where(MinDrives[:, gear] <= RequiredEngineSpeeds[:, gear]),
                        np.where(
                            RequiredEngineSpeeds[:, gear]
                            <= EngineSpeedAtGearAtMaxRequiredSpeed
                        ),
                    ),
                ),
                1,
            )

    # 3.3c
    np.put(
        PossibleGearsByEngineSpeed[:, 0],
        np.intersect1d(
            np.where(InStandStill == 0),
            np.where(RequiredEngineSpeeds[:, 0] < MinDrives[:, 0]),
        ),
        1,
    )

    ClutchDisengagedByGear = np.zeros((TraceTimesCount, NoOfGearsFinal))
    ClutchUndefinedByGear = np.zeros((TraceTimesCount, NoOfGearsFinal))

    InAnyStandStill = np.zeros(len(RequiredVehicleSpeeds))
    np.put(InAnyStandStill, np.where(RequiredVehicleSpeeds < 1), 1)

    InAnyDeceleration = np.zeros(len(RequiredVehicleSpeeds))
    np.put(
        InAnyDeceleration,
        np.intersect1d(
            np.where(np.diff(np.append(RequiredVehicleSpeeds, 0)) <= -0.001),
            np.where(InAnyStandStill == 0),
        ),
        1,
    )

    InAnyAcceleration = np.zeros(len(RequiredVehicleSpeeds))
    np.put(
        InAnyAcceleration,
        np.intersect1d(
            np.where(np.diff(np.append(RequiredVehicleSpeeds, 0)) >= +0.001),
            np.where(InAnyStandStill == 0),
        ),
        1,
    )

    InAnyConstantSpeed = np.full(len(RequiredVehicleSpeeds), 1)
    np.put(
        InAnyConstantSpeed,
        reduce(
            np.union1d,
            (
                np.where(InAnyStandStill == 1),
                np.where(InAnyDeceleration == 1),
                np.where(InAnyAcceleration == 1),
            ),
        ),
        0,
    )

    InAnyDecelerationWithLowEngineSpeed = np.zeros(
        (len(RequiredEngineSpeeds), NoOfGearsFinal)
    )
    for gear in range(0, NoOfGearsFinal):
        np.put(
            InAnyDecelerationWithLowEngineSpeed[:, gear],
            np.intersect1d(
                np.where(InAnyDeceleration == 1),
                np.where(RequiredEngineSpeeds[:, gear] < IdlingEngineSpeed),
            ),
            1,
        )

    for gear in range(0, NoOfGearsFinal):
        np.put(
            ClutchDisengagedByGear[:, gear],
            np.where(InAnyDecelerationWithLowEngineSpeed[:, gear] == 1),
            1,
        )
        np.put(
            RequiredEngineSpeeds[:, gear],
            np.where(InAnyDecelerationWithLowEngineSpeed[:, gear] == 1),
            IdlingEngineSpeed,
        )

    InAnyAccelOrConstSpeedWithLowEngineSpeed = np.zeros(
        (len(RequiredEngineSpeeds), NoOfGearsFinal)
    )
    for gear in range(0, NoOfGearsFinal):
        np.put(
            InAnyAccelOrConstSpeedWithLowEngineSpeed[:, gear],
            np.intersect1d(
                np.union1d(
                    np.where(InAnyAcceleration == 1), np.where(InAnyConstantSpeed == 1)
                ),
                np.where(
                    RequiredEngineSpeeds[:, gear]
                    < np.max((1.15 * IdlingEngineSpeed, PowerCurveEngineSpeeds[0]))
                ),
            ),
            1,
        )

    for gear in range(0, NoOfGearsFinal):
        np.put(
            ClutchDisengagedByGear[:, gear],
            np.where(InAnyAccelOrConstSpeedWithLowEngineSpeed[:, gear] == 1),
            1,
        )
        np.put(
            ClutchUndefinedByGear[:, gear],
            np.where(InAnyAccelOrConstSpeedWithLowEngineSpeed[:, gear] == 1),
            1,
        )

    RequiredEngineSpeedsBefore = np.copy(RequiredEngineSpeeds)
    for gear in range(0, NoOfGearsFinal):
        np.put(
            RequiredEngineSpeeds[:, gear],
            np.where(InAnyAccelOrConstSpeedWithLowEngineSpeed[:, gear] == 1),
            np.max(
                (
                    1.15 * IdlingEngineSpeed,
                    np.max(
                        RequiredEngineSpeeds[
                            np.where(
                                InAnyAccelOrConstSpeedWithLowEngineSpeed[:, gear] == 1
                            ),
                            gear,
                        ]
                    ),
                )
            ),
        )

    InAnyAccelOrConstSpeedWithLowEngineSpeedModified = np.abs(
        RequiredEngineSpeeds - RequiredEngineSpeedsBefore
    )
    InAnyAccelOrConstSpeedWithLowEngineSpeedModified[
        InAnyAccelOrConstSpeedWithLowEngineSpeedModified != 0
    ] = 1

    Gear1WithIncrEngineSpeed = np.zeros(TraceTimesCount)
    np.put(
        Gear1WithIncrEngineSpeed,
        reduce(
            np.intersect1d,
            (
                np.where(
                    InitialRequiredEngineSpeeds[:, 0] < RequiredEngineSpeeds[:, 0]
                ),
                np.where(InStandStill == 0),
                np.where(InDecelerationToStandstill == 0),
            ),
        ),
        1,
    )

    np.put(ClutchDisengagedByGear[:, 0], np.where(Gear1WithIncrEngineSpeed == 1), 1)
    np.put(
        ClutchUndefinedByGear[:, 0],
        np.intersect1d(
            np.where(Gear1WithIncrEngineSpeed == 1), np.where(InAnyDeceleration == 0)
        ),
        1,
    )

    return (
        RequiredEngineSpeeds,
        InitialRequiredEngineSpeeds,
        PossibleGearsByEngineSpeed,
        AccelerationFromStandstillStarts,
        ClutchDisengagedByGear,
        ClutchUndefinedByGear,
        ClutchDisengaged,
        ClutchUndefined,
        AdvancedClutchDisengage,
    )


@sh.add_function(dsp, outputs=["AvailablePowers", "InitialAvailablePowers"])
def calculate_available_powers(
    DefinedPowerCurveAdditionalSafetyMargins,
    RequiredEngineSpeeds,
    IdlingEngineSpeed,
    PowerCurveEngineSpeeds,
    SafetyMargin,
    PowerCurveASM,
    PowerCurvePowers,
    NoOfGearsFinal,
    InitialRequiredEngineSpeeds,
):

    from scipy.interpolate import interp1d

    interpval = PowerCurvePowers * (1 - (SafetyMargin * 100 + PowerCurveASM) / 100)

    if DefinedPowerCurveAdditionalSafetyMargins:
        np.put(
            RequiredEngineSpeeds[:, 1],
            np.where(RequiredEngineSpeeds[:, 1] < IdlingEngineSpeed),
            IdlingEngineSpeed,
        )
        AvailablePowers = np.zeros(np.shape(RequiredEngineSpeeds))
        for gear in range(0, NoOfGearsFinal):
            for i in range(0, len(AvailablePowers)):
                if gear in [0, 1]:
                    AvailablePowers[i, gear] = interp1d(
                        PowerCurveEngineSpeeds,
                        interpval,
                        bounds_error=False,
                        fill_value=np.nan,
                    )(
                        np.max(
                            (
                                RequiredEngineSpeeds[i, gear],
                                PowerCurveEngineSpeeds[0],
                            )
                        )
                    )
                else:
                    AvailablePowers[i, gear] = interp1d(
                        PowerCurveEngineSpeeds,
                        interpval,
                        kind="linear",
                        fill_value="extrapolate",
                    )(
                        np.max(
                            (
                                RequiredEngineSpeeds[i, gear],
                                PowerCurveEngineSpeeds[0],
                            )
                        )
                    )

        InitialAvailablePowers = interp1d(
            PowerCurveEngineSpeeds,
            PowerCurvePowers * (1 - (SafetyMargin * 100 + PowerCurveASM) / 100),
            bounds_error=False,
            fill_value=np.nan,
        )(InitialRequiredEngineSpeeds)

    return AvailablePowers, InitialAvailablePowers


def sub2ind(array_shape, rows, cols):
    ind = rows * array_shape[0] + cols
    return ind


@sh.add_function(dsp, outputs=["PossibleGearsByAvailablePowersWithTotalSafetyMargin"])
def determine_possible_gears_based_available_powers(
    AvailablePowers,
    requiredPowersF,
    TraceTimesCount,
    NoOfGearsFinal,
    PossibleGearsByEngineSpeed,
):
    PossibleGearsByAvailablePowersWithTotalSafetyMargin = np.empty(
        (TraceTimesCount, NoOfGearsFinal)
    )
    PossibleGearsByAvailablePowersWithTotalSafetyMargin[:] = np.nan
    PossibleGearsByAvailablePowersWithTotalSafetyMargin[:, 0:2] = 1

    for gear in range(2, NoOfGearsFinal):
        np.put(
            PossibleGearsByAvailablePowersWithTotalSafetyMargin[:, gear],
            np.where(AvailablePowers[:, gear] >= requiredPowersF),
            1,
        )

    K = AvailablePowers * PossibleGearsByEngineSpeed
    K[np.isnan(K)] = -1
    I = np.argmax(np.fliplr(K), axis=1)
    I = np.shape(AvailablePowers)[1] - I - 1

    m, n = np.shape(AvailablePowers)

    linearInd = sub2ind(np.shape(AvailablePowers), I, np.arange(0, m))

    PossibleGearsByAvailablePowersWithTotalSafetyMargin[
        np.unravel_index(
            linearInd, PossibleGearsByAvailablePowersWithTotalSafetyMargin.shape, "F"
        )
    ] = 1

    return PossibleGearsByAvailablePowersWithTotalSafetyMargin


@sh.add_function(dsp, outputs=["InitialGears", "PossibleGears"])
def determine_initial_gears(
    InStandStill,
    NoOfGearsFinal,
    PossibleGearsByEngineSpeed,
    PossibleGearsByAvailablePowersWithTotalSafetyMargin,
    AccelerationFromStandstillStarts,
    PhaseEnds,
    PhaseValues,
    PHASE_ACCELERATION_FROM_STANDSTILL,
    InitialRequiredEngineSpeeds,
    MinDrive1stTo2nd,
):

    InStandStillReps = np.tile(InStandStill, (NoOfGearsFinal, 1)).T
    PossibleGears = np.copy(PossibleGearsByEngineSpeed)
    PossibleGears[np.where(InStandStillReps == 0)] = (
        PossibleGears[np.where(InStandStillReps == 0)]
        * PossibleGearsByAvailablePowersWithTotalSafetyMargin[
            np.where(InStandStillReps == 0)
        ]
    )

    for gear in range(0, NoOfGearsFinal):
        PossibleGears[:, gear] = np.float(gear + 1) * PossibleGears[:, gear]

    K = np.copy(PossibleGears)
    K[np.isnan(K)] = -2
    InitialGears = np.max(K, axis=1)

    InitialGears[AccelerationFromStandstillStarts] = 1

    AccelerationFromStandstillEnds = PhaseEnds[
        np.where(PhaseValues == PHASE_ACCELERATION_FROM_STANDSTILL)
    ]

    AccelerationsFromStandstill = [
        np.arange(
            AccelerationFromStandstillStarts[i], AccelerationFromStandstillEnds[i] + 1
        )
        for i in range(0, len(AccelerationFromStandstillEnds))
    ]

    for phase in AccelerationsFromStandstill:
        gears = InitialGears[phase]
        if np.where(gears == 2)[0].size != 0:
            secondGearEngaged = np.where(gears == 2)[0][0] - 1
            gears[1:secondGearEngaged] = 1
            InitialGears[phase] = gears

    # Changed requirement:
    # MinDrive1stTo2nd no longer limited to acceleration phase.
    for i in range(0, len(InitialGears)):
        if InitialGears[i] == 1:
            FromGear1 = True
        elif InitialGears[i] == 2:
            if (
                FromGear1
                and InitialRequiredEngineSpeeds[i, 1] < MinDrive1stTo2nd
                and PossibleGears[i, 0] == 1
            ):
                InitialGears[i] = 1
            else:
                FromGear1 = False
        else:
            FromGear1 = False

    return InitialGears, PossibleGears


def _next_n_gears_are_higher(n, gears):
    enabled = np.full(len(gears), 1)
    for i in range(0, len(gears)):
        for k in range(1, n + 1):
            if i + k < len(gears) - 1:
                if gears[i + k] <= gears[i]:
                    enabled[i] = 0

    return enabled


@sh.add_function(
    dsp,
    outputs=[
        "InitialGearsFinal",
        "CorrectionsCells",
        "ClutchDisengagedByGearFinal",
        "ClutchUndefinedByGearFinal",
    ],
)
def apply_corrections(
    InitialGears,
    PhaseValues,
    PhaseStarts,
    PhaseEnds,
    PHASE_ACCELERATION_FROM_STANDSTILL,
    PHASE_ACCELERATION,
    NoOfGearsFinal,
    PossibleGears,
    InAcceleration,
    InConstantSpeed,
    InAccelerationAnyDuration,
    ClutchDisengagedByGear,
    ClutchUndefinedByGear,
    PHASE_DECELERATION,
    PHASE_DECELERATION_TO_STANDSTILL,
    TraceTimesCount,
    RequiredVehicleSpeeds,
    SuppressGear0DuringDownshifts,
    ClutchDisengaged,
    InitialRequiredEngineSpeeds,
    IdlingEngineSpeed,
    Phases,
    InStandStill,
    InDecelerationToStandstill,
    InDeceleration,
):
    from functools import reduce

    CorrectionsCells = [[] for _ in range(0, len(InitialGears))]
    CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
        CorrectionsCells, InitialGears, InitialGears, "", 0
    )

    corr_4d_applied_before = np.zeros(np.size(InitialGears))

    for correction in range(1, 3):
        Corr4bToBeDoneAfterCorr4a = np.zeros(len(InitialGears))
        Corr4bToBeDoneAfterCorr4d = np.zeros(len(InitialGears))

        (
            InitialGears,
            Corr4bToBeDoneAfterCorr4a,
            Corr4bToBeDoneAfterCorr4d,
        ) = applyCorrection4b(
            InitialGears,
            Corr4bToBeDoneAfterCorr4a,
            Corr4bToBeDoneAfterCorr4d,
            PhaseValues,
            PhaseStarts,
            PhaseEnds,
            PHASE_ACCELERATION_FROM_STANDSTILL,
            PHASE_ACCELERATION,
            NoOfGearsFinal,
        )

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4b", correction
        )

        InitialGears = applyCorrection4a(
            InitialGears,
            Corr4bToBeDoneAfterCorr4a,
            PossibleGears,
            InAcceleration,
            InConstantSpeed,
            InAccelerationAnyDuration,
        )

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4a", correction
        )

        # Do an extra delayed gear correction "4s" ( s : short downshift )
        # which was determined during gear correction 4b
        # but shall be done after gear correction 4a.
        # This delayed correction must be suppressed at positions
        # where there is no such short downshift anymore
        # (and at positions where correction 4c will extend such short downshifts)

        np.put(
            Corr4bToBeDoneAfterCorr4a,
            reduce(
                np.intersect1d,
                (
                    np.where(Corr4bToBeDoneAfterCorr4a == 1),
                    np.where(np.diff(np.insert(InitialGears, 0, np.nan)) < 0),
                    np.where(np.diff(np.append(InitialGears, np.nan)) > 0),
                ),
            ),
            1,
        )

        enabled = _next_n_gears_are_higher(6, InitialGears)
        np.put(
            Corr4bToBeDoneAfterCorr4a,
            np.intersect1d(
                np.where(Corr4bToBeDoneAfterCorr4a == 1), np.where(enabled == 1)
            ),
            1,
        )
        InitialGears[np.where(Corr4bToBeDoneAfterCorr4a == 1)] = InitialGears[
            np.where(Corr4bToBeDoneAfterCorr4a == 1)[0] - 1
        ]

        for igear in np.unique(InitialGears[np.where(Corr4bToBeDoneAfterCorr4a == 1)]):
            ClutchDisengagedByGear[
                np.where(Corr4bToBeDoneAfterCorr4a == 1), int(igear) - 1
            ] = 0
            ClutchUndefinedByGear[
                np.where(Corr4bToBeDoneAfterCorr4a == 1), int(igear) - 1
            ] = 0

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4s", correction
        )

        # -----------------------------------------------------------------------
        # Regulation Annex 2, 4.(c) preface
        # -----------------------------------------------------------------------
        # The modification check described in paragraph 4.(c) of this annex
        # shall be applied to the complete cycle trace twice
        # prior to the application of paragraphs 4.(d) to 4.(f) of this annex.
        # -----------------------------------------------------------------------
        for correction_4c in range(1, 3):
            InitialGears = applyCorrection4c(InitialGears, PossibleGears)
            CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
                CorrectionsCells, InitialGears, InitialGearsPrev, "4c", correction
            )

        InitialGears = applyCorrection4d(
            InitialGears,
            PhaseStarts,
            PhaseEnds,
            PhaseValues,
            PHASE_DECELERATION,
            PHASE_DECELERATION_TO_STANDSTILL,
            corr_4d_applied_before,
            TraceTimesCount,
            NoOfGearsFinal,
            RequiredVehicleSpeeds,
        )
        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4d", correction
        )

        # Do an extra delayed gear correction "4t" ( t : two step downshift )
        # which was determined during gear correction 4b
        # but shall be done after gear correction 4d (according Heinz Steven).
        # This delayed correction must be suppressed at positions
        # where there is no downshift by more than one gear anymore.
        np.put(
            Corr4bToBeDoneAfterCorr4d,
            np.intersect1d(
                np.where(Corr4bToBeDoneAfterCorr4d == 1),
                np.where(np.diff(np.append(InitialGears, np.nan)) < -1),
            ),
            1,
        )
        if SuppressGear0DuringDownshifts:
            nextCorr4bToBeDoneAfterCorr4d = np.insert(Corr4bToBeDoneAfterCorr4d, 0, 0)
            InitialGears[np.where(Corr4bToBeDoneAfterCorr4d == 1)] = InitialGears[
                np.where(nextCorr4bToBeDoneAfterCorr4d == 1)
            ]
        else:
            InitialGears[np.where(Corr4bToBeDoneAfterCorr4d == 1)] = 0
            ClutchDisengaged[np.where(Corr4bToBeDoneAfterCorr4d == 1)] = 1

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4t", correction
        )

        # But also such delayed gear corrections "4t" must be undone
        # when an even later 2nd gear correction 4d
        # reduces such downshifts to downshift by only one gear.
        prevInitialGears = np.insert(InitialGears, 0, 0)[:-1]
        nextInitialGears = np.insert(InitialGears[1:], -1, InitialGears[-1])
        idx = reduce(
            np.intersect1d,
            (
                np.where(InitialGears == 0),
                np.where(prevInitialGears - 1 == nextInitialGears),
                np.where(nextInitialGears > 0),
            ),
        )
        InitialGears[idx] = InitialGears[idx - 1]
        ClutchDisengaged[idx] = 0

        InitialGears, ClutchDisengaged = applyCorrection4e(
            InitialGears,
            PhaseStarts,
            PhaseEnds,
            PhaseValues,
            ClutchDisengaged,
            InitialRequiredEngineSpeeds,
            IdlingEngineSpeed,
            PHASE_DECELERATION,
            PHASE_DECELERATION_TO_STANDSTILL,
            Phases,
        )

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4e", correction
        )

        InitialGears, ClutchDisengaged = applyCorrection4f(
            InitialGears,
            ClutchDisengaged,
            SuppressGear0DuringDownshifts,
            PossibleGears,
            InStandStill,
            InDecelerationToStandstill,
            InDeceleration,
        )

        CorrectionsCells, InitialGearsPrev = appendCorrectionCells(
            CorrectionsCells, InitialGears, InitialGearsPrev, "4f", correction
        )

    InitialGearsFinal = InitialGears
    ClutchDisengagedByGearFinal = ClutchDisengagedByGear
    ClutchUndefinedByGearFinal = ClutchUndefinedByGear

    return (
        InitialGearsFinal,
        CorrectionsCells,
        ClutchDisengagedByGearFinal,
        ClutchUndefinedByGearFinal,
    )


@sh.add_function(dsp, outputs=["AverageGear", "PhaseSum"])
def calculate_average_gear(Phases, PHASE_STANDSTILL, InitialGearsFinal):
    PhaseSum = np.zeros(np.shape(Phases))
    np.put(
        PhaseSum,
        np.intersect1d(
            np.where(Phases != PHASE_STANDSTILL), np.where(~np.isnan(InitialGearsFinal))
        ),
        1,
    )
    AverageGear = np.round(
        np.sum(InitialGearsFinal[np.where(PhaseSum == 1)]) / np.sum(PhaseSum), 4
    )

    return AverageGear, PhaseSum


@sh.add_function(dsp, outputs=["ChecksumVxGear"])
def calculate_average_gear(PhaseSum, InitialGearsFinal, RequiredVehicleSpeeds):
    ChecksumVxGear = np.sum(
        InitialGearsFinal[np.where(PhaseSum == 1)]
        * RequiredVehicleSpeeds[np.where(PhaseSum == 1)]
    )
    return ChecksumVxGear


@sh.add_function(
    dsp,
    outputs=[
        "InitialGearsFinalAfterClutch",
        "ClutchDisengagedFinal",
        "ClutchUndefinedFinal",
    ],
)
def interleave_clutch(
    TraceTimesCount,
    InitialGearsFinal,
    ClutchDisengagedByGearFinal,
    ClutchDisengaged,
    ClutchUndefinedByGearFinal,
    ClutchUndefined,
    AutomaticClutchOperation,
    InDeceleration,
    AdvancedClutchDisengage,
):

    # This is a test parameter that can be included in the inputs in the future
    DoNotMergeClutchIntoGearsOutput = True

    for t in range(0, TraceTimesCount):
        if InitialGearsFinal[t] >= 1:
            if ClutchDisengagedByGearFinal[t, int(InitialGearsFinal[t]) - 1] == 1:
                ClutchDisengaged[t] = 1
            if ClutchUndefinedByGearFinal[t, int(InitialGearsFinal[t]) - 1] == 1:
                ClutchUndefined[t] = 1

    if not AutomaticClutchOperation and not DoNotMergeClutchIntoGearsOutput:
        InitialGearsFinal[
            np.intersect1d(
                np.where(InDeceleration == 1), np.where(ClutchDisengaged == 1)
            )
        ] = -1
        for ad in AdvancedClutchDisengage:
            InitialGearsFinal[ad] = -1

    InitialGearsFinalAfterClutch = InitialGearsFinal
    ClutchDisengagedFinal = ClutchDisengaged
    ClutchUndefinedFinal = ClutchUndefined

    return InitialGearsFinalAfterClutch, ClutchDisengagedFinal, ClutchUndefinedFinal


@sh.add_function(dsp, outputs=["ClutchHST", "GearSequenceStarts", "GearNames"])
def remove_duplicate_gears(
    InitialGearsFinalAfterClutch, ClutchUndefinedFinal, ClutchDisengagedFinal
):
    from functools import reduce
    import regex as re

    GearSequenceStarts = reduce(
        np.intersect1d,
        (
            np.where(~np.isnan(InitialGearsFinalAfterClutch[:-1])),
            np.where(~np.isnan(InitialGearsFinalAfterClutch[1:])),
            np.where(np.diff(InitialGearsFinalAfterClutch) != 0),
        ),
    )

    GearSequenceStarts = np.insert(GearSequenceStarts + 1, 0, 0)

    GearNames = [
        "MANUAL-" + str(int(ig))
        for ig in InitialGearsFinalAfterClutch[GearSequenceStarts]
    ]
    GearNames = [re.sub("MANUAL-0", "MANUAL-NEUTRAL", i) for i in GearNames]
    GearNames = [re.sub("MANUAL--1", "MANUAL-CLUTCH", i) for i in GearNames]

    # generate clutch state strings as done by Heinz Steven Tool (HST)
    ClutchHST = np.full(
        np.shape(ClutchDisengagedFinal), "                              "
    )
    for i in range(0, len(ClutchDisengagedFinal)):
        if ClutchUndefinedFinal[i] == 1:
            ClutchHST[i] = "undefined"
        elif ClutchDisengagedFinal[i] == 1:
            ClutchHST[i] = "disengaged"
        elif InitialGearsFinalAfterClutch[i] == 0:
            ClutchHST[i] = "engaged; gear lever in neutral"
        else:
            ClutchHST[i] = "engaged"

    return ClutchHST, GearSequenceStarts, GearNames


@sh.add_function(dsp, outputs=["AvailablePowersFinal"])
def reduce_vehicle_speed_if_not_enough_power(
    DefinedPowerCurveAdditionalSafetyMargins,
    PowerCurveEngineSpeeds,
    PowerCurvePowers,
    SafetyMargin,
    PowerCurveASM,
    IdlingEngineSpeed,
    AdditionalSafetyMargin0,
    RequiredEngineSpeeds,
    RequiredVehicleSpeeds,
    f0,
    f1,
    f2,
    VehicleTestMass,
    requiredPowersF,
    ClutchDisengagedFinal,
    ClutchUndefinedFinal,
    InitialGearsFinalAfterClutch,
    NoOfGearsFinal,
    AvailablePowers,
    NdvRatios,
):

    from scipy.interpolate import interp1d

    # This is a test parameter that can be included in the inputs in the future
    LimitVehicleSpeedByAvailablePower = True

    if LimitVehicleSpeedByAvailablePower:
        # if the clutch is "undefined" then assume that
        # the available power is determined from the engine speed
        # also used for transitions from first to second gear
        #
        #   Annex 2
        #
        #     2.(k)
        #       (2) For n_gear = 2,
        #         (i) for transitions from first to second gear:
        #           n_min_drive = 1.15 × n_idle,
        #
        #     3.3. Selection of possible gears with respect to engine speed
        #       If   a_j >= 0
        #       and  n_i,j <  max( 1.15 × n_idle, min. engine speed of the P_wot(n) curve )
        #       then n_i,j := max( 1.15 × n_idle, min. engine speed of the P_wot(n) curve )
        #       and the clutch shall be set to "undefined".
        #
        # if the clutch is "disengaged" then assume that
        # the available power is determined from the idling engine speed n_idle
        # but if n_idle < min. engine speed of the P_wot(n) curve
        # then no check for the available power will be done
        #
        #   Annex 2
        #
        #     3.3. Selection of possible gears with respect to engine speed
        #       If   a_j < 0
        #       and  n_i,j <= n_idle
        #       then n_i,j := n_idle
        #       and the clutch shall be set to "disengaged".
        #
        # note that the available power defined by the P_wot(n) curve
        if DefinedPowerCurveAdditionalSafetyMargins:

            interpval = PowerCurvePowers * (
                1 - (SafetyMargin * 100 + PowerCurveASM) / 100
            )

            AvailablePowerClutchDisengaged = interp1d(
                PowerCurveEngineSpeeds,
                interpval,
                bounds_error=False,
                fill_value=np.nan,
            )(
                np.max(
                    (
                        IdlingEngineSpeed,
                        PowerCurveEngineSpeeds[0],
                    )
                )
            )

            AvailablePowerClutchUndefined = interp1d(
                PowerCurveEngineSpeeds,
                interpval,
                bounds_error=False,
                fill_value=np.nan,
            )(
                np.max(
                    (
                        1.15 * IdlingEngineSpeed,
                        PowerCurveEngineSpeeds[0],
                    )
                )
            )

        CheckAvailablePowerClutchDisengaged = (
            IdlingEngineSpeed >= PowerCurveEngineSpeeds[0]
        )

        for i in range(0, len(RequiredEngineSpeeds[:, 1]) - 1):
            PowerForRestistance = (
                f0 * RequiredVehicleSpeeds[i]
                + f1 * np.power(RequiredVehicleSpeeds[i], 2)
                + f2 * np.power(RequiredVehicleSpeeds[i], 3)
            ) / 3600

            Acceleration = (
                RequiredVehicleSpeeds[i + 1] - RequiredVehicleSpeeds[i]
            ) / 3.6
            PowerForAcceleration = (
                Acceleration * 1.03 * RequiredVehicleSpeeds[i] * VehicleTestMass / 3600
            )
            requiredPowersF[i] = PowerForRestistance + PowerForAcceleration
            g = InitialGearsFinalAfterClutch[i]
            if ClutchDisengagedFinal[i] == 1 or (g >= 1 and g <= NoOfGearsFinal):
                if ClutchDisengagedFinal[i] == 1:
                    if ClutchUndefinedFinal[i] == 1:
                        CheckAvailablePower = True
                        AvailablePower = AvailablePowerClutchUndefined
                    else:
                        CheckAvailablePower = CheckAvailablePowerClutchDisengaged
                        AvailablePower = AvailablePowerClutchDisengaged
                else:
                    CheckAvailablePower = True
                    AvailablePower = AvailablePowers[i, int(g) - 1]

                if (
                    CheckAvailablePower
                    and requiredPowersF[i] > AvailablePower
                    and RequiredVehicleSpeeds[i] >= 1
                    and (
                        ClutchDisengagedFinal[i] == 1
                        or RequiredEngineSpeeds[i, int(g) - 1]
                        > PowerCurveEngineSpeeds[0]
                    )
                ):
                    requiredPowersF[i] = AvailablePower
                    PowerForAcceleration = AvailablePower - PowerForRestistance
                    Acceleration = (
                        PowerForAcceleration
                        / (1.03 * RequiredVehicleSpeeds[i] * VehicleTestMass)
                        * 3600
                    )
                    NextVehicleSpeed = RequiredVehicleSpeeds[i] + Acceleration * 3.6
                    if RequiredVehicleSpeeds[i + 1] > NextVehicleSpeed:
                        RequiredVehicleSpeeds[i + 1] = NextVehicleSpeed
                        RequiredEngineSpeeds[i + 1, :] = NextVehicleSpeed * NdvRatios

                    # determine available powers for next trace second with reduced vehicle speed
                    if DefinedPowerCurveAdditionalSafetyMargins:
                        interpval = PowerCurvePowers * (
                            1 - (SafetyMargin * 100 + PowerCurveASM) / 100
                        )
                        for n in range(0, NoOfGearsFinal):
                            if n in [0, 1]:
                                AvailablePowers[i + 1, n] = interp1d(
                                    PowerCurveEngineSpeeds,
                                    interpval,
                                    bounds_error=False,
                                    fill_value=np.nan,
                                )(
                                    max(
                                        RequiredEngineSpeeds[i + 1, n],
                                        PowerCurveEngineSpeeds[0],
                                    )
                                )
                            else:
                                AvailablePowers[i + 1, n] = interp1d(
                                    PowerCurveEngineSpeeds,
                                    interpval,
                                    kind="linear",
                                    fill_value="extrapolate",
                                )(RequiredEngineSpeeds[i + 1, n])

    AvailablePowersFinal = AvailablePowers

    return AvailablePowersFinal


@sh.add_function(dsp, outputs=["shift_poits"])
def generate_gears(
    TraceTimes,
    GearSequenceStarts,
    GearNames,
    AverageGear,
    Max95EngineSpeedFinal,
    RequiredVehicleSpeeds,
    requiredPowersF,
    RequiredEngineSpeeds,
    PossibleGearsByEngineSpeed,
    AvailablePowersFinal,
    InitialRequiredEngineSpeeds,
    InitialAvailablePowers,
    FullPowerCurve,
    EngineSpeedAtGearAtMaxRequiredSpeed,
    EngineSpeedAtGearAtMaxVehicleSpeed,
    MaxEngineSpeed,
    MaxVehicleSpeedFinal,
    GearAtMaxVehicleSpeedFinal,
    MinDrive1st,
    MinDrive1stTo2nd,
    MinDrive2ndDecel,
    MinDrive2nd,
    MinDriveGreater2nd,
    InitialGearsFinalAfterClutch,
    ClutchDisengagedFinal,
    ClutchUndefinedFinal,
    ClutchHST,
    CorrectionsCells,
    ChecksumVxGear,
):
    # This is a test parameter that can be included in the inputs in the future
    ReturnAdjustedEngSpeedsAndAvlPowers = True

    if ReturnAdjustedEngSpeedsAndAvlPowers:
        RequiredEngineSpeeds[np.where(~(PossibleGearsByEngineSpeed == 1))] = np.nan
        AvailablePowersFinal[np.where(~(PossibleGearsByEngineSpeed == 1))] = np.nan
        RequiredEngineSpeedsOutput = np.round(RequiredEngineSpeeds, 4)
        AvailablePowersOutput = np.round(AvailablePowersFinal, 4)
    else:
        RequiredEngineSpeedsOutput = np.round(InitialRequiredEngineSpeeds, 4)
        AvailablePowersOutput = np.round(InitialAvailablePowers, 4)

    shift_poits = {
        "CalculatedGearsOutput": np.vstack(
            (TraceTimes[GearSequenceStarts], GearNames)
        ).T,
        "AverageGearOutput": np.round(AverageGear * 10000) / 10000,
        "PowerCurveOutput": FullPowerCurve,
        "AdjustedMax95EngineSpeed": Max95EngineSpeedFinal,
        "TraceTimesOutput": TraceTimes,
        "RequiredVehicleSpeedsOutput": RequiredVehicleSpeeds,
        "RequiredPowersOutput": np.round(requiredPowersF, 4),
        "RequiredEngineSpeedsOutput": RequiredEngineSpeedsOutput,
        "AvailablePowersOutput": AvailablePowersOutput,
        "MaxEngineSpeedCycleOutput": EngineSpeedAtGearAtMaxRequiredSpeed,
        "MaxEngineSpeedReachableOutput": EngineSpeedAtGearAtMaxVehicleSpeed,
        "MaxEngineSpeedOutput": MaxEngineSpeed,
        "MaxVehicleSpeedCycleOutput": np.max(RequiredVehicleSpeeds),
        "MaxVehicleSpeedReachableOutput": MaxVehicleSpeedFinal,
        "GearMaxVehicleSpeedReachableOutput": GearAtMaxVehicleSpeedFinal,
        "MinDriveEngineSpeed1stOutput": MinDrive1st,
        "MinDriveEngineSpeed1stTo2ndOutput": MinDrive1stTo2nd,
        "MinDriveEngineSpeed2ndDecelOutput": MinDrive2ndDecel,
        "MinDriveEngineSpeed2ndOutput": MinDrive2nd,
        "MinDriveEngineSpeedGreater2ndOutput": MinDriveGreater2nd,
        "GearsOutput": InitialGearsFinalAfterClutch.astype(int),
        "ClutchDisengagedOutput": ClutchDisengagedFinal.astype(int),
        "ClutchUndefinedOutput": ClutchUndefinedFinal.astype(int),
        "ClutchHSTOutput": ClutchHST,
        "GearCorrectionsOutput": CorrectionsCells,
        "ChecksumVxGearOutput": np.round(ChecksumVxGear * 10000) / 10000,
    }

    return shift_poits
