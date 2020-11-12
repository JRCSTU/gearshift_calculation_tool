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
    from scipy.interpolate import interp1d

    originalTraceTimes = np.arange(int(Trace[:, 0][-1] + 1)).astype(int)
    originalVehicleSpeeds = np.around(
        interp1d(Trace[:, 0].astype(int), Trace[:, 1])(originalTraceTimes), 4
    )
    originalTraceTimesCount = len(originalTraceTimes)
    return originalTraceTimes, originalVehicleSpeeds, originalTraceTimesCount


@sh.add_function(dsp, outputs=["phaseStarts", "phaseEnds"])
def identify_phases(PhaseLengths, originalTraceTimes):
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

    scalingStartIndex = np.where(originalTraceTimes >= ScalingStartTimes)[0][0]

    correctionStartIndex = np.where(originalTraceTimes >= ScalingCorrectionTimes)[0][0]

    scalingEndIndex = np.where(originalTraceTimes >= ScalingEndTimes)[0][0]

    downscaledVehicleSpeeds = np.copy(originalVehicleSpeeds)

    for i in range(scalingStartIndex, correctionStartIndex - 1):
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

    for i in range(scalingStartIndex + 1, scalingEndIndex):
        downscaledVehicleSpeeds[i] = (
            downscaledVehicleSpeeds[i - 1]
            + accelerations[i] * (1 - correctionFactor) * 3.6
        )

    downscaledVehicleSpeeds = np.round(downscaledVehicleSpeeds, 4)

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
        "compensatedTraceTimes",
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
        compensatedTraceTimes,
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
        "RequiredToRatedPowerRatios": requiredToRatedPowerRatios,
        "calculatedDownscalingFactors": np.round(
            (calculatedDownscalingFactors * 1000) / 1000
        ),
        "CalculatedDownscalingPercentages": np.round(
            (calculatedDownscalingFactors * 1000) / 1000
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
