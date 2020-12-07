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
    """
    Check if is necessary exclude the first gear from the input gears

    :param NoOfGears:
        Annex 2 (2d) ng. The number of forward gears.
    :type NoOfGears: Integer

    :param gear_nbrs:
        List with of gears of the vehicle.
    :type gear_nbrs: list

    :param Ndv:
        Annex 2 (2e) i ==> (n/v)_i
        The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng.
    :type Ndv: list

    :param ExcludeCrawlerGear:
        Annex 2 (2j)
        Gear 1 may be excluded at the request of . the manufacturer if
    :type ExcludeCrawlerGear: boolean

    :return:
        NoOfGearsFinal: The number of forward gears after apply the exclusion of first gear
        if is necessary.
        Gears: List with of gears of the vehicle after apply the exclusion of first gear
        if is necessary.
        NdvRatios: The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng after apply the exclusion of first gear if
        is necessary.
    :rtype: (integer, list, array)
    """
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
    """
    Split speed trace in trace times and required vehicles speeds

    :param speed_trace:
        Annex 1 (eg 8.3) i ==> v_i
        The vehicle speed at second i.
    :type speed_trace: array

    :return TraceTimesInput:
        Times for each vehicle speed required
    :rtype TraceTimesInput: array

    :return RequiredVehicleSpeedsInput:
        The vehicle speed required for the whole cycle.
    :rtype RequiredVehicleSpeedsInput: array
    """
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
    """
    Re-sample the trace in 1Hz
    If the trace was provided with higher sample rate, this may lead to data
    loss.

    :param TraceTimesInput:
        Times for each vehicle speed required
    :type TraceTimesInput: array

    :param RequiredVehicleSpeedsInput:
        The vehicle speed required for the whole cycle.
    :type RequiredVehicleSpeedsInput: array

    :return TraceTimes:
        Times for each vehicle speed required re-sampled in 1Hz
    :rtype TraceTimes: array

    :return RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :rtype RequiredVehicleSpeeds: array

    :return TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :rtype TraceTimesCount: integer
    """
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
    """
    Identify phases

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :return Phases:
        The list of phases that are used during whole cycle
    :rtype Phases: array

    :return InDecelerationToStandstill:
        The array that contains the seconds from deceleration to standstill as a True
    :rtype InDecelerationToStandstill: boolean array

    :return PhaseValues:
        Contains the points of changes phases
    :rtype PhaseValues: array

    :return InStandStill:
        Contains the points that are in standstill phase as a True
    :rtype InStandStill: boolean array

    :return PhaseStarts:
        Contains the points that are start point from a phase
    :rtype PhaseStarts: array

    :return PhaseEnds:
        Contains the points that are end point from a phase
    :rtype PhaseEnds: array

    :return PHASE_ACCELERATION_FROM_STANDSTILL:
        Acceleration phase following a standstill phase
    :rtype PHASE_ACCELERATION_FROM_STANDSTILL: integer

    :return PHASE_ACCELERATION:
        Acceleration phase
    :rtype PHASE_ACCELERATION: integer

    :return InAcceleration:
        Contains the points that are in acceleration phase as a True
    :rtype InAcceleration: boolean array

    :return InConstantSpeed:
        Contains the points that are in constant speed phase as a True
    :rtype InConstantSpeed: boolean array

    :return InAccelerationAnyDuration:
         some gear corrections ignore the duration of acceleration phases
         so save acceleration phases with any duration here
    :rtype InAccelerationAnyDuration: boolean array

    :return PHASE_DECELERATION:
        time period of more than 2 seconds with required vehicle
                speed >= 1km/h and monotonically decreasing
    :rtype PHASE_DECELERATION: integer

    :return PHASE_DECELERATION_TO_STANDSTILL:
        DECELERATION phase preceding a STANDSTILL phase
    :rtype PHASE_DECELERATION_TO_STANDSTILL: integer

    :return InDeceleration:
        Contains the points that are in deceleration phase as a True
    :rtype InDeceleration: boolean array

    :return PHASE_STANDSTILL:
        Time period with required vehicle speed < 1km/h
    :rtype PHASE_STANDSTILL: integer
    """
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
    """
    Load full power curve
    This function split the different components of full power curve in a independent array

    :param FullPowerCurve:
        Annex 2 (2h) and (3.4) n ==> P_wot(n), ASM
        The full load power curve over the engine speed range.
    :type FullPowerCurve: array

    :param AdditionalSafetyMargin0:
        This is a legacy parameter used until regulation GRPE-72-10-Rev.2.
        Later regulations define the additional safety margin values
        as part of the FullPowerCurve.
    :type AdditionalSafetyMargin0: array

    :param StartEngineSpeed:
        This is a legacy parameter used until regulation GRPE-72-10-Rev.2.
        GRPE-72-10-Rev.2 Annex 2 (3.4) n_start
        The engine speed at which ASM approching zero starts.
    :type StartEngineSpeed: array

    :param EndEngineSpeed:
        This is a legacy parameter used until regulation GRPE-72-10-Rev.2.
        GRPE-72-10-Rev.2 Annex 2 (3.4) n_end
        The engine speed at which ASM approching zero ends.
    :type EndEngineSpeed: array

    :result PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :rtype PowerCurveEngineSpeeds: array

    :result PowerCurvePowers:
        Contains the power curve powers
    :rtype PowerCurvePowers: array

    :result PowerCurveASM:
        Contains the power curve additional save margin
    :rtype PowerCurveASM: array

    :result DefinedPowerCurveAdditionalSafetyMargins:
        Boolean that define if the additional save margins are present
    :rtype DefinedPowerCurveAdditionalSafetyMargins: boolean
    """
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


@sh.add_function(dsp, outputs=["RatedEnginePowerF", "RatedEngineSpeedF"])
def determine_rated_engine_power(
    RatedEnginePower, RatedEngineSpeed, PowerCurvePowers, PowerCurveEngineSpeeds
):
    """
    Determine rated engine power and rated engine speed from the full power curve

    .. note::
    The following requirement was deleted from the regulation but as there is no
    new requirement we will stay with the old one :
    If the maximum power is developed over an engine speed range, n_rated shall be
    the minimum of this range

    :param RatedEnginePower:
        Annex 2 (2a) P_rated.
        This is a legacy parameter used until regulation GRPE-75-23.The maximum rated
        engine power as declared by the manufacturer. But the newer regulation
        GRPE/2018/2 Annex 2 (2g) now requires : The data sets and the values P_rated
        and n_rated shall be taken from the power curve as declared by the manufacturer.

        For backward compatibility this parameter may still be used to override the
        value calculated from FullPowerCurve. Set RatedEnginePower and RatedEngineSpeed
        to 0 to use the calculated values.
    :type RatedEnginePower: array

    :param RatedEngineSpeed:
        Annex 2 (2b) n_rated. This is a legacy parameter used until regulation GRPE-75-23.
        The rated engine speed at which an engine declared by the manufacturer as the
        engine speed at which the engine develops its maximum power.

        But the newer regulation GRPE/2018/2 Annex 2 (2g) now requires: The data sets and
        the values P_rated and n_rated shall be taken from the power curve as declared by
        the manufacturer.

        For backward compatibility this parameter may still be used to override the value
        calculated from FullPowerCurve. Set RatedEnginePower and RatedEngineSpeed to 0
        to use the calculated values.
    :type RatedEngineSpeed: array

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :return RatedEnginePowerF:
        Contains the rated engine power corrected if is necessary
    :rtype RatedEnginePowerF: float

    :return RatedEngineSpeedF:
        Contains the rated engine speed corrected if is necessary
    :rtype RatedEngineSpeedF: float
    """
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
    """
    Determine the maximum engine speed where 95 percent of the rated power is
    reached from the full power curve

    .. note::
    This will only be done if this value was not set as input parameter

    :param Max95EngineSpeed:
        Annex 2 (2g) n_max1 = n_95_high
        The maximum engine speed where 95 per cent of rated power is reached.
        If the dummy value 0 will be given for this parameter then n_max1 will
        be calculated from parameter FullPowerCurve P_wot.
    :type Max95EngineSpeed: float

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :return Max95EngineSpeedFinal:
         Annex 2 (2g) n_max1 = n_95_high adjusted
         If n_95_high cannot be determined because the engine speed is limited to
         a lower value n_lim for all gears and the corresponding full load power
         is higher than 95 per cent of rated power, n_95_high shall be set to n_lim.
    :rtype Max95EngineSpeedFinal: float
    """
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
    RatedEngineSpeedF,
    MinDriveEngineSpeed1st,
    MinDriveEngineSpeed1stTo2nd,
    MinDriveEngineSpeed2ndDecel,
    MinDriveEngineSpeed2nd,
    MinDriveEngineSpeedGreater2nd,
    TraceTimesCount,
    NoOfGearsFinal,
    InDecelerationToStandstill,
):
    """
    Define minimum engine speeds when vehicle is in motion (2k)

    .. note::
    The calculation of minimum engine speeds for the second gear does
    not fully confirm to the latest legislation text, but rather reflects
    the previous revision of it until (2ka) is clarified.

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param RatedEngineSpeedF:
        Contains the rated engine speed corrected if is necessary
    :type RatedEngineSpeedF: float

    :param MinDriveEngineSpeed1st:
        This is a legacy parameter used until regulation GRPE-75-23.
        This value may be used to increase the calculated value.
        Annex 2 (2k) n_min_drive = n_idle for n_gear:1
        The minimum engine speed when the vehicle is in motion.
    :type MinDriveEngineSpeed1st: float

    :param MinDriveEngineSpeed1stTo2nd:
        This is a legacy parameter used until regulation GRPE-75-23.
        This value may be used to increase the calculated value.
        Annex 2 (2ka) n_min_drive = 1.15 x n_idle for n_gear:1->2
        The minimum engine speed for transitions from first to second gear.
    :type MinDriveEngineSpeed1stTo2nd: float

    :param MinDriveEngineSpeed2ndDecel:
        This is a legacy parameter used until regulation GRPE-75-23.
        This value may be used to increase the calculated value.
        Annex 2 (2kb) n_min_drive = n_idle for n_gear:2
        The minimum engine speed for decelerations to standstill in second gear.
    :type MinDriveEngineSpeed2ndDecel: float

    :param MinDriveEngineSpeed2nd:
        This is a legacy parameter used until regulation GRPE-75-23.
        This value may be used to increase the calculated value.
        Annex 2 (2kc) n_min_drive = 0.9 x n_idle for n_gear:2
    :type MinDriveEngineSpeed2nd: float

    :param MinDriveEngineSpeedGreater2nd:
        This is a legacy parameter used until regulation GRPE-75-23.
        This value may be used to increase the calculated value.
        Annex 2 (2k) n_min_drive = n_idle + 0.125 × ( n_rated - n_idle ) for n_gear:3..
        This value shall be referred to as n_min_drive_set.
        The minimum engine speed for all driving conditions in gears greater than 2.
    :type MinDriveEngineSpeedGreater2nd: float

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param InDecelerationToStandstill:
        The array that contains the seconds from deceleration to standstill as a True
    :type InDecelerationToStandstill: boolean array

    :return MinDrivesI:
        Minimum engine speeds when vehicle is in motion
    :rtype MinDrivesI: array

    :return CalculatedMinDriveEngineSpeedGreater2nd:
        The minimum drive engine speed grater than second
    :rtype CalculatedMinDriveEngineSpeedGreater2nd: float

    :return MinDrive1stTo2nd:
        Annex 2 (2ka) n_min_drive = 1.15 x n_idle for n_gear:1->2
        The minimum engine speed for transitions from first to second gear.
        This is the maximum of calculated value and input parameter value.
    :rtype MinDrive1stTo2nd: float

    :param MinDrive1st:
        Annex 2 (2k) n_min_drive = n_idle for n_gear:1
        The minimum engine speed when the vehicle is in motion.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive1st: float

    :return MinDrive2ndDecel:
        Annex 2 (2kb) n_min_drive = n_idle for n_gear:2
        The minimum engine speed for decelerations to standstill in second gear.
        This is the maximum of calculated value and input parameter value.
    :rtype MinDrive2ndDecel: float

    :return MinDrive2nd:
        Annex 2 (2kc) n_min_drive = 0.9 x n_idle for n_gear:2
        The minimum engine speed for all other driving conditions in second gear.
        This is the maximum of calculated value and input parameter value.
    :rtype MinDrive2nd: float

    :return MinDriveGreater2nd:
        Annex 2 (2k) n_min_drive = n_idle + 0.125 × ( n_rated - n_idle ) for n_gear:3..
        This value shall be referred to as n_min_drive_set.
        The minimum engine speed for all driving conditions in gears greater than 2.
        This is the maximum of calculated value and input parameter value.
    :rtype MinDriveGreater2nd: float
    """
    CalculatedMinDriveEngineSpeed1st = IdlingEngineSpeed
    CalculatedMinDriveEngineSpeed1stTo2nd = np.round(1.15 * IdlingEngineSpeed)
    CalculatedMinDriveEngineSpeed2ndDecel = IdlingEngineSpeed
    CalculatedMinDriveEngineSpeed2nd = 0.9 * IdlingEngineSpeed
    CalculatedMinDriveEngineSpeedGreater2nd = IdlingEngineSpeed + 0.125 * (
        RatedEngineSpeedF - IdlingEngineSpeed
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
    """
    Calculate accelerations.

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param TraceTimes:
        Times for each vehicle speed required re-sampled in 1Hz
    :type TraceTimes: array

    :return Accelerations:
         The acceleration required for the whole cycle re-sampled in 1Hz
    :rtype accelerations: array
    """
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
    """
    Determine the gear, in which the maximum vehicle speed is reached (2i)
    The maximum vehicle speed is defined as the vehicle speed, at which the
    available power equals the road load power caused by friction and
    aerodynamics, and is usually not covered by typical traces. That is why
    the calculation is based on sufficient fictive road load speeds.

    :param MinDrivesI:
        Minimum engine speeds when vehicle is in motion
    :type MinDrivesI: array

    :param CalculatedMinDriveEngineSpeedGreater2nd:
        The minimum drive engine speed grater than second
    :type CalculatedMinDriveEngineSpeedGreater2nd: float

    :param MinDriveEngineSpeedGreater2ndAccel:
        Annex 2 (2j) n_min_drive_up
        Values higher than n_min_drive_set may be used for n_gear > 2.
        The manufacturer may specify a value
        for acceleration/constant speed phases (n_min_drive_up).
    :type MinDriveEngineSpeedGreater2ndAccel: float

    :param MinDriveEngineSpeedGreater2ndDecel:
        Annex 2 (2j) n_min_drive_down
        Values higher than n_min_drive_set may be used for n_gear > 2.
        The manufacturer may specify a value
        for deceleration phases (n_min_drive_down).
    :type MinDriveEngineSpeedGreater2ndDecel: float

    :param MinDriveEngineSpeedGreater2ndAccelStartPhase:
        Annex 2 (2j) n_min_drive_up_start
        Heinz Steven Tool n_min_drive_start_up
        For an initial period of time (t_start_phase),
        the manufacturer may specify higher values
        (n_min_drive_start and/or n_min_drive_up_start)
        for the values n_min_drive and/or n_min_drive_up
        for n_gear > 2.
        This requirement was implemented with other parameters
        by the reference implementation Heinz Steven Tool.
    :type MinDriveEngineSpeedGreater2ndAccelStartPhase: float

    :param MinDriveEngineSpeedGreater2ndDecelStartPhase:
        Annex 2 (2j) n_min_drive_start
        Heinz Steven Tool n_min_drive_start_down
        For an initial period of time (t_start_phase),
        the manufacturer may specify higher values
        (n_min_drive_start and/or n_min_drive_up_start)
        for the values n_min_drive and/or n_min_drive_up
        for n_gear > 2.
        This requirement was implemented with other parameters
        by the reference implementation Heinz Steven Tool.
    :type MinDriveEngineSpeedGreater2ndDecelStartPhase: float

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param TimeEndOfStartPhase:
        Annex 2 (2j) t_start_phase
        For an initial period of time (t_start_phase),
        the manufacturer may specify higher values
        (n_min_drive_start and/or n_min_drive_up_start)
        for the values n_min_drive and/or n_min_drive_up
        for n_gear > 2.
        The input parameter here is used in combination with
        MinDriveEngineSpeedGreater2ndAccelStartPhase and
        MinDriveEngineSpeedGreater2ndDecelStartPhase.
    :type TimeEndOfStartPhase: array

    :param TraceTimes:
        Times for each vehicle speed required re-sampled in 1Hz
    :type TraceTimes: array

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param Accelerations:
         The acceleration required for the whole cycle re-sampled in 1Hz
    :type Accelerations: array

    :return MinDrives:
        Samples which have acceleration values >= -0.1389 m/s² ( = 0.5 (km/h)/s )
        shall belong to the acceleration/constant speed phases.
    :rtype MinDrives: array
    """

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
    """
    The maximum vehicle speed is defined as the vehicle speed, at which the
    available power equals the road load power caused by friction and
    aerodynamics, and is usually not covered by typical traces. That is why
    the calculation is based on sufficient fictive road load speeds.

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :param f0:
        The constant road load coefficient,
        i.e. independent of velocity, caused by internal frictional resistances.
    :type f0: float

    :param f1:
        The linear road load coefficient,
        i.e. proportional to velocity, caused by tyres rolling resistances.
    :type f1: float

    :param f2:
        The quadratic road load coefficient,
        i.e. quadratical to velocity, caused by aerodynamic resistances.
    :type f2: float

    :param NdvRatios:
        The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng after apply the exclusion of first gear if
        is necessary.
    :type NdvRatios: array

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :return GearAtMaxVehicleSpeed:
        The gear that have the maximum vehicle speed
    :rtype GearAtMaxVehicleSpeed: float

    :return MaxVehicleSpeed:
        The maximum vehicle speed
    :rtype MaxVehicleSpeed: float
    """
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
    RatedEnginePowerF,
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
    RatedEnginePowerF,
    NdvRatios,
    GearAtMaxVehicleSpeed,
    RequiredVehicleSpeeds,
    MaxVehicleSpeed,
    NoOfGearsFinal,
):
    """
    Determine maximum engine speed (2g)

    n_max1 = n_95_high
    If n_95_high cannot be determined
    because the engine speed is limited to a lower value n_lim for all gears
    and the corresponding full load power is higher than 95 per cent of rated power,
    n_95_high shall be set to n_lim.

    :param EngineSpeedLimitVMax:
        Annex 2, (2i) n_lim
        The maximum engine speed for the purpose of limiting maximum vehicle speed.
        (value 0 means unlimited vehicle speed)
    :type EngineSpeedLimitVMax: float

    :param Max95EngineSpeedFinal:
         Annex 2 (2g) n_max1 = n_95_high adjusted
         If n_95_high cannot be determined because the engine speed is limited to
         a lower value n_lim for all gears and the corresponding full load power
         is higher than 95 per cent of rated power, n_95_high shall be set to n_lim.
    :type Max95EngineSpeedFinal: float

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :param RatedEnginePowerF:
        Contains the rated engine power corrected if is necessary
    :type RatedEnginePowerF: float

    :param NdvRatios:
        The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng after apply the exclusion of first gear if
        is necessary.
    :type NdvRatios: array

    :param GearAtMaxVehicleSpeed:
        The gear that have the maximum vehicle speed
    :type GearAtMaxVehicleSpeed: float

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param MaxVehicleSpeed:
        The maximum vehicle speed
    :type MaxVehicleSpeed: float

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :return MaxEngineSpeed:
        The maximum engine speed
    :rtype MaxEngineSpeed: float

    :return GearAtMaxVehicleSpeedFinal:
        Annex 2 (2i) ng_vmax
        The gear in which the maximum vehicle speed is reached.
    :rtype GearAtMaxVehicleSpeedFinal: integer

    :return MaxVehicleSpeedFinal:
        Annex 2 (2g, 2i) v_max,vehicle
        The maximum vehicle speed reachable
        using the gear in which the maximum vehicle speed can be reached.
    :rtype MaxVehicleSpeedFinal: float

    :return EngineSpeedAtGearAtMaxRequiredSpeed:
        The engine speed at gear maximum required speed
    :rtype EngineSpeedAtGearAtMaxRequiredSpeed: float

    :return EngineSpeedAtGearAtMaxVehicleSpeed:
        The engine speed at gear at maximum vehicle speed
    :rtype EngineSpeedAtGearAtMaxVehicleSpeed: float
    """
    NoOfGears = NoOfGearsFinal

    if EngineSpeedLimitVMax > 0 and EngineSpeedLimitVMax < Max95EngineSpeedFinal:
        from scipy.interpolate import interp1d

        PowerAtEngineSpeedLimitVMax = interp1d(
            PowerCurveEngineSpeeds, PowerCurvePowers
        )(EngineSpeedLimitVMax)
        if PowerAtEngineSpeedLimitVMax > 0.95 * RatedEnginePowerF:
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
    """
    Calculate required powers (3.1)

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param Accelerations:
         The acceleration required for the whole cycle re-sampled in 1Hz
    :type Accelerations: array

    :param f0:
        The constant road load coefficient,
        i.e. independent of velocity, caused by internal frictional resistances.
    :type f0: float

    :param f1:
        The linear road load coefficient,
        i.e. proportional to velocity, caused by tyres rolling resistances.
    :type f1: float

    :param f2:
        The quadratic road load coefficient,
        i.e. quadratical to velocity, caused by aerodynamic resistances.
    :type f2: float

    :param VehicleTestMass:
        The test mass of the vehicle.
    :type VehicleTestMass: float

    :return requiredPowersF:
        Annex 2 (3.1) P_required,j
        The power required to overcome driving resistance and to accelerate
        for each second j of the cycle trace.
    :rtype requiredPowersF: array
    """
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
    """
    Determine possible gears based on required engine speeds (3.3)

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param NdvRatios:
        The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng after apply the exclusion of first gear if
        is necessary.
    :type NdvRatios: array

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: array

    :param InStandStill:
        Contains the points that are in standstill phase as a True
    :type InStandStill: boolean array

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param PhaseStarts:
        Contains the points that are start point from a phase
    :type PhaseStarts: array

    :param PHASE_ACCELERATION_FROM_STANDSTILL:
        Acceleration phase following a standstill phase
    :type PHASE_ACCELERATION_FROM_STANDSTILL: integer

    :param Accelerations:
         The acceleration required for the whole cycle re-sampled in 1Hz
    :type Accelerations: array

    :param MinDrives:
        Samples which have acceleration values >= -0.1389 m/s² ( = 0.5 (km/h)/s )
        shall belong to the acceleration/constant speed phases.
    :type MinDrives: array

    :param GearAtMaxVehicleSpeedFinal:
        Annex 2 (2i) ng_vmax
        The gear in which the maximum vehicle speed is reached.
    :type GearAtMaxVehicleSpeedFinal: integer

    :param Max95EngineSpeedFinal:
         Annex 2 (2g) n_max1 = n_95_high adjusted
         If n_95_high cannot be determined because the engine speed is limited to
         a lower value n_lim for all gears and the corresponding full load power
         is higher than 95 per cent of rated power, n_95_high shall be set to n_lim.
    :type Max95EngineSpeedFinal: float

    :return EngineSpeedAtGearAtMaxRequiredSpeed:
        The engine speed at gear maximum required speed
    :rtype EngineSpeedAtGearAtMaxRequiredSpeed: float

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :param InDecelerationToStandstill:
        The array that contains the seconds from deceleration to standstill as a True
    :type InDecelerationToStandstill: boolean array

    :return RequiredEngineSpeeds:
        Annex 2 (3.2) n_i,j
        The engine speeds required
        for each gear i from 1 to ng and
        for each second j of the cycle trace.
        Note that this are the uncorrected values n_i,j
        ie without the increments required by Annex 2 (3.3)
    :rtype RequiredEngineSpeeds: array

    :return InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :rtype InitialRequiredEngineSpeeds: array

    :return PossibleGearsByEngineSpeed:
        The possible gear that can be used for each second.
    :rtype PossibleGearsByEngineSpeed: boolean array

    :return AccelerationFromStandstillStarts:
        The phase start seconds when the phase is going to acceleration
        from stand still.
    :rtype AccelerationFromStandstillStarts: array

    :return ClutchDisengagedByGear:
        The clutch disengaged by each gear and each second.
    :rtype ClutchDisengagedByGear: boolean array

    :return ClutchUndefinedByGear:
        The clutch undefined by each gear and each second.
    :rtype ClutchUndefinedByGear: boolean array

    :return ClutchDisengaged:
        The clutch disengaged by each second.
    :rtype ClutchDisengaged: boolean array

    :return ClutchUndefined:
        The clutch undefined by each second.
    :rtype ClutchUndefined: boolean array

    :return AdvancedClutchDisengage:
        The seconds in which the advanced clutch disengage
    :rtype AdvancedClutchDisengage: list
    """
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
    """deCalculate available powers (3.4)

    Additional safety margins defined together with the power curve take precedence
    over the legacy additional safety margins exponentially decaying from start to
    end engine speed

    :param DefinedPowerCurveAdditionalSafetyMargins:
        Boolean that define if the additional save margins are present
    :type DefinedPowerCurveAdditionalSafetyMargins: boolean

    :param RequiredEngineSpeeds:
        Annex 2 (3.2) n_i,j
        The engine speeds required
        for each gear i from 1 to ng and
        for each second j of the cycle trace.
        Note that this are the uncorrected values n_i,j
        ie without the increments required by Annex 2 (3.3)
    :type RequiredEngineSpeeds: array

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :param PowerCurveASM:
        Contains the power curve additional save margin
    :type PowerCurveASM: array

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :type InitialRequiredEngineSpeeds: array
    """

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
    """
    Determine possible gears based on available powers (3.5)

    :param AvailablePowers:
        Annex 2 (3.4) P_available_i,j
        The power available for each gear i from 1 to ng and for each second j
        of the cycle trace.
        Note that this power values are determined from uncorrected values n_i,j
        i.e. without the engine speed increments required by Annex 2 (3.3)
    :type AvailablePowers: array

    :param requiredPowersF:
        Annex 2 (3.1) P_required,j
        The power required to overcome driving resistance and to accelerate
        for each second j of the cycle trace.
    :type requiredPowersF: array

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :return PossibleGearsByEngineSpeed:
        The possible gear that can be used for each second.
    :rtype PossibleGearsByEngineSpeed: boolean array

    :return PossibleGearsByAvailablePowersWithTotalSafetyMargin:
        The possible gears by available powers with total safety margin
        (following section 3.5 of Sub-Annex 2)
    :rtype PossibleGearsByAvailablePowersWithTotalSafetyMargin: boolean array
    """
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
    """
    Determine initial gears

    :param InStandStill:
        Contains the points that are in standstill phase as a True
    :type InStandStill: boolean array

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param PossibleGearsByEngineSpeed:
        The possible gear that can be used for each second.
    :type PossibleGearsByEngineSpeed: boolean array

    :param PossibleGearsByAvailablePowersWithTotalSafetyMargin:
        The possible gears by available powers with total safety margin
        (following section 3.5 of Sub-Annex 2)
    :type PossibleGearsByAvailablePowersWithTotalSafetyMargin: boolean array

    :param AccelerationFromStandstillStarts:
        The phase start seconds when the phase is going to acceleration
        from stand still.
    :type AccelerationFromStandstillStarts: array

    :param PhaseEnds:
        Contains the points that are end point from a phase
    :type PhaseEnds: array

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: array

    :param PHASE_ACCELERATION_FROM_STANDSTILL:
        Acceleration phase following a standstill phase
    :type PHASE_ACCELERATION_FROM_STANDSTILL: integer

    :param InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :type InitialRequiredEngineSpeeds: array

    :param MinDrive1stTo2nd:
        Annex 2 (2ka) n_min_drive = 1.15 x n_idle for n_gear:1->2
        The minimum engine speed for transitions from first to second gear.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive1stTo2nd: float

    :return InitialGears:
        The initial gears calculated by each second
    :rtype InitialGears: array

    :return PossibleGears:
        The possible gears calculated by each second
    :rtype PossibleGears: array
    """
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
            gears[0:secondGearEngaged] = 1
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
    """
    Apply corrections defined in section 4 of the sub-Annex 2

    :param InitialGears:
        The initial gears calculated by each second
    :type InitialGears: array

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: array

    :param PhaseStarts:
        Contains the points that are start point from a phase
    :type PhaseStarts: array

    :param PhaseEnds:
        Contains the points that are end point from a phase
    :type PhaseEnds: array

    :param PHASE_ACCELERATION_FROM_STANDSTILL:
        Acceleration phase following a standstill phase
    :type PHASE_ACCELERATION_FROM_STANDSTILL: integer

    :param PHASE_ACCELERATION:
        Acceleration phase
    :type PHASE_ACCELERATION: integer

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param PossibleGears:
        The possible gears calculated by each second
    :type PossibleGears: array

    :param InAcceleration:
        Contains the points that are in acceleration phase as a True
    :type InAcceleration: boolean array

    :param InConstantSpeed:
        Contains the points that are in constant speed phase as a True
    :type InConstantSpeed: boolean array

    :param InAccelerationAnyDuration:
         some gear corrections ignore the duration of acceleration phases
         so save acceleration phases with any duration here
    :type InAccelerationAnyDuration: boolean array

    :param ClutchDisengagedByGear:
        The clutch disengaged by each gear and each second.
    :type ClutchDisengagedByGear: boolean array

    :param ClutchUndefinedByGear:
        The clutch undefined by each gear and each second.
    :type ClutchUndefinedByGear: boolean array

    :param PHASE_DECELERATION:
        time period of more than 2 seconds with required vehicle
                speed >= 1km/h and monotonically decreasing
    :type PHASE_DECELERATION: integer

    :param PHASE_DECELERATION_TO_STANDSTILL:
        DECELERATION phase preceding a STANDSTILL phase
    :type PHASE_DECELERATION_TO_STANDSTILL: integer

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param SuppressGear0DuringDownshifts:
        Sub-Annex 2 (4f).If a gear is used for only 1 second during a deceleration phase
        it shall be replaced by gear 0 with clutch disengaged, in order to avoid too high
        engine speeds. But if this is not an issue, the manufacturer may allow to use the
        lower gear of the following second directly instead of gear 0 for downshifts of
        up to 3 steps.
    :type SuppressGear0DuringDownshifts: boolean

    :param ClutchDisengaged:
        The clutch disengaged by each second.
    :type ClutchDisengaged: boolean array

    :param InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :type InitialRequiredEngineSpeeds: array

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param Phases:
        The list of phases that are used during whole cycle
    :type Phases: array

    :param InStandStill:
        Contains the points that are in standstill phase as a True
    :type InStandStill: boolean array

    :param InDecelerationToStandstill:
        The array that contains the seconds from deceleration to standstill as a True
    :type InDecelerationToStandstill: boolean array

    :param InDeceleration:
        Contains the points that are in deceleration phase as a True
    :type InDeceleration: boolean array

    :return InitialGearsFinal:
        The initial gears after apply corrections calculated by each second.
    :rtype InitialGearsFinal: array

    :return CorrectionsCells:
        Array of gear correction strings for debugging. This contains a historic
        transformation of each gear during all execution and the transformation
        applied.
    :rtype CorrectionsCells: array

    :return ClutchDisengagedByGearFinal:
        The clutch disengaged by each gear and each second after apply corrections.
    :rtype ClutchDisengagedByGearFinal: boolean array

    :return ClutchUndefinedByGearFinal:
        The clutch undefined by each gear and each second after apply corrections.
    :rtype ClutchUndefinedByGearFinal: boolean array
    """
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
    """
    Calculate Average Gear

    :param Phases:
        The list of phases that are used during whole cycle
    :type Phases: array

    :param PHASE_STANDSTILL:
        Time period with required vehicle speed < 1km/h
    :type PHASE_STANDSTILL: integer

    :param InitialGearsFinal:
        The initial gears after apply corrections calculated by each second.
    :type InitialGearsFinal: array

    :return AverageGear:
        Annex 2 (5) average gear
        In order to enable the assessment of the correctness of the calculation,
        the average gear for v >= 1 km/h, rounded to four places of decimal,
        shall be calculated and recorded.
    :rtype AverageGear: float

    :return PhaseSum:
        The all phases that are different of standstill phase
    :rtype PhaseSum: boolean array
    """
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
    """
    Calculate average gear

    :param PhaseSum:
        The all phases that are different of standstill phase
    :type PhaseSum: boolean array

    :param InitialGearsFinal:
        The initial gears after apply corrections calculated by each second.
    :type InitialGearsFinal: array

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :return ChecksumVxGear:
        Checksum of v * gear for v >= 1 km/h rounded to four places of decimal
    :rtype ChecksumVxGear: float
    """
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
    """
    Interleave the clutch Sub-Annex 2 (1.5)

    .. note::
    The prescriptions for the clutch operation shall not be applied if the clutch
    is operated automatically without the need of an engagement or disengagement
    of the driver.

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: integer

    :param InitialGearsFinal:
        The initial gears after apply corrections calculated by each second.
    :type InitialGearsFinal: array

    :param ClutchDisengagedByGearFinal:
        The clutch disengaged by each gear and each second after apply corrections.
    :type ClutchDisengagedByGearFinal: boolean array

    :param ClutchDisengaged:
        The clutch disengaged by each second.
    :type ClutchDisengaged: boolean array

    :param ClutchUndefinedByGearFinal:
        The clutch undefined by each gear and each second after apply corrections.
    :type ClutchUndefinedByGearFinal: boolean array

    :param ClutchUndefined:
        The clutch undefined by each second.
    :type ClutchUndefined: boolean array

    :param AutomaticClutchOperation:
        Sub-Annex 2 (1.5)
        The prescriptions for the clutch operation shall not be applied if the clutch
        is operated automatically without the need of an engagement or disengagement
        of the driver.
    :type AutomaticClutchOperation: boolean

    :param InDeceleration:
        Contains the points that are in deceleration phase as a True
    :type InDeceleration: boolean array

    :param AdvancedClutchDisengage:
        The seconds in which the advanced clutch disengage
    :type AdvancedClutchDisengage: list

    :return InitialGearsFinalAfterClutch:
        The initial gears after apply corrections calculated by each second and the
        interleave clutch.
    :rtype InitialGearsFinalAfterClutch: array

    :return ClutchDisengagedFinal:
        The clutch disengaged by each second after apply the interleave clutch
    :rtype ClutchDisengagedFinal: boolean array

    :return ClutchUndefinedFinal:
        The clutch undefined by each second after apply the interleave clutch
    :rtype ClutchUndefinedFinal: boolean array
    """
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
    """
    Remove duplicate gears

    :param InitialGearsFinalAfterClutch:
        The initial gears after apply corrections calculated by each second and the
        interleave clutch.
    :type InitialGearsFinalAfterClutch: array

    :param ClutchUndefinedFinal:
        The clutch undefined by each second after apply the interleave clutch
    :type ClutchUndefinedFinal: boolean array

    :param ClutchDisengagedFinal:
        The clutch disengaged by each second after apply the interleave clutch
    :type ClutchDisengagedFinal: boolean array

    :return ClutchHST:
        Array of clutch state names as used by the Heinz Steven Tool (HST).
    :rtype ClutchHST: array

    :return GearSequenceStarts:
        Array that contains the position of the gear sequence start for the different
        gears.
        .. note::
        A clutch disengagement and a gear change cannot be indicated at the same time
       and the clutch disengagement will therefore be indicated one second earlier.
    :rtype GearSequenceStarts: array

    :return GearNames:
        The name of gear to used by each gear sequence starts.
    :rtype GearNames: array
    """
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
    """
    Reduce vehicle speed if not enough power is available

    :param DefinedPowerCurveAdditionalSafetyMargins:
        Boolean that define if the additional save margins are present
    :type DefinedPowerCurveAdditionalSafetyMargins: boolean

    :param PowerCurveEngineSpeeds:
        Contains the power curve engine speeds
    :type PowerCurveEngineSpeeds: array

    :param PowerCurvePowers:
        Contains the power curve powers
    :type PowerCurvePowers: array

    :param SafetyMargin:
        Annex 2 (3.4) SM
        The safety margin is accounting for the difference between the
        stationary full load condition power curve and the power available
        during transition conditions.
        SM is set to 10 per cent.
    :type SafetyMargin: float

    :param PowerCurveASM:
        Contains the power curve additional save margin
    :type PowerCurveASM: array

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param RequiredEngineSpeeds:
        Annex 2 (3.2) n_i,j
        The engine speeds required
        for each gear i from 1 to ng and
        for each second j of the cycle trace.
        Note that this are the uncorrected values n_i,j
        ie without the increments required by Annex 2 (3.3)
    :type RequiredEngineSpeeds: array

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param f0:
        The constant road load coefficient,
        i.e. independent of velocity, caused by internal frictional resistances.
    :type f0: float

    :param f1:
        The linear road load coefficient,
        i.e. proportional to velocity, caused by tyres rolling resistances.
    :type f1: float

    :param f2:
        The quadratic road load coefficient,
        i.e. quadratical to velocity, caused by aerodynamic resistances.
    :type f2: float

    :param VehicleTestMass:
        The test mass of the vehicle.
    :type VehicleTestMass: float

    :param requiredPowersF:
        Annex 2 (3.1) P_required,j
        The power required to overcome driving resistance and to accelerate
        for each second j of the cycle trace.
    :type requiredPowersF: array

    :param ClutchDisengagedFinal:
        The clutch disengaged by each second after apply the interleave clutch
    :type ClutchDisengagedFinal: boolean array

    :param ClutchUndefinedFinal:
        The clutch undefined by each second after apply the interleave clutch
    :type ClutchUndefinedFinal: boolean array

    :param InitialGearsFinalAfterClutch:
        The initial gears after apply corrections calculated by each second and the
        interleave clutch.
    :type InitialGearsFinalAfterClutch: array

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: integer

    :param AvailablePowers:
        Annex 2 (3.4) P_available_i,j
        The power available for each gear i from 1 to ng and for each second j
        of the cycle trace.
        Note that this power values are determined from uncorrected values n_i,j
        i.e. without the engine speed increments required by Annex 2 (3.3)
    :type AvailablePowers: array

    :param NdvRatios:
        The ratio obtained by dividing the engine speed n by the vehicle speed v
        for each gear i form 1 to ng after apply the exclusion of first gear if
        is necessary.
    :type NdvRatios: array

    :return AvailablePowersFinal:
        Annex 2 (3.4) P_available_i,j
        The power available for each gear i from 1 to ng and for each second j
        of the cycle trace, after check vehicle speed.
        Note that this power values are determined from uncorrected values n_i,j
        i.e. without the engine speed increments required by Annex 2 (3.3)
    :rtype AvailablePowersFinal: array
    """

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


@sh.add_function(dsp, outputs=["shift_points"])
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
    """
    Assign outputs in the final dictionary

    :param TraceTimes:
        Times for each vehicle speed required re-sampled in 1Hz
    :type TraceTimes: array

    :param GearSequenceStarts:
        Array that contains the position of the gear sequence start for the different
        gears.
        .. note::
        A clutch disengagement and a gear change cannot be indicated at the same time
        and the clutch disengagement will therefore be indicated one second earlier.
    :type GearSequenceStarts: array

    :param GearNames:
        The name of gear to used by each gear sequence starts.
    :type GearNames: array

    :return AverageGear:
        Annex 2 (5) average gear
        In order to enable the assessment of the correctness of the calculation,
        the average gear for v >= 1 km/h, rounded to four places of decimal,
        shall be calculated and recorded.
    :rtype AverageGear: float

    :param Max95EngineSpeedFinal:
         Annex 2 (2g) n_max1 = n_95_high adjusted
         If n_95_high cannot be determined because the engine speed is limited to
         a lower value n_lim for all gears and the corresponding full load power
         is higher than 95 per cent of rated power, n_95_high shall be set to n_lim.
    :type Max95EngineSpeedFinal: float

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: array

    :param requiredPowersF:
        Annex 2 (3.1) P_required,j
        The power required to overcome driving resistance and to accelerate
        for each second j of the cycle trace.
    :type requiredPowersF: array

    :param RequiredEngineSpeeds:
        Annex 2 (3.2) n_i,j
        The engine speeds required
        for each gear i from 1 to ng and
        for each second j of the cycle trace.
        Note that this are the uncorrected values n_i,j
        ie without the increments required by Annex 2 (3.3)
    :type RequiredEngineSpeeds: array

    :param PossibleGearsByEngineSpeed:
        The possible gear that can be used for each second.
    :type PossibleGearsByEngineSpeed: boolean array

    :param AvailablePowersFinal:
        Annex 2 (3.4) P_available_i,j
        The power available for each gear i from 1 to ng and for each second j
        of the cycle trace, after check vehicle speed.
        Note that this power values are determined from uncorrected values n_i,j
        i.e. without the engine speed increments required by Annex 2 (3.3)
    :type AvailablePowersFinal: array

    :param InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :type InitialRequiredEngineSpeeds: array

    :param InitialAvailablePowers:
        Annex 2 (3.4) P_available_i,j (initials)
        The power available for each gear i from 1 to ng and for each second j
        of the cycle trace.
        Note that this power values are determined from uncorrected values n_i,j
        i.e. without the engine speed increments required by Annex 2 (3.3)
    :type InitialAvailablePowers: array

    :param FullPowerCurve:
        Annex 2 (2h) and (3.4) n ==> P_wot(n), ASM
        The full load power curve over the engine speed range.
    :type FullPowerCurve: array

    :param EngineSpeedAtGearAtMaxRequiredSpeed:
        The engine speed at gear maximum required speed
    :type EngineSpeedAtGearAtMaxRequiredSpeed: float

    :param EngineSpeedAtGearAtMaxVehicleSpeed:
        The engine speed at gear at maximum vehicle speed
    :type EngineSpeedAtGearAtMaxVehicleSpeed: float

    :param MaxEngineSpeed:
        The maximum engine speed
    :type MaxEngineSpeed: float

    :param MaxVehicleSpeedFinal:
        Annex 2 (2g, 2i) v_max,vehicle
        The maximum vehicle speed reachable
        using the gear in which the maximum vehicle speed can be reached.
    :type MaxVehicleSpeedFinal: float

    :param GearAtMaxVehicleSpeedFinal:
        Annex 2 (2i) ng_vmax
        The gear in which the maximum vehicle speed is reached.
    :type GearAtMaxVehicleSpeedFinal: integer

    :param MinDrive1st:
        Annex 2 (2k) n_min_drive = n_idle for n_gear:1
        The minimum engine speed when the vehicle is in motion.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive1st: float

    :param MinDrive1stTo2nd:
        Annex 2 (2ka) n_min_drive = 1.15 x n_idle for n_gear:1->2
        The minimum engine speed for transitions from first to second gear.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive1stTo2nd: float

    :param MinDrive2ndDecel:
        Annex 2 (2kb) n_min_drive = n_idle for n_gear:2
        The minimum engine speed for decelerations to standstill in second gear.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive2ndDecel: float

    :param MinDrive2nd:
        Annex 2 (2kc) n_min_drive = 0.9 x n_idle for n_gear:2
        The minimum engine speed for all other driving conditions in second gear.
        This is the maximum of calculated value and input parameter value.
    :type MinDrive2nd: float

    :param MinDriveGreater2nd:
        Annex 2 (2k) n_min_drive = n_idle + 0.125 × ( n_rated - n_idle ) for n_gear:3..
        This value shall be referred to as n_min_drive_set.
        The minimum engine speed for all driving conditions in gears greater than 2.
        This is the maximum of calculated value and input parameter value.
    :type MinDriveGreater2nd: float

    :param InitialGearsFinalAfterClutch:
        The initial gears after apply corrections calculated by each second and the
        interleave clutch.
    :type InitialGearsFinalAfterClutch: array

    :param ClutchDisengagedFinal:
        The clutch disengaged by each second after apply the interleave clutch
    :type ClutchDisengagedFinal: boolean array

    :param ClutchUndefinedFinal:
        The clutch undefined by each second after apply the interleave clutch
    :type ClutchUndefinedFinal: boolean array

    :param ClutchHST:
        Array of clutch state names as used by the Heinz Steven Tool (HST).
    :type ClutchHST: array

    :param CorrectionsCells:
        Array of gear correction strings for debugging. This contains a historic
        transformation of each gear during all execution and the transformation
        applied.
    :type CorrectionsCells: array

    :param ChecksumVxGear:
        Checksum of v * gear for v >= 1 km/h rounded to four places of decimal.
    :type ChecksumVxGear: float

    :return shift_points:
        Dictionary that contains the all input parameters with the expected
        output format.
    :rtype shift_points: dict
    """
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

    shift_points = {
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

    return shift_points
