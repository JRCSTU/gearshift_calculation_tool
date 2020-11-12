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
import numpy as np

log = logging.getLogger(__name__)

dsp = sh.BlueDispatcher(
    name="GEARSHIFT calculateShiftpointsNdvFullPC model",
    description="This function calibrates the speed trance, following the Sub-Annex 2",
)


@sh.add_function(dsp, outputs=["TraceTimesInput", "RequiredVehicleSpeedsInput"])
def parse_speed_trace(speed_trace):
    TraceTimesInput = speed_trace["ApplicableTrace"]["compensatedTraceTimes"]
    RequiredVehicleSpeedsInput = speed_trace["ApplicableTrace"]["compensatedVehicleSpeeds"]
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

@sh.add_function(dsp, outputs=["a"])
def generate_gears(RatedEnginePower):
    a = RatedEnginePower
    return a
