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

.. currentmodule:: gearshift.core.model.scaleTrace

.. autosummary::
    :nosignatures:
    :toctree: scaleTrace/
"""

import schedula as sh
import numpy as np
import logging

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="GEARSHIFT speedTrace model",
    description="This function calibrates the speed trance, following the Sub-Annex 1",
)


@sh.add_function(
    dsp,
    outputs=["originalTraceTimes", "originalVehicleSpeeds", "originalTraceTimesCount"],
)
def resample_trace(Trace):
    """
    Re-sample the trace in 1Hz. If the trace was provided with higher sample rate, this may lead to data loss.

    :param Trace:
        Velocities and times from the phases of the WLTC cycle.
    :type Trace: array

    :returns:
        - originalTraceTimes (:py:class:`numpy.array`):
            Times for each vehicle speed required re-sampled in 1Hz
        - originalVehicleSpeeds (:py:class:`numpy.array`):
            The vehicle speed required for the whole cycle re-sampled in 1Hz
        - originalTraceTimesCount (:py:class:`int`):
            The length of trace times re-sampled in 1Hz
    """
    from scipy.interpolate import interp1d

    originalTraceTimes = np.arange(int(Trace[:, 0][-1] + 1)).astype(int)
    originalVehicleSpeeds = np.around(
        interp1d(Trace[:, 0].astype(int), Trace[:, 1])(originalTraceTimes), 4
    )
    originalTraceTimesCount = len(originalTraceTimes)
    return originalTraceTimes, originalVehicleSpeeds, originalTraceTimesCount


@sh.add_function(dsp, outputs=["phaseStarts", "phaseEnds"])
def identify_phases(PhaseLengths, originalTraceTimes):
    """
    This function determines the starts and ends of different phases of the whole cycles.

    :param PhaseLengths:
        Contains the lengths of the different phases.
    :type PhaseLengths: list

    :param originalTraceTimes:
        Contains the total times of the whole WLTC cycles.
    :type originalTraceTimes: array

    :returns:
        - phaseStarts (:py:class:`numpy.array`):
            The position of the beginning of each cycle
        - phaseEnds (:py:class:`numpy.array`):
            The position of the end of each cycle
    """
    originalPhaseLengths = PhaseLengths.copy()

    phaseEnds = np.cumsum(originalPhaseLengths)
    originalPhaseLengths.insert(0, 1)
    phaseStarts = np.cumsum(originalPhaseLengths[:-1])

    if np.sum(PhaseLengths) != originalTraceTimes[-1]:
        log.error(
            "INVALID_INPUT:PhaseLengths",
            "Sum of phase lengths must equal the trace length",
        )
        return sh.NONE
    else:
        return phaseStarts, phaseEnds


@sh.add_function(dsp, outputs=["accelerations"])
def calculate_accelerations(originalVehicleSpeeds, originalTraceTimes):
    """
    Calculate accelerations.

    :param originalVehicleSpeeds:
        Contains the speeds of the whole WLTC cycles.
    :type originalVehicleSpeeds: array

    :param originalTraceTimes:
        Contains the times of the whole WLTC cycles.
    :type originalTraceTimes: array

    :returns:
        - accelerations (:py:class:`numpy.array`):
            Accelerations from the whole WLTC cycles.
    """
    accelerations = np.around(
        np.append(
            np.diff(originalVehicleSpeeds) / (3.6 * np.diff(originalTraceTimes)), 0
        ),
        4,
    )
    return accelerations


@sh.add_function(dsp, outputs=["requiredPowers"])
def calculate_required_powers(
    originalVehicleSpeeds, accelerations, VehicleTestMass, f0, f1, f2
):
    """
    Calculate required powers, following the P_req,max,i function in section 8.3.

    :param originalVehicleSpeeds:
        Contains the speeds of the whole WLTC cycles.
    :type originalVehicleSpeeds: array

    :param accelerations:
        Accelerations from the whole WLTC cycles.
    :type accelerations: array

    :param VehicleTestMass:
        Vehicle test mass used during the cycle execution.
    :type VehicleTestMass: float

    :param f0:
        Represents the constant road load coefficient, i.e. independent of velocity, caused by internal
        frictional resistances.
    :type f0: float

    :param f1:
        Represents the linear road load coefficient, i.e. proportional to velocity, caused by tyres rolling
        resistances.
    :type f1: float

    :param f2:
        Represents the exponential road load coefficient, i.e. quadratical to velocity, caused by
        aerodynamic resistances.
    :type f2: float

    :returns:
        - requiredPowers (:py:class:`numpy.array`):
            The power required to overcome driving resistance and to accelerate.
    """
    requiredPowers = (
        f0 * originalVehicleSpeeds
        + f1 * np.power(originalVehicleSpeeds, 2)
        + f2 * np.power(originalVehicleSpeeds, 3)
        + 1.03 * accelerations * originalVehicleSpeeds * VehicleTestMass
    )
    requiredPowers = np.around(requiredPowers / 3600, 4)
    return requiredPowers


def _calculate_required_to_rated_power_ratio(
    indexing, requiredPowers, RatedEnginePower
):
    """
    :param indexing:
        Boolean array that select the required powers to take into account to calculate the rated power ratio
    :type indexing: boolean array

    :param requiredPowers:
        The power required to overcome driving resistance and to accelerate.
    :type requiredPowers: array

    :param RatedEnginePower:
        The maximum rated engine required
    :type RatedEnginePower: float

    :returns:
        - requiredToRatedPowerRatio (:py:class:`float`):
            The required power ratio
    """
    requiredPowersInd = [
        requiredPowers[i] for i in range(len(requiredPowers)) if indexing[i] == 1
    ]
    requiredToRatedPowerRatio = np.around(max(requiredPowersInd) / RatedEnginePower, 4)
    return requiredToRatedPowerRatio


def _calculate_downscaling_factor(
    r0,
    a1,
    b1,
    UseCalculatedDownscalingPercentage,
    DownscalingPercentage,
    requiredPowers,
    RatedEnginePower,
    indexing=None,
):
    """
    Determine the downscaling factor for the entire trace (8.3)

    :param r0:
        Factor to determine the downscaling factor
    :type r0: float

    :param a1:
        Factor to determine the downscaling factor
    :type a1: float

    :param b1:
        Factor to determine the downscaling factor
    :type b1: float

    :param UseCalculatedDownscalingPercentage:
        Boolean variable to check if is necessary calculates the downscaling factor
    :type UseCalculatedDownscalingPercentage: boolean

    :param DownscalingPercentage:
        The degree of downscaling. This value will only be used if the input parameter
        UseCalculatedDownscalingPercentage is false.
    :type DownscalingPercentage: float

    :param requiredPowers:
        The power required to overcome driving resistance and to accelerate.
    :type requiredPowers: array

    :param RatedEnginePower:
        The maximum rated engine required
    :type RatedEnginePower: float

    :param indexing:
        (optional) Boolean array that select the required powers to take into account to calculate the rated
        power ratio
    :type indexing: boolean array

    :returns:
        - downscalingFactor (:py:class:`float`):
            The downscaling factor to apply to the whole cycle
        - requiredToRatedPowerRatio (:py:class:`float`):
            The required rated power ratio after apply the downscaling factor
    """
    if UseCalculatedDownscalingPercentage:
        if indexing is None:
            indexing = np.full((len(requiredPowers)), 1)
        requiredToRatedPowerRatio = _calculate_required_to_rated_power_ratio(
            indexing, requiredPowers, RatedEnginePower
        )
        if requiredToRatedPowerRatio >= r0:
            downscalingFactor = a1 * requiredToRatedPowerRatio + b1
        else:
            downscalingFactor = 0
        return downscalingFactor, requiredToRatedPowerRatio
    else:
        if indexing is None:
            indexing = np.full((len(requiredPowers)), 1)
        requiredToRatedPowerRatio = _calculate_required_to_rated_power_ratio(
            indexing, requiredPowers, RatedEnginePower
        )
        downscalingFactor = DownscalingPercentage
        return downscalingFactor, requiredToRatedPowerRatio


def _algorithm_wltp(
    ScalingStartTimes,
    ScalingCorrectionTimes,
    ScalingEndTimes,
    originalTraceTimes,
    originalVehicleSpeeds,
    downscalingFactor,
    accelerations,
):
    """
    Algorithm WLTP

    :param ScalingStartTimes:
         Contains the start times of the segments to scale in seconds.
    :type ScalingStartTimes: array

    :param ScalingCorrectionTimes:
        Contains the times to begin the scaling correction at in seconds. The size must correspond to the size of
        ScalingStartTimes. Each value must be between the corresponding start and end times.
    :type ScalingCorrectionTimes: array

    :param ScalingEndTimes:
        Contains the end times of the segments to scale in seconds. The size must correspond to the
        size of ScalingStartTimes.
    :type ScalingEndTimes: array

    :param originalTraceTimes:
        Contains the times of the whole WLTC cycles.
    :type originalTraceTimes: array

    :param originalVehicleSpeeds:
        Contains the speeds of the whole WLTC cycles.
    :type originalVehicleSpeeds: array

    :param downscalingFactor:
        The downscaling factor for the cycle
    :type downscalingFactor: float

    :param accelerations:
        Accelerations from the whole WLTC cycles.
    :type accelerations: array

    :returns:
        - downscaledVehicleSpeeds (:py:class:`numpy.array`):
            Contains the speeds of the whole WLTC cycles downscaled.
    """

    scalingStartIndex = np.where(originalTraceTimes >= ScalingStartTimes)[0][0]

    correctionStartIndex = np.where(originalTraceTimes >= ScalingCorrectionTimes)[0][0]

    scalingEndIndex = np.where(originalTraceTimes >= ScalingEndTimes)[0][0]

    downscaledVehicleSpeeds = np.copy(originalVehicleSpeeds)

    for i in range(scalingStartIndex, correctionStartIndex):
        downscaledVehicleSpeeds[i + 1] = (
            downscaledVehicleSpeeds[i]
            + accelerations[i] * (1 - downscalingFactor) * 3.6
        )

    if scalingEndIndex < len(originalTraceTimes):
        subsequentVehicleSpeed = originalVehicleSpeeds[scalingEndIndex + 1]
    else:
        subsequentVehicleSpeed = originalVehicleSpeeds[-1]

    if originalVehicleSpeeds[correctionStartIndex] - subsequentVehicleSpeed == 0:
        # This would result in division by zero.
        # The correction factor is explicitly set to 0.
        correctionFactor = 0
    else:
        correctionFactor = (
            downscaledVehicleSpeeds[correctionStartIndex] - subsequentVehicleSpeed
        ) / (originalVehicleSpeeds[correctionStartIndex] - subsequentVehicleSpeed)

    for i in range(correctionStartIndex + 1, scalingEndIndex + 1):
        downscaledVehicleSpeeds[i] = (
            downscaledVehicleSpeeds[i - 1]
            + accelerations[i - 1] * correctionFactor * 3.6
        )

    downscaledVehicleSpeeds = np.round(downscaledVehicleSpeeds * 10) / 10

    return downscaledVehicleSpeeds


@sh.add_function(
    dsp,
    outputs=[
        "downscaled",
        "downscaledVehicleSpeeds",
        "requiredToRatedPowerRatios",
        "calculatedDownscalingFactors",
        "downscalingFactor",
        "requiredToRatedPowerRatio",
    ],
)
def downscale_trace(
    r0,
    a1,
    b1,
    UseCalculatedDownscalingPercentage,
    DownscalingPercentage,
    requiredPowers,
    RatedEnginePower,
    ScalingStartTimes,
    ScalingCorrectionTimes,
    ScalingEndTimes,
    originalTraceTimes,
    ScalingAlgorithms,
    originalVehicleSpeeds,
    ApplyDownscaling,
    accelerations,
):
    """
    Downscaling applies to very low powered class 1 vehicles or vehicles with power to mass ratios close to class
    borderlines, thus causing driveability issues.

    :param r0:
        Factor to determine the downscaling factor
    :type r0: float

    :param a1:
        Factor to determine the downscaling factor
    :type a1: float

    :param b1:
        Factor to determine the downscaling factor
    :type b1: float

    :param UseCalculatedDownscalingPercentage:
        Boolean variable to check if is necessary calculates the downscaling factor
    :type UseCalculatedDownscalingPercentage: boolean

    :param DownscalingPercentage:
        The degree of downscaling. This value will only be used if the input parameter
        UseCalculatedDownscalingPercentage is false.
    :type DownscalingPercentage: float

    :param requiredPowers:
        The power required to overcome driving resistance and to accelerate.
    :type requiredPowers: array

    :param RatedEnginePower:
        The maximum rated engine required
    :type RatedEnginePower: float

    :param ScalingStartTimes:
         Contains the start times of the segments to scale in seconds.
    :type ScalingStartTimes: array

    :param ScalingCorrectionTimes:
        Contains the times to begin the scaling correction at in seconds. The size must correspond to the size of
        ScalingStartTimes. Each value must be between the corresponding start and end times.
    :type ScalingCorrectionTimes: array

    :param ScalingEndTimes:
        Contains the end times of the segments to scale in seconds. The size must correspond to the
        size of ScalingStartTimes.
    :type ScalingEndTimes: array

    :param originalTraceTimes:
        The times used in the whole trace.
    :type originalTraceTimes: array

    :param ScalingAlgorithms:
        Represents a strings, that denotes the algorithm to use for the specific segment.
    :type ScalingAlgorithms: String

    :param originalVehicleSpeeds:
        The speeds used in the whole trace.
    :type originalVehicleSpeeds: array

    :param ApplyDownscaling:
        Specifies if the trace shall be downscaled.
    :type ApplyDownscaling: boolen

    :param accelerations:
        Accelerations from the whole WLTC cycles.
    :type accelerations: array

    :returns:
        - downscaled (:py:class:`boolean numpy.array`):
            Array that contains the values that have been downscaled as True
        - downscaledVehicleSpeeds (:py:class:`boolean numpy.array`):
            The vehicle speed after have been downscaled
        - requiredToRatedPowerRatios (:py:class:`numpy.array`):
            The required power ratios after apply the downscaling factor
        - calculatedDownscalingFactors (:py:class:`numpy.array`):
            The downscaling factor for each time of the whole cycle
        - downscalingFactor (:py:class:`float`):
            The downscaling factor applicable
        - requiredToRatedPowerRatio (:py:class:`float`):
            The maximum required to rated power ratio
    """

    downscalingFactor, requiredToRatedPowerRatio = _calculate_downscaling_factor(
        r0,
        a1,
        b1,
        UseCalculatedDownscalingPercentage,
        DownscalingPercentage,
        requiredPowers,
        RatedEnginePower,
    )

    downscaledVehicleSpeeds = np.copy(originalVehicleSpeeds)

    if ApplyDownscaling:
        if ScalingAlgorithms == "WLTP":
            downscaledVehicleSpeeds = _algorithm_wltp(
                ScalingStartTimes,
                ScalingCorrectionTimes,
                ScalingEndTimes,
                originalTraceTimes,
                originalVehicleSpeeds,
                downscalingFactor,
                accelerations,
            )

    indexing = [
        1 if ScalingStartTimes <= i and i <= ScalingEndTimes else 0
        for i in originalTraceTimes
    ]

    requiredToRatedPowerRatios = _calculate_required_to_rated_power_ratio(
        indexing, requiredPowers, RatedEnginePower
    )

    (
        calculatedDownscalingFactors,
        requiredToRatedPowerRatio,
    ) = _calculate_downscaling_factor(
        r0,
        a1,
        b1,
        UseCalculatedDownscalingPercentage,
        DownscalingPercentage,
        requiredPowers,
        RatedEnginePower,
        indexing,
    )

    downscaled = [
        1 if downscaledVehicleSpeeds[i] != originalVehicleSpeeds[i] else 0
        for i in range(len(downscaledVehicleSpeeds))
    ]

    return (
        downscaled,
        downscaledVehicleSpeeds,
        requiredToRatedPowerRatios,
        calculatedDownscalingFactors,
        downscalingFactor,
        requiredToRatedPowerRatio,
    )


@sh.add_function(dsp, outputs=["capped", "cappedVehicleSpeeds"])
def cap_trace(ApplySpeedCap, CappedSpeed, downscaledVehicleSpeeds):
    """
    Speed cap applies to vehicles that are technically able to follow the given trace, but whose maximum speed
    is limited to a value lower than the maximum speed of that trace.

    :param ApplySpeedCap:
        Specifies if the trace shall be capped to the given CappedSpeed.
    :type ApplySpeedCap: boolean

    :param CappedSpeed:
        The maximum speed of vehicles, which are technically able to follow the speed of the given trace but are not
        able to reach the maximum speed of that trace.
    :type CappedSpeed: array

    :returns:
        - capped (:py:class:`boolean numpy.array`):
            The boolean array that show the vehicle speeds capped
        - cappedVehicleSpeeds (:py:class:`numpy.array`):
            The vehicle speeds capped according to the maximum value available
    """
    cappedVehicleSpeeds = np.copy(downscaledVehicleSpeeds)

    if ApplySpeedCap:
        cappedVehicleSpeeds[cappedVehicleSpeeds > CappedSpeed] = CappedSpeed

    capped = [
        1 if downscaledVehicleSpeeds[i] != cappedVehicleSpeeds[i] else 0
        for i in range(len(cappedVehicleSpeeds))
    ]

    return capped, cappedVehicleSpeeds


@sh.add_function(
    dsp,
    outputs=[
        "compensated",
        "compensatedTraceTimes",
        "compensatedVehicleSpeeds",
        "downscaledCompensated",
        "cappedCompensated",
        "additionalSamples",
    ],
)
def compensate_trace(
    originalTraceTimesCount,
    originalTraceTimes,
    cappedVehicleSpeeds,
    PhaseLengths,
    ApplyDistanceCompensation,
    phaseStarts,
    phaseEnds,
    downscaledVehicleSpeeds,
    CappedSpeed,
    capped,
    downscaled,
):
    """
    A capped trace may need compensations to achieve the same distance as for the original trace.

    :param originalTraceTimesCount:
        The original length of the trace time
    :type originalTraceTimesCount: integer

    :param originalTraceTimes:
        The times used in the whole trace.
    :type originalTraceTimes: array

    :param cappedVehicleSpeeds:
        The vehicle speeds capped according to the maximum value available
    :type cappedVehicleSpeeds: array

    :param PhaseLengths:
        Contains the lengths of the different phases.
    :type PhaseLengths: list

    :param ApplyDistanceCompensation:
        Specifies it the trace shall be compensated for distance due to capped speeds.
    :type ApplyDistanceCompensation: boolean

    :param phaseStarts:
        The position of the beginning of each cycle.
    :type phaseStarts: array

    :param phaseEnds:
        The position of the end of each cycle.
    :type phaseEnds: array

    :param downscaledVehicleSpeeds:
        Contains the speeds of the whole WLTC cycles downscaled.
    :type downscaledVehicleSpeeds: array

    :param CappedSpeed:
        The maximum speed of vehicles, which are technically able to follow the speed of the given trace but are not
        able to reach the maximum speed of that trace.
    :type CappedSpeed: array

    :param capped:
        The boolean array that show the vehicle speeds capped.
    :type capped: boolean array

    :param downscaled:
        The boolean array that show the vehicle speeds downscaled.
    :type  downscaled: boolean array

    :returns:
        - compensated (:py:class:`boolean numpy.array`):
            The boolean array that contains the values that have been compensated as True
        - compensatedTraceTimes (:py:class:`numpy.array`):
            The trace times that array contains the new values of the compensation if
            compensation has been necessary
        - compensatedVehicleSpeeds (:py:class:`numpy.array`):
            The vehicle speeds array that contains the new values of the compensation if
            compensation has been necessary
        - downscaledCompensated (:py:class:`boolean numpy.array`):
            The boolean array that contains the values that have been downscaled and
            compensated as True
        - cappedCompensated (:py:class:`boolean numpy.array`):
            The boolean array that contains the values that have been capped and
            compensated as True
        - additionalSamples (:py:class:`numpy.array`):
            The additional samples after apply compensation
    """

    compensated = np.zeros(originalTraceTimesCount)
    compensatedTraceTimes = np.copy(originalTraceTimes)
    compensatedVehicleSpeeds = np.copy(cappedVehicleSpeeds)
    downscaledCompensated = np.copy(downscaled)
    cappedCompensated = np.copy(capped)
    additionalSamples = np.zeros(len(PhaseLengths))

    if ApplyDistanceCompensation:
        compensationStarts = np.zeros(len(PhaseLengths))
        compensationEnds = np.zeros(len(PhaseLengths))

        for phase in range(len(PhaseLengths)):
            phaseStart = phaseStarts[phase]
            phaseEnd = phaseEnds[phase]

            if phaseStart < phaseEnd:
                cappedDistance = np.sum(cappedVehicleSpeeds[phaseStart:phaseEnd])
                downscaledDistance = np.sum(
                    downscaledVehicleSpeeds[phaseStart:phaseEnd]
                )

                if cappedDistance != downscaledDistance:
                    additionalSamples[phase] = np.round(
                        (downscaledDistance - cappedDistance) / CappedSpeed
                    )
                    compensationStarts[phase] = (
                        np.sum(additionalSamples[1 : phase - 1])
                        + phaseStart
                        + np.max(np.nonzero(capped[phaseStart:phaseEnd]))
                        + 1
                    )
                    compensationEnds[phase] = (
                        compensationStarts[phase] + additionalSamples[phase]
                    )

        compensated = np.zeros(originalTraceTimesCount + int(np.sum(additionalSamples)))
        np.put(compensated, compensationStarts[compensationStarts > 0].astype(int), 1)
        np.put(compensated, compensationEnds[compensationEnds > 0].astype(int), -1)
        compensated = np.cumsum(compensated)
        compensated[compensated != 0] = 1

        compensatedTraceTimes = np.arange(originalTraceTimes[0], len(compensated))
        compensatedVehicleSpeeds = np.zeros(len(compensated))
        np.put(compensatedVehicleSpeeds, np.where(compensated == 1), CappedSpeed)
        np.put(
            compensatedVehicleSpeeds, np.where(compensated != 1), cappedVehicleSpeeds
        )

        downscaledCompensated = np.zeros(len(compensated))
        np.put(downscaledCompensated, np.where(compensated != 1), np.array(downscaled))

        cappedCompensated = np.zeros(len(compensated))
        np.put(cappedCompensated, np.where(compensated != 1), np.array(capped))

    return (
        compensated,
        compensatedTraceTimes,
        compensatedVehicleSpeeds,
        downscaledCompensated,
        cappedCompensated,
        additionalSamples,
    )


@sh.add_function(dsp, outputs=["speed_trace"])
def generate_speed_trace(
    downscalingFactor,
    requiredToRatedPowerRatio,
    requiredToRatedPowerRatios,
    calculatedDownscalingFactors,
    originalVehicleSpeeds,
    PhaseLengths,
    phaseStarts,
    phaseEnds,
    compensatedVehicleSpeeds,
    additionalSamples,
    originalTraceTimes,
    compensatedTraceTimes,
    downscaledCompensated,
    cappedCompensated,
    compensated,
):
    """
    This function creates a dictionary with the final results of the Scale trace

    :param downscalingFactor:
        The downscaling factor for the cycle
    :type downscalingFactor: float

    :param requiredToRatedPowerRatio:
        The required rated power ratio after apply the downscaling factor.
    :type requiredToRatedPowerRatio: float

    :param requiredToRatedPowerRatio:
        The required rated power ratio after apply the downscaling factors.
    :type requiredToRatedPowerRatio: float

    :param calculatedDownscalingFactors:
            The downscaling factor for the cycle
    :type calculatedDownscalingFactors: float

    :param originalVehicleSpeeds:
        The speeds used in the whole trace.
    :type originalVehicleSpeeds: array

    :param PhaseLengths:
        Contains the lengths of the different phases.
    :type PhaseLengths: list

    :param phaseStarts:
        The position of the beginning of each cycle.
    :type phaseStarts: array

    :param phaseEnds:
        The position of the end of each cycle.
    :type phaseEnds: array

    :param compensatedVehicleSpeeds:
        The vehicle speeds after apply compensation.
    :type compensatedVehicleSpeeds: array

    :param additionalSamples:
        The additional samples added to compensate the capped speed correction.
    :type additionalSamples: array

    :param originalTraceTimes:
        The times used in the whole trace.
    :type originalTraceTimes: array

    :param compensatedTraceTimes:
        The final times after applied compensation
    :type compensatedTraceTimes: array

    :param downscaledCompensated:
        The boolean array that shows the vehicle speeds downscaled and compensated
    :type downscaledCompensated: boolean array

    :param cappedCompensated:
        The boolean array that shows the vehicle speeds capped and compensated
    :param compensated:boolean array

    :returns:
        - speed_trace (:py:class:`dict`):
            The dictionary that contains the all final values of speed trace
    """
    calculatedDownscalingFactor = downscalingFactor
    if calculatedDownscalingFactor <= 0.01:
        calculatedDownscalingFactor = 0

    if calculatedDownscalingFactors <= 0.01:
        calculatedDownscalingFactors = 0

    PhaseChecksums = np.zeros(len(PhaseLengths))

    for phase in range(0, len(PhaseLengths)):
        PhaseChecksums[phase] = (
            np.round(
                np.sum(
                    originalVehicleSpeeds[phaseStarts[phase] : phaseEnds[phase]] * 10
                )
            )
            / 10
        )

    speed_trace = {
        "RequiredToRatedPowerRatio": requiredToRatedPowerRatio,
        "calculatedDownscalingFactor": np.round(
            (calculatedDownscalingFactor * 1000) / 1000
        ),
        "CalculatedDownscalingPercentage": np.round(
            (calculatedDownscalingFactor * 1000) / 1000
        )
        * 100,
        "TotalChecksum": np.round(np.sum(originalVehicleSpeeds) * 10 / 10),
        "MaxVehicleSpeed": np.max(compensatedVehicleSpeeds),
        "TotalDistance": np.round(np.sum(compensatedVehicleSpeeds / 3.6) * 10) / 10,
        "DistanceCompensatedPhaseLengths": np.add(
            PhaseLengths, additionalSamples
        ).astype(int),
        "OriginalTrace": [originalTraceTimes, originalVehicleSpeeds],
        "ApplicableTrace": {
            "compensatedTraceTimes": compensatedTraceTimes,
            "compensatedVehicleSpeeds": compensatedVehicleSpeeds,
            "downscaled": downscaledCompensated,
            "capped": cappedCompensated,
            "compensated": compensated,
        },
    }
    return speed_trace
