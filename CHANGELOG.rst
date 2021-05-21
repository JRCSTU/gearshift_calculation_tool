..    include:: <isonum.txt>

#######
Changes
#######
.. contents::

GTR version matrix
==================
Given a version number ``MAJOR.MINOR.PATCH``, the ``MAJOR`` part tracks the GTR phase implemented.
The following matrix shows these correspondences:

+---------+---------------------------------------+
| Release |           GTR ver                     |
| train   |                                       |
+=========+=======================================+
|         |  Correct bugs compatibles             |
|  1.1.x  |  with the Amendment 6 of the          |
|         |  COMMISSION REGULATION (EU) 2017/1151 |
+---------+---------------------------------------+
|  1.x.x  |  GTR phase 2 [TDB]                    |
+---------+---------------------------------------+

Changelog
=========

v1.1.3, 20 May 2021: Suppress gear 0 during execution
-----------------------------------------------------

- Correct correction 4f in correction file:
    - In all cases specified above in this sub-paragraph, the clutch disengagement (gear 0) for 1 second is used in order to avoid too high engine speeds for this second. If this is not an issue and,
      if requested by the manufacturer, it is allowed to use the lower gear of the following second directly instead of gear 0 for downshifts of up to 3 steps. The use of this option shall be recorded.
    - This correction should be applied after all corrections described in section 4 of sub-Annex 2.
- Define new input template reducing the mandatory parameters.
- Update copyright.

v1.1.2.1, 11 May 2021: Fix demo files
------------------------------------------------

- Update demo files.

v1.1.2, 11 May 2021: Fix downscaling calculation
------------------------------------------------

- Correct calculate downscaling function inside of scaleTrace according to the regulation.
- Define new input template reducing the mandatory parameters.
- Redefine the color description in the input template.
- Updated documentation.
- style: auto-format python files with |black|_  using |pre-commit|_.

v1.1.1, 22 April 2021: PY3.5 or grater and real work
----------------------------------------------------

- Drop support for Python <3.6, due to f"string:, among others... The supported Pythons `covers 85% of 2020 Python-3 installations <https://www.jetbrains.com/lp/python-developers-survey-2020/>`__
- Updated documentation.
- style: auto-format python files with |black|_  using |pre-commit|_.
- Build & dev-dependencies enhancements.
    - Correct reading of xlsx files according to xlrd deprecation.

v1.0.0, 14 April 2021: 1st version with mandatory definitions
-------------------------------------------------------------

This first release contains the whole mandatory definitions in COMMISSION REGULATION (EU) 2017/1151 according to
Amendment 6 to GTR No. 15 (Worldwide harmonized Light vehicles Test Procedures (WLTP) - Annex XXI sub-Annex 1 and 2.


.. |black| replace:: *black* opinionated formatter
.. _black: https://black.readthedocs.io/
.. |pre-commit| replace:: *pre-commit* hooks framework
.. _pre-commit: https://pre-commit.com/
