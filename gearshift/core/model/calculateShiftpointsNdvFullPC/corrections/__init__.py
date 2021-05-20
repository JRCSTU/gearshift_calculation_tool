# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
It provides the corrections defined in section 4 of the Sub-Annex 2 from Annex XXI from the
COMMISSION REGULATION (EU) 2017/1151.

Docstrings should provide sufficient understanding for any individual function.

Sub-Modules:

.. currentmodule:: gearshift.core.model.calculateShiftpointsNdvFullPC.corrections

.. autosummary::
    :nosignatures:
    :toctree: calculateShiftpointsNdvFullPC/corrections/
"""

import logging
import regex as re
import numpy as np


def appendCorrectionCells(
    CorrectionsCells, InitialGears, InitialGearsPrev, correctionType, correctionNbr
):
    """
     This function is just for debugging of gear corrections.
     It extends a cell array of gear correction strings by the current corrections and the resulting corrected gears.
     Each gear correction is indicated by a string combining correction type and number.
     If eg gear 2 is corrected to gear 3 by correction '4a' during the first iteration then the gear correction string
     will be extended by ' 4a1 3'.
     If eg gear 2 is not corrected then the gear correction string will be extended by ' --- 2'.

    :param CorrectionsCells:
        A cell array of gear correction strings BEFORE the current correction
    :type CorrectionsCells: numpy.array

    :param InitialGears:
        A cell array of gear numbers AFTER the current correction
    :type InitialGears: numpy.array

    :param InitialGearsPrev:
        A cell array of gear numbers BEFORE the current correction
    :type InitialGearsPrev: numpy.array

    :param InitialGearsPrev:
        A cell array of gear numbers BEFORE the current correction
    :type InitialGearsPrev: numpy.array

    :param correctionType:
        A string indicating the type of the current correction
        eg '4c'
    :type correctionType: String

    :param correctionNbr:
        A number indicating the iteration of the current correction
    :type correctionNbr: Integer

    :returns:
        - CorrectionsCells (:py:class:`numpy.array`):
            A cell array of gear correction strings AFTER the current correction.
            For example:

            '4 --- 4 4b1 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2 --- 2'

            '4 --- 4 4b1 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3'

            '5 --- 5 4b1 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 4b2 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3 --- 3'

            '5 --- 5 --- 5 4c1 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 4g2 3 --- 3 --- 3 --- 3 --- 3'

            '5 --- 5 --- 5 4c1 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 --- 4 4g2 3 --- 3 --- 3 --- 3 --- 3'

        - InitialGearsPrev (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER current correction i.e. before next correction
    """

    InitialGearsCells = list(map(str, list(map(int, list(InitialGears)))))
    InitialGearsCells = [re.sub("-1", "C", i) for i in InitialGearsCells]
    InitialGearsCells = [re.sub("10", "X", i) for i in InitialGearsCells]
    InitialGearsCells = [re.sub("nan", "?", i) for i in InitialGearsCells]
    InitialGearsCells = [re.sub(" *", "", i) for i in InitialGearsCells]

    if correctionNbr == 0:
        CorrectionsCellsF = np.asarray(InitialGearsCells)
    else:
        BlankCells = [re.sub(".*", " ", i) for i in InitialGearsCells]
        ChangedGearsCells = ["---" for i in InitialGearsCells]
        ChangedGearsCells = np.asarray(ChangedGearsCells)
        ChangedGearsCells[
            np.where(InitialGears != InitialGearsPrev)
        ] = correctionType + str(correctionNbr)
        ChangedGearsCells[
            np.intersect1d(
                np.where(np.isnan(InitialGears)), np.where(np.isnan(InitialGearsPrev))
            )
        ] = "---"
        CorrectionsCellsF = []
        for i in range(0, len(CorrectionsCells)):
            CorrectionsCellsF.append(
                str(CorrectionsCells[i])
                + str(BlankCells[i])
                + str(ChangedGearsCells[i])
                + str(BlankCells[i])
                + str(InitialGearsCells[i])
            )

    InitialGearsPrev = np.copy(InitialGears)

    return np.asarray(CorrectionsCellsF), InitialGearsPrev


def _my_cummin(A):
    min_val = np.nan
    M = []
    for i in range(0, len(A)):
        if np.isnan(min_val):
            min_val = A[i]
        elif A[i] < min_val:
            min_val = A[i]

        M.append(min_val)

    return M


def _sub2ind(array_shape, rows, cols):
    ind = rows * array_shape[0] + cols
    return ind


def applyCorrection4b(
    InitialGears,
    Corr4bToBeDoneAfterCorr4a,
    Corr4bToBeDoneAfterCorr4d,
    PhaseValues,
    PhaseStarts,
    PhaseEnds,
    PHASE_ACCELERATION_FROM_STANDSTILL,
    PHASE_ACCELERATION,
    NoOfGearsFinal,
):
    """
    Sub-Annex 2 in section 4.(b) :

    If a downshift is required during an acceleration phase
    or at the beginning of the acceleration phase
    the gear required during this downshift shall be noted (i_DS).

    The starting point of a correction procedure is defined by either
    the last previous second when i_DS was identified
    or by the starting point of the acceleration phase,
    if all time samples before have gears > i_DS.

    The highest gear of the time samples before the downshift
    determines the reference gear i_ref for the downshift.
    A downshift where i_DS = i_ref - 1
    is referred to as a one step downshift,
    a downshift where i_DS = i_ref - 2
    is referred to as a two step downshift,
    a downshift where i_DS = i_ref – 3
    is referred to as a three step downshift.

    Visualization of rules implemented:

    initial gear sequence:

    .. image:: ../doc/_static/images/initial_gears_correction_4b.*
    .. image:: ../doc/_static/images/correction_4b_1.*
    .. image:: ../doc/_static/images/correction_4b_2.*
    .. image:: ../doc/_static/images/correction_4b_3.*
    .. image:: ../doc/_static/images/correction_4b_4.*

    final gear sequence:

    .. image:: ../doc/_static/images/correction_4b_5.*

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param Corr4bToBeDoneAfterCorr4a:
        Boolean that check if the correction 4b to be done after correction 4a
    :type Corr4bToBeDoneAfterCorr4a: bool

    :param Corr4bToBeDoneAfterCorr4d:
        Boolean that check if the correction 4b to be done after correction 4d
    :type Corr4bToBeDoneAfterCorr4d: bool

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: numpy.array

    :param PhaseStarts:
        Contains the points that are start point from a phase
    :type PhaseStarts: numpy.array

    :param PhaseEnds:
        Contains the points that are end point from a phase
    :type PhaseEnds: numpy.array

    :param PHASE_ACCELERATION_FROM_STANDSTILL:
        Acceleration phase following a standstill phase
    :type PHASE_ACCELERATION_FROM_STANDSTILL: int

    :param PHASE_ACCELERATION:
        Acceleration phase
    :type PHASE_ACCELERATION: int

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: int

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
        - Corr4bToBeDoneAfterCorr4a (:py:class:`bool`):
            Boolean that check if the correction 4b to be done after correction 4a
        - Corr4bToBeDoneAfterCorr4d (:py:class:`bool`):
            Boolean that check if the correction 4b to be done after correction 4d
    """
    AnyAccelerationStarts = PhaseStarts[
        np.union1d(
            np.where(PhaseValues == PHASE_ACCELERATION),
            np.where(PhaseValues == PHASE_ACCELERATION_FROM_STANDSTILL),
        )
    ]

    AnyAccelerationEnds = PhaseEnds[
        np.union1d(
            np.where(PhaseValues == PHASE_ACCELERATION),
            np.where(PhaseValues == PHASE_ACCELERATION_FROM_STANDSTILL),
        )
    ]

    AnyAccelerations = []
    for i in range(0, len(AnyAccelerationStarts)):
        AnyAccelerations.append(
            np.arange(AnyAccelerationStarts[i], AnyAccelerationEnds[i] + 1)
        )

    for phase in AnyAccelerations:
        gears = InitialGears[phase]
        gears_orig = np.copy(gears)

        gears_greater_one = np.copy(gears)
        gears_greater_one[gears_greater_one <= 1] = np.nan
        gears_max_allowed = np.asarray(_my_cummin(gears_greater_one[::-1])) + 1
        gears_max_allowed = gears_max_allowed[::-1]

        for i in range(0, len(gears)):
            gears[i] = min(gears[i], gears_max_allowed[i])

        use_per_gear = []
        cumulated_use_per_gear = []
        for gear in range(1, NoOfGearsFinal + 1):
            values = np.zeros(len(gears))
            values[np.where(gears == gear)] = 1
            use_per_gear.append(values)
            cumulated_use_per_gear.append(np.cumsum(values))

        use_per_gear = np.asarray(use_per_gear)
        cumulated_use_per_gear = np.asarray(cumulated_use_per_gear)

        size_of_window = 10
        outdated_use_per_gear = np.concatenate(
            (np.zeros((NoOfGearsFinal, 10)), cumulated_use_per_gear), axis=1
        )
        outdated_use_per_gear = outdated_use_per_gear[
            :, : np.shape(outdated_use_per_gear)[1] - size_of_window
        ]

        nbr_of_use_per_gear = cumulated_use_per_gear - outdated_use_per_gear

        gears_without_nan = np.copy(gears)
        gears_without_nan[np.isnan(gears_without_nan)] = 1
        index = (
            _sub2ind(
                np.shape(nbr_of_use_per_gear),
                np.arange(0, len(gears)),
                gears_without_nan,
            ).astype(int)
            - 1
        )
        nbr_of_use_gear = nbr_of_use_per_gear[
            np.unravel_index(index, np.shape(nbr_of_use_per_gear), "F")
        ].astype(int)

        gears_used_twice = np.copy(gears)
        gears_used_twice[gears_used_twice <= 1] = np.nan
        gears_used_twice[np.where(nbr_of_use_gear < 2)] = np.nan

        gears_max_allowed = np.asarray(_my_cummin(gears_used_twice[::-1]))[::-1]

        for i in range(0, len(gears)):
            gears[i] = min(gears[i], gears_max_allowed[i])

        gears_prev = np.copy(gears)
        gears_prev = np.insert(gears_prev, 0, gears[0])[:-1]
        gears_next = np.insert(gears[1:], -1, gears[-1])

        if phase[0] > 0:
            gears_prev[0] = InitialGears[phase[0] - 1]

        gears_greater_one = np.copy(gears)
        gears_greater_one[np.where(gears <= 1)] = np.nan

        final_val_cor4b = Corr4bToBeDoneAfterCorr4a[phase]

        np.put(
            final_val_cor4b,
            np.union1d(
                np.intersect1d(
                    np.where(gears_greater_one < gears_next),
                    np.where(gears_prev > gears_greater_one),
                ),
                np.where(Corr4bToBeDoneAfterCorr4a[phase] == 1),
            ),
            1,
        )

        Corr4bToBeDoneAfterCorr4a[phase] = final_val_cor4b

        gears[np.isnan(gears_orig)] = np.nan
        InitialGears[phase] = gears

        # Annex 2, 5.(b)
        idx_begin = phase[0]
        if idx_begin > 0:
            if InitialGears[idx_begin] - InitialGears[idx_begin - 1] < -1:
                Corr4bToBeDoneAfterCorr4d[idx_begin - 1] = 1

    return InitialGears, Corr4bToBeDoneAfterCorr4a, Corr4bToBeDoneAfterCorr4d


def applyCorrection4a(
    InitialGears,
    Corr4bToBeDoneAfterCorr4a,
    PossibleGears,
    InAcceleration,
    InConstantSpeed,
    InAccelerationAnyDuration,
):
    """
    Sub-Annex 2 in sectoin 4.(a)

    If a one step higher gear (n+1) is required for only 1 second
    and the gears before and after are the same (n),
    or one of them is one step lower (n-1),
    gear (n+1) shall be corrected to gear n.

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param Corr4bToBeDoneAfterCorr4a:
        Boolean that check if the correction 4b to be done after correction 4a
    :type Corr4bToBeDoneAfterCorr4a: bool

    :param PossibleGears:
        The possible gears calculated by each second
    :type PossibleGears: numpy.array

    :param InAcceleration:
        Contains the points that are in acceleration phase as a True
    :type InAcceleration: boolean numpy.array

    :param InConstantSpeed:
        Contains the points that are in constant speed phase as a True
    :type InConstantSpeed: boolean numpy.array

    :param InAccelerationAnyDuration:
         some gear corrections ignore the duration of acceleration phases
         so save acceleration phases with any duration here
    :type InAccelerationAnyDuration: boolean numpy.array

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
    """
    from functools import reduce

    PreviousInitialGears = np.empty(np.shape(InitialGears))
    PreviousInitialGears[:] = np.nan

    for i in range(0, 2 * len(InitialGears)):
        # The gear at the first gear position to be corrected
        # will be finally corrected after at most two iterations.
        # So the maximum number of iteration required to correct all gears
        # will be at most two times the size of the vector of gears.
        if np.array_equal(PreviousInitialGears, InitialGears, equal_nan=True):
            break
        else:
            PreviousInitialGears = np.copy(InitialGears)

        minPossibleGears = np.asarray(
            np.min(np.ma.masked_array(PossibleGears, np.isnan(PossibleGears)), axis=1)
        )

        # -----------------------------------------------------------------------
        # Regulation Annex 2, 4.(a) :
        # -----------------------------------------------------------------------
        # If a one step higher gear (n+1) is required for only 1 second
        # and the gears before and after are the same (n),
        # or one of them is one step lower (n-1),
        # gear (n+1) shall be corrected to gear n.
        # -----------------------------------------------------------------------

        nextInitialGears = np.append(InitialGears[1:], np.nan)

        upshiftsOneOrTwoGearsOneSec = (
            reduce(
                np.union1d,
                (
                    np.intersect1d(
                        np.where(np.diff(InitialGears) == 1),
                        np.where(np.diff(nextInitialGears) == -1),
                    ),
                    np.intersect1d(
                        np.where(np.diff(InitialGears) == 1),
                        np.where(np.diff(nextInitialGears) == -2),
                    ),
                    np.intersect1d(
                        np.where(np.diff(InitialGears) == 2),
                        np.where(np.diff(nextInitialGears) == -1),
                    ),
                ),
            )
            + 1
        )

        for shift in upshiftsOneOrTwoGearsOneSec:
            # reduce upshift only if possible for complete duration
            if (
                InitialGears[shift] - 1 >= minPossibleGears[shift]
                and InitialGears[shift] - 1 >= 1
            ):
                InitialGears[shift] = InitialGears[shift] - 1

        # -----------------------------------------------------------------------
        # 4.(a) continued :
        # -----------------------------------------------------------------------
        # If, during acceleration or constant speed phases
        # or transitions from constant speed to acceleration
        # or acceleration to constant speed phases
        # where these phases only contain upshifts,
        # a gear is used for only one second,
        # the gear in the following second shall be corrected to the gear before,
        # so that a gear is used for at least 2 seconds.
        #
        # This requirement shall not be applied to downshifts during an acceleration phase
        # or if the use of a gear for just one second
        # follows immediately after such a downshift
        # or if the downshift occurs right at the beginning of an acceleration phase.
        # In these cases, the downshifts shall be first corrected
        # according to paragraph 4.(b) of this annex.
        #
        # However, if the gear at the beginning of an acceleration phase
        # is one step lower than the gear in the previous second
        # and the gears in the following (up to five) seconds
        # are the same as the gear in the previous second but followed by a downshift,
        # so that the application of 4.(c) would correct them
        # to the same gear as at the beginning of the acceleration phase,
        # the application of 4.(c) should be performed instead.
        # -----------------------------------------------------------------------

        # if a gear is used for a single second but the next gear is lower
        # then extend this next gear backwards instead of extending the single gear forwards
        # and so avoid that a higher gear with to less power will used after the single second
        # eg RRT vehicle 15, trace seconds 909..918 :
        #   909      918
        #    v        v
        #    4345545555    InitialGears
        #      *>            single extended FORWARD
        #    4344545555    InitialGears
        #        <*          single extended BACKWARD
        #    4344445555    InitialGears
        # But such a backward extension of the next gear is not allowed
        # according Heinz Steven (Workshop 2019-02-05)

        InAccelOrConst = np.zeros(len(InAcceleration))
        np.put(
            InAccelOrConst,
            np.union1d(np.where(InAcceleration == 1), np.where(InConstantSpeed == 1)),
            1,
        )

        singlesInAccelOrConstNextHigher = np.zeros(np.shape(InAccelOrConst))
        np.put(
            singlesInAccelOrConstNextHigher,
            reduce(
                np.intersect1d,
                (
                    np.where(InAccelOrConst == 1),
                    np.where(~np.isnan(InitialGears)),
                    np.union1d(
                        np.intersect1d(
                            np.where(
                                InitialGears == np.insert(InitialGears, 0, np.nan)[:-1]
                            ),
                            np.where(np.diff(np.insert(InAcceleration, 0, 0)) == 1),
                        ),
                        np.where(
                            InitialGears > np.insert(InitialGears, 0, np.nan)[:-1]
                        ),
                    ),
                    np.where(InitialGears < np.insert(InitialGears, -1, np.nan)[1:]),
                    np.where(
                        InitialGears >= np.insert(minPossibleGears, -1, np.nan)[1:]
                    ),
                ),
            ),
            1,
        )

        # exclude singles immediately after singles
        # as later singles will be adjusted to earlier singles
        update = np.intersect1d(
            np.where(singlesInAccelOrConstNextHigher == 1),
            np.where(np.insert(singlesInAccelOrConstNextHigher, 0, 0)[:-1] == 0),
        )
        singlesInAccelOrConstNextHigher = np.zeros(np.shape(InAccelOrConst))
        singlesInAccelOrConstNextHigher[update] = 1

        # exclude singles immediately after downshifts
        update = np.intersect1d(
            np.where(singlesInAccelOrConstNextHigher == 1),
            np.where(
                np.insert(InitialGears, 0, np.nan)[:-1]
                >= np.insert(InitialGears, np.asarray([0, 0]), np.nan)[:-2]
            ),
        )
        singlesInAccelOrConstNextHigher = np.zeros(np.shape(InAccelOrConst))
        singlesInAccelOrConstNextHigher[update] = 1

        if np.where(singlesInAccelOrConstNextHigher != 0)[0].size != 0:
            InitialGears[
                np.where(np.insert(singlesInAccelOrConstNextHigher, 0, 0)[:-1] == 1)
            ] = InitialGears[np.where(singlesInAccelOrConstNextHigher == 1)]

        singlesInAccelOrConstNextLower = np.zeros(np.shape(InAccelOrConst))
        np.put(
            singlesInAccelOrConstNextLower,
            reduce(
                np.intersect1d,
                (
                    np.where(InAccelOrConst == 1),
                    np.where(~np.isnan(InitialGears)),
                    np.union1d(
                        np.intersect1d(
                            np.where(
                                InitialGears == np.insert(InitialGears, 0, np.nan)[:-1]
                            ),
                            np.where(np.diff(np.insert(InAcceleration, 0, 0)) == 1),
                        ),
                        np.where(
                            InitialGears > np.insert(InitialGears, 0, np.nan)[:-1]
                        ),
                    ),
                    np.where(InitialGears > np.insert(InitialGears, -1, np.nan)[1:]),
                    np.where(
                        InitialGears >= np.insert(minPossibleGears, -1, np.nan)[1:]
                    ),
                ),
            ),
            1,
        )

        update = np.intersect1d(
            np.where(singlesInAccelOrConstNextLower == 1),
            np.where(
                np.insert(InitialGears, 0, np.nan)[:-1]
                >= np.insert(InitialGears, np.asarray([0, 0]), np.nan)[:-2]
            ),
        )
        singlesInAccelOrConstNextLower = np.zeros(np.shape(InAccelOrConst))
        singlesInAccelOrConstNextLower[update] = 1

        if np.where(singlesInAccelOrConstNextLower != 0)[0].size != 0:
            update = np.intersect1d(
                np.where(singlesInAccelOrConstNextLower == 1),
                np.where(np.insert(singlesInAccelOrConstNextLower, 0, 0)[:-1] == 0),
            )
            singlesInAccelOrConstNextLower = np.zeros(np.shape(InAccelOrConst))
            singlesInAccelOrConstNextLower[update] = 1

            InitialGears[
                np.where(np.insert(singlesInAccelOrConstNextLower, 0, 0)[:-1] == 1)
            ] = InitialGears[np.where(singlesInAccelOrConstNextLower == 1)]

        # -----------------------------------------------------------------------
        # 4.(a) continued :
        # -----------------------------------------------------------------------
        # Furthermore, if the gear in the first second of an acceleration phase
        # is the same as the gear in the previous second
        # and the gear in the following seconds is one step higher,
        # the gear in the second second of the acceleration phase
        # shall be replaced by the gear used in the first second of the acceleration phase
        # -----------------------------------------------------------------------
        # The Heinz Steven Tool ignores the length of the acceleration phases here.
        # So we use InAccelerationAnyDuration instead of InAcceleration here.
        # HST corrects the gear for eg vehicle_no: 109 time: 1088
        # where acceleration phase lasts only for time 1087..1088.
        # -----------------------------------------------------------------------

        # but this will only be done
        # if the gear in the first second of the acceleration phase
        # may not be increased by correction 4b to done after correction 4a

        prevInAccelAnyDur = np.insert(InAccelerationAnyDuration, 0, 0)[:-1]
        prevPrevNotInAccelAnyDur = np.insert(
            np.invert(prevInAccelAnyDur.astype(int)) + 2, 0, 0
        )[:-1]
        prevGears = np.insert(InitialGears, 0, 0)[:-1]
        prevPrevGears = np.insert(prevGears, 0, 0)[:-1]
        prev_Corr4bToBeDoneAfterCorr4a = np.insert(Corr4bToBeDoneAfterCorr4a, 0, 0)[:-1]

        idx = np.zeros(np.shape(prevInAccelAnyDur))
        np.put(
            idx,
            reduce(
                np.intersect1d,
                (
                    np.where(prevPrevNotInAccelAnyDur == 1),
                    np.where(prevInAccelAnyDur == 1),
                    np.where(InAccelerationAnyDuration == 1),
                    np.where(prevPrevGears >= prevGears),
                    np.where(prevGears + 1 == InitialGears),
                    np.where(InitialGears - 1 >= minPossibleGears),
                    np.where(prev_Corr4bToBeDoneAfterCorr4a == 0),
                ),
            ),
            1,
        )

        InitialGears[np.where(idx == 1)] = InitialGears[np.where(idx == 1)] - 1

        # -----------------------------------------------------------------------
        # 4.(a) continued :
        # -----------------------------------------------------------------------
        # Gears shall not be skipped during acceleration phases.
        # -----------------------------------------------------------------------
        # In an acceleration phase :
        # Decrease a gear, if it differs from the previous non-neutral gear by more than 1 step
        # and the previous gear may not be increased by correction 4b done after correction 4a

        prev_gear = np.insert(InitialGears, 0, np.nan)[:-1]
        upshift = np.diff(np.insert(InitialGears, 0, InitialGears[0]))
        gear_decr_possible = np.where(InitialGears - 1 >= minPossibleGears)
        prev_Corr4bToBeDoneAfterCorr4a = np.insert(Corr4bToBeDoneAfterCorr4a, 0, 0)[:-1]
        twoStepUpshiftInAcceleration = np.zeros(np.shape(prev_gear))
        np.put(
            twoStepUpshiftInAcceleration,
            reduce(
                np.intersect1d,
                (
                    np.where(prev_gear > 0),
                    np.where(InAcceleration == 1),
                    np.where(upshift > 1),
                    gear_decr_possible,
                    np.where(prev_Corr4bToBeDoneAfterCorr4a == 0),
                ),
            ),
            1,
        )

        if np.where(twoStepUpshiftInAcceleration != 0)[0].size != 0:
            InitialGears[np.where(twoStepUpshiftInAcceleration != 0)] = (
                InitialGears[np.where(twoStepUpshiftInAcceleration != 0)] - 1
            )

        # -----------------------------------------------------------------------
        # 4.(a) continued :
        # -----------------------------------------------------------------------
        # However an upshift by two gears is permitted
        # at the transition from an acceleration phase to a constant speed phase
        # if the duration of the constant speed phase exceeds 5 seconds.
        # -----------------------------------------------------------------------

        # At a transition from acceleration phase to a constant speed phase longer than 5 seconds :
        # Decrease a gear, if it differs from the previous non-neutral gear by more than 2 steps.
        # But assume that this rule must also be applied at other transitions.
        # At a transition from acceleration phase to a constant speed phase of up to 5 seconds :
        # Decrease a gear, if it differs from the previous non-neutral gear by more than 1 step..

        prevInAcceleration = np.insert(InAcceleration, 0, 0)[:-1]
        next1stInConstantSpeed = np.append(InConstantSpeed[1:], 0)
        next2ndInConstantSpeed = np.append(next1stInConstantSpeed[1:], 0)
        next3rdInConstantSpeed = np.append(next2ndInConstantSpeed[1:], 0)
        next4thInConstantSpeed = np.append(next3rdInConstantSpeed[1:], 0)
        next5thInConstantSpeed = np.append(next4thInConstantSpeed[1:], 0)
        inConstantSpeedMoreThan5Sec = np.zeros(np.shape(InConstantSpeed))
        np.put(
            inConstantSpeedMoreThan5Sec,
            reduce(
                np.intersect1d,
                (
                    np.where(InConstantSpeed == 1),
                    np.where(next1stInConstantSpeed == 1),
                    np.where(next2ndInConstantSpeed == 1),
                    np.where(next3rdInConstantSpeed == 1),
                    np.where(next4thInConstantSpeed == 1),
                    np.where(next5thInConstantSpeed == 1),
                ),
            ),
            1,
        )

        prev_gear = np.insert(InitialGears, 0, np.nan)[:-1]
        upshift = np.diff(np.insert(InitialGears, 0, InitialGears[0]))
        gear_decr_possible = np.where(InitialGears - 1 >= minPossibleGears)
        tooBigUpshiftAtTransition = np.zeros(np.shape(prev_gear))
        np.put(
            tooBigUpshiftAtTransition,
            reduce(
                np.intersect1d,
                (
                    np.where(prev_gear > 1),
                    np.where(prevInAcceleration == 1),
                    np.where(InConstantSpeed == 1),
                    np.union1d(
                        np.intersect1d(
                            np.where(upshift > 1),
                            np.where(inConstantSpeedMoreThan5Sec == 0),
                        ),
                        np.intersect1d(
                            np.where(upshift > 2),
                            np.where(inConstantSpeedMoreThan5Sec == 1),
                        ),
                    ),
                    gear_decr_possible,
                ),
            ),
            1,
        )

        if np.where(tooBigUpshiftAtTransition != 0)[0].size != 0:
            InitialGears[np.where(tooBigUpshiftAtTransition != 0)] = (
                InitialGears[np.where(tooBigUpshiftAtTransition != 0)] - 1
            )

    return InitialGears


def applyCorrection4c(InitialGears, PossibleGears):
    """
    Sub-Annex 2 in section 4.(c)

    If gear i is used for a time sequence of 1 to 5 seconds
    and the gear prior to this sequence is one step lower
    and the gear after this sequence is one or two steps lower than within this sequence
    or the gear prior to this sequence is two steps lower
    and the gear after this sequence is one step lower than within the sequence,
    the gear for the sequence shall be corrected to
    the maximum of the gears before and after the sequence.
    In all cases i-1 >= i_min shall be fulfilled.

    .. note:: The corrected gear will be i-1 in all cases. 3.5. Determination of possible
        gears to be used. The lowest final possible gear is i_min.

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param PossibleGears:
        The possible gears calculated by each second
    :type PossibleGears: numpy.array

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
    """
    minPossibleGears = np.asarray(
        np.min(np.ma.masked_array(PossibleGears, np.isnan(PossibleGears)), axis=1)
    )
    for b in range(0, len(InitialGears) - 2):
        if (
            InitialGears[b] > 0
            and InitialGears[b + 1] == InitialGears[b] + 1
            and InitialGears[b + 2] == InitialGears[b + 1]
        ):
            d = b + 2
            i = 0
            while d + i <= len(InitialGears) and InitialGears[d + i] > InitialGears[b]:
                i = i + 1
            if i <= 4:
                r = np.arange(b + 1, d + i).astype(int)
                InitialGears[r] = InitialGears[b]
                maxgears = np.asarray(
                    [max(InitialGears[ri], minPossibleGears[ri]) for ri in r]
                )
                InitialGears[r] = maxgears
        elif (
            InitialGears[b] > 0
            and InitialGears[b + 1] == InitialGears[b] + 2
            and InitialGears[b + 2] == InitialGears[b + 1]
        ):
            d = b + 2
            i = 0
            while (
                d + i <= len(InitialGears) - 1
                and InitialGears[d + i] != InitialGears[b] + 1
            ):
                i = i + 1
            if i <= 4:
                r = np.arange(b + 1, d + i).astype(int)
                InitialGears[r] = InitialGears[b] + 1
                maxgears = np.asarray(
                    [max(InitialGears[ri], minPossibleGears[ri]) for ri in r]
                )
                InitialGears[r] = maxgears

    return InitialGears


def applyCorrection4d(
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
):
    """
    Regulation Annex 2, 4.(d) :
    No upshift to a higher gear shall be performed within a deceleration phase.

    .. note:: The newest regulation ECE/TRANS/WP.29/GRPE/2019/2 moved the text part below to paragraph Annex 2, 4.(e).
        But we keep it here as it does not matter whether it will be executed at the end of 4.(d) or at the begin of 4.(e).
    No upshift to a higher gear at the transition
    from an acceleration or constant speed phase
    to a deceleration phase shall be performed
    if one of the gears in the first two seconds
    following the end of the deceleration phase
    is lower than the upshifted gear or is gear 0.
    If there is an upshift during the transition
    and the initial deceleration phase by 2 gears,
    an upshift by 1 gear shall be performed instead.
    In this case, no further modifications shall be perfomed
    in the following gear use checks.

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param PhaseStarts:
        Contains the points that are start point from a phase
    :type PhaseStarts: numpy.array

    :param PhaseEnds:
        Contains the points that are end point from a phase
    :type PhaseEnds: numpy.array

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: numpy.array

    :param PHASE_DECELERATION:
        time period of more than 2 seconds with required vehicle
                speed >= 1km/h and monotonically decreasing
    :type PHASE_DECELERATION: int

    :param PHASE_DECELERATION_TO_STANDSTILL:
        DECELERATION phase preceding a STANDSTILL phase
    :type PHASE_DECELERATION_TO_STANDSTILL: int

    :param corr_4d_applied_before:
        Boolean array that check if correction 4d have been applied before as True
    :type corr_4d_applied_before: boolean numpy.array

    :param TraceTimesCount:
        The length of trace times re-sampled in 1Hz
    :type TraceTimesCount: int

    :param NoOfGearsFinal:
        The number of forward gears after apply the exclusion of first gear
        if is necessary.
    :type NoOfGearsFinal: int

    :param RequiredVehicleSpeeds:
        The vehicle speed required for the whole cycle re-sampled in 1Hz
    :type RequiredVehicleSpeeds: numpy.array

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
    """
    AnyDecelerationStarts = PhaseStarts[
        np.union1d(
            np.where(PhaseValues == PHASE_DECELERATION),
            np.where(PhaseValues == PHASE_DECELERATION_TO_STANDSTILL),
        )
    ]

    AnyDecelerationEnds = PhaseEnds[
        np.union1d(
            np.where(PhaseValues == PHASE_DECELERATION),
            np.where(PhaseValues == PHASE_DECELERATION_TO_STANDSTILL),
        )
    ]

    AnyDecelerations = [
        np.arange(AnyDecelerationStarts[i], AnyDecelerationEnds[i] + 1)
        for i in range(0, len(AnyDecelerationStarts))
    ]

    for phase in AnyDecelerations:
        if np.where(corr_4d_applied_before[phase] != 0)[0].size != 0:
            continue

        # NOTE:
        # the phase before a deceleration phase
        # is guaranteed to be either a acceleration phase or a constant speed phase
        # because it can neither be a stillstand phase nor another deceleration phase

        # correction 4a requires that each gear must be used for at least 2 sec during acceleration
        # this may lead to a delayed usage of higher gears even in the subsequent deceleration phase
        # so an upshift at the transition from acceleration to deceleration phase
        # may occur not immediately at the first second of the transition but some seconds later
        # therefore we will regard any upshift occuring during the first 3 seconds of the deceleration phase
        # as being related to the transition
        # eg RRT vehicle 23, trace seconds 605..616 :
        #   605        616
        #    v          v
        #    AAAAAAAAADDD  A:acceleration D:deceleration
        #    223456677777  g_max
        #    223344556677  gear corr 4a : use each gear for at least 2 sec
        #              ^   delayed usage of higher gear after transition A->D

        g_max_at_transition = np.max(InitialGears[phase[0 : min(3, len(phase))]])

        if (
            phase[0] - 1 >= 1
            and g_max_at_transition > InitialGears[phase[0] - 1] > 0
            and phase[-1] + 2 <= TraceTimesCount
            and (
                g_max_at_transition > InitialGears[phase[-1] + 1]
                or g_max_at_transition > InitialGears[phase[-1] + 2]
                or InitialGears[phase[-1] + 1] == 0
                or InitialGears[phase[-1] + 2] == 0
            )
        ):
            if g_max_at_transition - InitialGears[phase[0] - 1] == 1:
                # single step upshift
                # disable upshifts to gears higher than used before decelaration phase
                mingears = np.asarray(
                    [min(InitialGears[p], InitialGears[phase[0] - 1]) for p in phase]
                )
                InitialGears[phase] = mingears
                corr_4d_applied_before[phase] = 1
            elif g_max_at_transition - InitialGears[phase[0] - 1] in range(
                2, NoOfGearsFinal + 1
            ):
                mingears = np.asarray(
                    [min(InitialGears[p], InitialGears[p - 1] + 1) for p in phase]
                )
                InitialGears[phase] = mingears
                corr_4d_applied_before[phase] = 1

        # no upshift to a higher gear shall be performed within a deceleration phase

        # but Heinz Steven Tool extends a deceleration phase by a following constant speed second
        # when handling gear correction "no upshift during decel"
        # eg for RRT vehicle 20 time 1744
        # 2019-02-26 found that HST extends a deceleration phase also by a following acceleration second
        # eg for RRT vehicle 20 time 670 when using n_min_drive_down = 1500

        phase_ext = phase
        if len(RequiredVehicleSpeeds) >= phase_ext[-1] + 2:
            if RequiredVehicleSpeeds[phase_ext[-1] + 1] >= 1 and (
                np.abs(
                    np.diff(
                        RequiredVehicleSpeeds[[phase_ext[-1] + 1, phase_ext[-1] + 2]]
                    )[0]
                )
                < 0.001
                or np.diff(
                    RequiredVehicleSpeeds[[phase_ext[-1] + 1, phase_ext[-1] + 2]]
                )[0]
                > 0
            ):
                phase_ext = np.append(phase_ext, phase_ext[-1] + 1)

        gears = InitialGears[phase_ext]
        idx_neutral = np.where(gears == 0)
        gears[idx_neutral] = NoOfGearsFinal
        gears = np.asarray(_my_cummin(gears))
        gears[idx_neutral] = 0
        InitialGears[phase_ext] = gears

    return InitialGears


def applyCorrection4e(
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
):
    """
    Regulation Annex 2, 4.(e) :

    .. note:: The newest regulation ECE/TRANS/WP.29/GRPE/2019/2
        moved this gear correction to paragraph
        3.3. Selection of possible gears with respect to engine speed.
        But we keep it here to check also additional usages of gear 2,
        which may result from other gear corrections done before.

    During a deceleration phase, gears with n_gear > 2 shall be used
    as long as the engine speed does not drop below n_min_drive.
    Gear 2 shall be used during a deceleration phase within a short trip
    of the cycle (not at the end of a short trip)as long as the engine
    speed does not drop below (0.9 × n_idle).
    If the engine speed drops below n_idle, the clutch shall be disengaged.
    If the deceleration phase is the last part of a short trip shortly before a stop phase,
    the second gear shall be used as long as the engine speed does not drop below n_idle.

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param PhaseStarts:
        Contains the points that are start point from a phase
    :type PhaseStarts: numpy.array

    :param PhaseEnds:
        Contains the points that are end point from a phase
    :type PhaseEnds: numpy.array

    :param PhaseValues:
        Contains the points of changes phases
    :type PhaseValues: numpy.array

    :param ClutchDisengaged:
        The clutch disengaged by each second.
    :type ClutchDisengaged: boolean numpy.array

    :param InitialRequiredEngineSpeeds:
        The initial engine speeds required for each gear i from 1 to ng and
        for each second j of the cycle trace.
    :type InitialRequiredEngineSpeeds: numpy.array

    :param IdlingEngineSpeed:
        Annex 2 (2c) n_idle. The idling speed.
    :type IdlingEngineSpeed: float

    :param PHASE_DECELERATION:
        time period of more than 2 seconds with required vehicle
                speed >= 1km/h and monotonically decreasing
    :type PHASE_DECELERATION: int

    :param PHASE_DECELERATION_TO_STANDSTILL:
        DECELERATION phase preceding a STANDSTILL phase
    :type PHASE_DECELERATION_TO_STANDSTILL: int

    :param Phases:
        The list of phases that are used during whole cycle
    :type Phases: numpy.array

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
        - ClutchDisengaged (:py:class:`boolean numpy.array`):
            The clutch disengaged by each second AFTER the current correction
    """
    AnyDecelerationStarts = PhaseStarts[
        np.union1d(
            np.where(PhaseValues == PHASE_DECELERATION),
            np.where(PhaseValues == PHASE_DECELERATION_TO_STANDSTILL),
        )
    ]

    AnyDecelerationEnds = PhaseEnds[
        np.union1d(
            np.where(PhaseValues == PHASE_DECELERATION),
            np.where(PhaseValues == PHASE_DECELERATION_TO_STANDSTILL),
        )
    ]

    AnyDecelerations = [
        np.arange(AnyDecelerationStarts[i], AnyDecelerationEnds[i] + 1)
        for i in range(0, len(AnyDecelerationStarts))
    ]

    secondGearsWithLowEngineSpeeds = np.intersect1d(
        np.where(InitialGears == 2),
        np.union1d(
            np.intersect1d(
                np.where(Phases == PHASE_DECELERATION),
                np.where(InitialRequiredEngineSpeeds[:, 1] < 0.9 * IdlingEngineSpeed),
            ),
            np.intersect1d(
                np.where(Phases == PHASE_DECELERATION_TO_STANDSTILL),
                np.where(InitialRequiredEngineSpeeds[:, 1] < IdlingEngineSpeed),
            ),
        ),
    )

    for phase in AnyDecelerations:
        secondGearsWithLowEngineSpeedsInPhase = secondGearsWithLowEngineSpeeds[
            np.intersect1d(
                np.where(secondGearsWithLowEngineSpeeds >= phase[0]),
                np.where(secondGearsWithLowEngineSpeeds <= phase[-1]),
            )
        ]

        ClutchDisengaged[secondGearsWithLowEngineSpeedsInPhase] = 1

        # Additional correction get the same results as the Heinz Steven Tool
        # (eg for RRT vehicle 8, trace seconds 94:95, 440, 525, 1449, 1792:1793).
        # HST seems to do gear correction 4f (eg 33322111 -> 33301111)
        # while Matlab substitutes gear 1 by gear 2 before (eg 33322111 -> 33322222).
        # To compensate this an additional correction will be done here:
        # If gear 2 would only be used for 1 or 2 seconds before becomming disengaged
        # then disengage gear 2 also during this initial seconds.
        if secondGearsWithLowEngineSpeedsInPhase.size != 0:
            t_clutch = np.min(secondGearsWithLowEngineSpeedsInPhase)
            if InitialGears[t_clutch - 1] == 2 and InitialGears[t_clutch - 2] != 2:
                ClutchDisengaged[t_clutch - 1] = 1
            if (
                InitialGears[t_clutch - 1] == 2
                and InitialGears[t_clutch - 2] == 2
                and InitialGears[t_clutch - 3] != 2
            ):
                ClutchDisengaged[t_clutch - 1] = 1
                ClutchDisengaged[t_clutch - 2] = 1

    return InitialGears, ClutchDisengaged


def applyCorrection4f(
    InitialGears,
    ClutchDisengaged,
    SuppressGear0DuringDownshifts,
    PossibleGears,
    InStandStill,
    InDecelerationToStandstill,
    InDeceleration,
):
    """
    Sub-Annex 2 in section 4.(f)

    If during a deceleration phase the duration of a gear sequence between
    two gear sequences of 3 seconds or more is only 1 second, it shall be
    replaced by gear 0 and the clutch shall be disengaged.

    :param InitialGears:
        A cell array of gear numbers AFTER the previous correction
    :type InitialGears: numpy.array

    :param ClutchDisengaged:
        The clutch disengaged by each second.
    :type ClutchDisengaged: boolean numpy.array

    :param SuppressGear0DuringDownshifts:
        Sub-Annex 2 (4f).If a gear is used for only 1 second during a deceleration phase
        it shall be replaced by gear 0 with clutch disengaged, in order to avoid too high
        engine speeds. But if this is not an issue, the manufacturer may allow to use the
        lower gear of the following second directly instead of gear 0 for downshifts of
        up to 3 steps.
    :type SuppressGear0DuringDownshifts: bool

    :param PossibleGears:
        The possible gears calculated by each second
    :type PossibleGears: numpy.array

    :param InStandStill:
        Contains the points that are in standstill phase as a True
    :type InStandStill: boolean numpy.array

    :param InDecelerationToStandstill:
        The array that contains the seconds from deceleration to standstill as a True
    :type InDecelerationToStandstill: boolean numpy.array

    :param InDeceleration:
        Contains the points that are in deceleration phase as a True
    :type InDeceleration: boolean array

    :returns:
        - InitialGears (:py:class:`numpy.array`):
            A cell array of gear numbers AFTER the current correction
        - ClutchDisengaged (:py:class:`boolean numpy.array`):
            The clutch disengaged by each second AFTER the current correction
    """
    from functools import reduce

    gear = np.copy(InitialGears)
    i_max = len(gear)

    gear_max = np.asarray(
        np.max(np.ma.masked_array(PossibleGears, np.isnan(PossibleGears)), axis=1)
    )

    InStandStillExtended = np.copy(InStandStill)

    for i in range(i_max - 2, -1, -1):
        if gear[i] == 0 and InStandStillExtended[i + 1] == 1:
            InStandStillExtended[i] = 1

    for i in range(0, i_max):
        # NOTE:
        # In the gear sequence examples shown by the regulation text
        # eg "j, 0, i, i, i-1, k"
        # the letters "i", "j" and "k" denote gear NUMBERS.
        # But in this for-loop the letter "i" is the time INDEX of the gear
        # which possibly will be replaced by gear 0.
        # So the time indices for the regulation example above are i-1:i+4
        # and the related gear numbers are defined by gear(i-1:i+4).

        replaced = False

        # Heinz Steven Tool 2019-10-08 corrects the gear sequence
        # for vehicle 114 time 434..443
        # from 5 5 5 4 4 3 2 0 0 0
        # to   5 5 5 0 0 0 0 0 0 0
        # while it should have been corrected
        # to   5 5 5 0 2 2 2 0 0 0
        # So we correct such exceptional gear sequences like Heinz Steven.

        if (
            i - 1 >= 0
            and i + 6 <= i_max
            and InDecelerationToStandstill[np.arange(i - 1, i + 6)].all()
            and gear[i - 1] > gear[i] == gear[i + 1]
            and gear[i + 1] > gear[i + 2] > gear[i + 3] > 1
            and gear[i + 4] <= 1
            and gear[i + 5] <= 1
        ):
            gear[i] = 0
            gear[i + 1] = 0
            gear[i + 2] = 0
            gear[i + 3] = 0

        # -------------------------------------------------------------------
        # Regulation Annex 2, 4.(f) :
        # -------------------------------------------------------------------
        # If during a deceleration phase the duration of a gear sequence
        # (a time sequence with constant gear)
        # between two gear sequences of 3 seconds or more
        # is only 1 second,
        # it shall be replaced by gear 0 and "the clutch shall be disengaged.
        # -------------------------------------------------------------------
        # NOTE: Another text later was moved to the begin of regulation 4.(f).
        # -------------------------------------------------------------------
        if (
            i - 3 >= 0
            and i + 4 <= i_max
            and InDeceleration[np.arange(i - 3, i + 4)].all()
            and gear[i - 3] == gear[i - 2]
            and gear[i - 2] == gear[i - 1]
            and gear[i - 1] != gear[i]
            and gear[i] != gear[i + 1]
            and gear[i + 1] == gear[i + 2]
            and gear[i + 2] == gear[i + 3]
        ):
            gear[i] = 0
            ClutchDisengaged[i] = 1
            replaced = True

        # -------------------------------------------------------------------
        # If during a deceleration phase the duration of a gear period
        # (a time sequence with constant gear)
        # between two gear sequences of 3 seconds or more
        # is 2 seconds,
        # it shall be replaced by gear 0 for the 1st second
        # and for the 2nd second with the gear
        # that follows after the 2 second period.
        # The clutch shall be disengaged for the 1st second.
        # This requirement shall only be applied
        # if the gear that follows after the 2 second period is > 0.
        # -------------------------------------------------------------------
        elif (
            i - 3 >= 0
            and i + 5 <= i_max
            and InDeceleration[np.arange(i - 3, i + 5)].all()
            and gear[i - 3] == gear[i - 2]
            and gear[i - 2] == gear[i - 1]
            and gear[i - 1] != gear[i]
            and gear[i] == gear[i + 1]
            and gear[i + 1] != gear[i + 2]
            and gear[i + 2] > 0
            and gear[i + 2] == gear[i + 3]
            and gear[i + 3] == gear[i + 4]
        ):
            gear[i] = 0
            ClutchDisengaged[i] = 1
            gear[i + 1] = gear[i + 2]
            replaced = True

        # -------------------------------------------------------------------
        # If several gear sequences with durations of 1 or 2 seconds
        # follow one another, corrections shall be performed as follows:
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # A gear sequence
        #       i, i, i, i-1, i-1, i-2  or
        #       i, i, i, i-1, i-2, i-2
        # shall be changed to
        #   ==> i, i, i,   0, i-2, i-2
        # with i-2 > 0
        # -------------------------------------------------------------------
        elif (
            i - 3 >= 0
            and i + 3 <= i_max
            and InDeceleration[np.arange(i - 1, i + 1)].all()
            and gear[i - 3] == gear[i - 2]
            and gear[i - 2] == gear[i - 1]
            and gear[i - 1] - 1 == gear[i]
            and (
                gear[i] == gear[i + 1]
                and gear[i + 1] - 1 == gear[i + 2]
                or gear[i] - 1 == gear[i + 1]
                and gear[i + 1] == gear[i + 2]
            )
            and gear[i + 2] > 0
        ):
            gear[i] = 0
            ClutchDisengaged[i] = 1
            gear[i + 1] = gear[i + 2]
            replaced = True

        # -------------------------------------------------------------------
        # A gear sequence such as
        #       i, i, i, i-1, i-2, i-3  or
        #       i, i, i, i-2, i-2, i-3  or
        #       other possible combinations
        # shall be changed to
        #   ==> i, i, i,   0, i-3, i-3
        # with i-3 > 0
        # -------------------------------------------------------------------
        # what are "other possible combinations" ?
        # found that HST for RRT vehicle 32 time 1529:1534 replaces also
        # 6 6 6 5 2 2 -> 6 6 6 0 2 2 2
        # so also following correction must also be done :
        #       i, i, i, i-1, i-4, i-4
        # shall be changed to
        #   ==> i, i, i,   0, i-4, i-4
        # assume following generalization :
        # - the last three gears must not be increasing
        # - the last gear must be three or more steps below first gear (i)
        # -------------------------------------------------------------------
        elif (
            i - 3 >= 0
            and i + 3 <= i_max
            and InDeceleration[np.arange(i - 1, i + 1)].all()
            and gear[i - 3] == gear[i - 2]
            and gear[i - 2] == gear[i - 1]
            and (gear[i - 1] - 1 == gear[i] or gear[i - 1] - 2 == gear[i])
            and gear[i] >= gear[i + 1] >= gear[i + 2]
            and gear[i + 2] + 3 <= gear[i - 1]
            and gear[i + 2] > 0
        ):
            gear[i] = 0
            ClutchDisengaged[i] = 1
            gear[i + 1] = gear[i + 2]
            replaced = True
        # -------------------------------------------------------------------
        # This change shall also be applied to gear sequences
        # where the acceleration is >= 0 for the first 2 seconds
        # and < 0 for the 3rd second
        # or where the acceleration is >= 0 for the last 2 seconds.
        # -------------------------------------------------------------------
        # IMPLEMENTED ABOVE AS: all( InDeceleration( i-1 : i ) )
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # For extreme transmission designs, it is possible
        # that gear sequences with durations of 1 or 2 seconds
        # following one another may last up to 7 seconds.
        # In such cases, the correction above shall be complemented
        # by the following correction requirements in a second step:
        # -------------------------------------------------------------------
        # NOTE: This text is a earlier part of the regulation text.
        # -------------------------------------------------------------------
        if replaced:
            # ---------------------------------------------------------------
            # If gear i-1 is one or two steps below i_max
            # for second 3 of this sequence (one after gear 0).
            # A gear sequence shall be changed :
            #       j, 0, i  , i  , i-1, k
            #   ==> j, 0, i-1, i-1, i-1, k
            #       with j > i+1 and 0 < k <= i-1
            # ---------------------------------------------------------------
            if (
                i - 1 >= 0
                and i + 4 <= i_max
                and gear[i - 1] > gear[i + 1] + 1
                and gear[i] == 0
                and gear[i + 1] == gear[i + 2]
                and gear[i + 2] - 1 == gear[i + 3]
                and gear[i + 3] >= gear[i + 4]
                and gear[i + 3] + 2 >= gear_max[i + 1]
                and gear[i + 4] > 0
            ):
                gear[i + 1] = gear[i + 3]
                gear[i + 2] = gear[i + 3]

            # ---------------------------------------------------------------
            # If gear i-1 is more than two steps below i_max
            # for second 3 of this sequence
            # A gear sequence shall be changed :
            #       j, 0, i  , i  , i-1, k
            #   ==> j, 0, 0  , k  , k  , k
            #       with j > i+1 and 0 < k <= i-1
            # ---------------------------------------------------------------
            elif (
                i - 1 >= 0
                and i + 4 <= i_max
                and gear[i - 1] > gear[i + 1] + 1
                and gear[i] == 0
                and gear[i + 1] == gear[i + 2]
                and gear[i + 2] - 1 == gear[i + 3]
                and gear[i + 3] >= gear[i + 4]
                and gear[i + 3] + 2 < gear_max[i + 1]
                and gear[i + 4] > 0
            ):
                gear[i + 1] = 0
                ClutchDisengaged[i + 1] = 1
                gear[i + 2] = gear[i + 4]
                gear[i + 3] = gear[i + 4]

            # ---------------------------------------------------------------
            # If gear i-2 is one or two steps below i_max
            # for second 3 of this sequence (one after gear 0).
            # A gear sequence shall be changed :
            #       j, 0, i  , i  , i-2, k
            #   ==> j, 0, i-2, i-2, i-2, k
            #       with j > i+1 and 0 < k <= i-2
            # ---------------------------------------------------------------
            elif (
                i - 1 >= 0
                and i + 4 <= i_max
                and gear[i - 1] > gear[i + 1] + 1
                and gear[i] == 0
                and gear[i + 1] == gear[i + 2]
                and gear[i + 2] - 2 == gear[i + 3]
                and gear[i + 3] >= gear[i + 4]
                and gear[i + 3] + 2 >= gear_max[i + 1]
                and gear[i + 4] > 0
            ):
                gear[i + 1] = gear[i + 3]
                gear[i + 2] = gear[i + 3]

            # ---------------------------------------------------------------
            # If gear i-2 is more than two steps below i_max
            # for second 3 of this sequence,
            #       j, 0, i  , i  , i-2, k
            #   ==> j, 0, 0  , k  , k  , k
            #       with j > i+1 and 0 < k <= i-2
            # ---------------------------------------------------------------
            elif (
                i - 1 >= 0
                and i + 4 <= i_max
                and gear[i - 1] > gear[i + 1] + 1
                and gear[i] == 0
                and gear[i + 1] == gear[i + 2]
                and gear[i + 2] - 2 == gear[i + 3]
                and gear[i + 3] >= gear[i + 4]
                and gear[i + 3] + 2 < gear_max[i + 1]
                and gear[i + 4] > 0
            ):
                gear[i + 1] = 0
                ClutchDisengaged[i + 1] = 1
                gear[i + 2] = gear[i + 4]
                gear[i + 3] = gear[i + 4]

        # -------------------------------------------------------------------
        # In all cases specified above in this sub-paragraph,
        # the clutch disengagement (gear 0) for 1 second is used
        # in order to avoid too high engine speeds for this second.
        # If this is not an issue and, if requested by the manufacturer,
        # it is allowed to use the lower gear of the following second
        # directly instead of gear 0 for downshifts of up to 3 steps.
        # The use of this option shall be recorded.
        # -------------------------------------------------------------------
        # NOTE: This text is a later part of the regulation text.
        # -------------------------------------------------------------------
        if (
            replaced
            and SuppressGear0DuringDownshifts
            and i - 1 >= 1
            and i + 1 <= i_max
            and gear[i - 1] - 3 <= gear[i + 1]
        ):
            gear[i] = gear[i + 1]
            ClutchDisengaged[i] = 0

        # -------------------------------------------------------------------
        # If the deceleration phase is the last part of a short trip
        # shortly before a stop phase
        # and the last gear > 0 before the stop phase
        # is used only for a period of up to 2 seconds,
        # gear 0 shall be used instead
        # and the gear lever shall be placed in neutral
        # and the clutch shall be engaged.
        # -------------------------------------------------------------------
        # NOTE: This text later was moved to the begin of regulation 4.(f).
        # -------------------------------------------------------------------
        if (
            i - 1 > 0
            and i + 1 <= i_max
            and InDecelerationToStandstill[np.arange(i - 1, i + 1)].all()
            and InStandStillExtended[i + 1] == 1
            and gear[i] > 0
            and gear[i - 1] != gear[i]
            and gear[i] != gear[i + 1]
        ):
            # decelaration to standstill with last non-zero gear used for 1 second
            gear[i] = 0
            ClutchDisengaged[i] = 0
        elif (
            i - 1 > 0
            and i + 2 <= i_max
            and InDecelerationToStandstill[np.arange(i - 1, i + 2)].all()
            and InStandStillExtended[i + 2] == 1
            and gear[i] > 0
            and gear[i - 1] != gear[i]
            and gear[i] == gear[i + 1]
            and gear[i + 1] != gear[i + 2]
        ):
            # decelaration to standstill with last non-zero gear used for 2 seconds
            gear[i] = 0
            ClutchDisengaged[i] = 0
            gear[i + 1] = 0
            ClutchDisengaged[i + 1] = 0

    # -----------------------------------------------------------------------
    # A downshift to first gear is not permitted
    # during those deceleration phases.
    # If such a downshift would be necessary
    # in the last part of a short trip just before a stop phase,
    # since the engine speed would drop below n_idle in 2nd gear,
    # gear 0 shall be used instead
    # and the gear lever shall be placed in neutral
    # and the clutch shall be engaged.
    #
    # If the first gear is required in a time oeriod of the least 2 seconds
    # imemdiately before of a deceleration to stop,
    # this gear should be used until the first sample of the deceleration phase.
    # For the rest of the deceleration phase,
    # gear 0 shall be used and the gear lever shall be placed in neutral
    # and the clutch shall be engaged.
    # -----------------------------------------------------------------------
    # NOTE: This text later was moved to an earlier position of regulation 4.(f).
    # -----------------------------------------------------------------------
    InDecelerationToStandstillPrev = np.insert(InDecelerationToStandstill, 0, 0)[:-1]
    np.put(
        gear,
        reduce(
            np.intersect1d,
            (
                np.where(InDecelerationToStandstillPrev == 1),
                np.where(InDecelerationToStandstill == 1),
                np.where(gear == 1),
            ),
        ),
        0,
    )

    gearPrev = np.insert(gear, 0, 0)[:-1]
    # additional correction required for eg :
    # - HST vehicle_no: 109 time: 1446
    # - HST vehicle_no: 111 time: 1446
    BeginDecelerationToStandstillGear1Engaged = np.zeros(
        np.shape(InDecelerationToStandstillPrev)
    )
    np.put(
        BeginDecelerationToStandstillGear1Engaged,
        reduce(
            np.intersect1d,
            (
                np.where(InDecelerationToStandstillPrev == 0),
                np.where(gearPrev != 1),
                np.where(InDecelerationToStandstill == 1),
                np.where(gear == 1),
                np.where(ClutchDisengaged == 0),
            ),
        ),
        1,
    )

    gear[np.where(BeginDecelerationToStandstillGear1Engaged == 1)] = 0
    ClutchDisengaged[np.where(BeginDecelerationToStandstillGear1Engaged == 1)] = 1

    # If gear 0 with disengaged clutch was inserted by above gear corrections
    # then futher gear corrections may have lead to an immediately
    # following gear 0 with engaged clutch.
    # In this cases the clutch shall already be engaged for the inserted gear 0.
    InDecelerationToStandstillNext = np.append(InDecelerationToStandstill[1:], 0)
    gearNext = np.append(gear[1:], 0)
    ClutchDisengagedNext = np.append(ClutchDisengaged[1:], 0)
    np.put(
        ClutchDisengaged,
        reduce(
            np.intersect1d,
            (
                np.where(InDecelerationToStandstill == 1),
                np.where(InDecelerationToStandstillNext == 1),
                np.where(gear == 0),
                np.where(gearNext == 0),
                np.where(ClutchDisengaged == 1),
                np.where(ClutchDisengagedNext == 0),
            ),
        ),
        0,
    )
    InitialGears = gear

    return InitialGears, ClutchDisengaged
