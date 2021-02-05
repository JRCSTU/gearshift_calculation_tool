# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Project review for Gearshifting tool
# Navigate it using the "contents tab", at the left:
#
# ![image.png](attachment:fceb2c5c-cd52-44e5-bc9a-13658049a68e.png)
#
# # Conclusions
# (more detailed analysis & sugestions in cells below):
# * Console-UI tool
# * Relies on Excel&trade; as a UI for versatile input/outputs (i.e. supporting multiple cases at once).
# * Relies on `schedula` to execute flexibly with missing data (partial outputs require python programming, not from cmdline).
# * Documented with python's sphinx, with schedula diagrams (TODO: add missing API & dispatchers, publish in own site).
# * Package structure and dependencies need a bit of trimming.
#   * Classifiers claim it runs in python3.5, but docs writes 3.6+ (Q: is it tested in those versions?).
#   * I tested it under python3.8 and it seems ok, no? (TODO: add python3.8 in `setup.py:classifiers` and documentation)* QA needs some work (no TCs & assertions).
#   * Q: why is numpy==1.19.3 pinned?
# * Very good readability of the code.

# ## 0.Installation
# This notebook requires also these packages (install them before launching jupyter):
#
#     pip install 'jupyterlab>=3' radon findimports
#
# Install project (`dev` needed to view files & generate docs):
#
#     install them before launching jupyterpip install -e .[dev]
#
# Test it:

# !gearshift --help

# +
## This notebook needs as CWD the project's root dir.
#
import gearshift
from pathlib import Path
import os

proj_root = Path(gearshift.__file__).parent.parent
if not proj_root.samefile(Path.cwd()):
    print(f"CHDIR: {Path.cwd()} --> {proj_root}")
    os.chdir(proj_root)
# -

# !grep -i python setup.py

# %%writefile radon.cfg
[radon]
# Empty module
exclude = gearshift/core/model/__init__.py


# ## 1.Sources & package structure
#
# * No TestCases or assertions :-(
# * The following packages with a single module `__init__.py` could be transformed to same-named modules: 
#   * `gearshift/cli/__init__.py`
#   * `gearshift/core/model/calculateShiftpointsNdvFullPC/corrections/__init__.py`
# * The `doc/_build` folder should be ignored from git
#   (i guess it was there to facilitate review, correct?) 

# !ls -l

# !find gearshift -name '*.py'

# !grep -R assert gearshift/

# !find doc/_build | head 

# !findimports gearshift -u

# !findimports gearshift | grep -Ev 'logging|\bos\b'  # view important imports only

# !findimports gearshift -d > /tmp/gearshift-imports.dot

# +
from graphviz import Source

Source.from_file("/tmp/gearshift-imports.dot")
# -

# ## 2.Documentation
# * `sphinx_rtd_theme` is not needed (included by default since ~6 years now)
# * `/doc/modules.rst: WARNING: document isn't included in any toctree`
# * Contents in file:///home/ankostis/Work/gearshift_calculation_too.git/doc/_build/html/model.html#project-files-and-folders
# * API & dispatcher models missing (e.g. `save_demo` function & model).
# * "Usage" chapter is missing a rouch-description of the input-file (e.g. a screenshot & a mention of the sub-sheets):
#
#   ![image.png](attachment:2aa255eb-94f3-4098-8f0e-1aea5d3a05db.png)
#
# * I would re-odrer "Model" chapter after "Usage";  and if "Usage" is augmented with Inputs, i would move its current content in a new "Quick-start" sub-section under the "Introduction". 

# !rm -rf doc/_buil/* && python setup.py build_sphinx

# !ls doc/_build/html/

# !ls doc/_build/html/{_modules,_sources}/

# ## 3.Code metrics
# * All well;  the x2 functions that are too-complex, are well-written (structure & readability).
#
# ### 3.1.Maintainability metric
# * All well

# !radon mi -s gearshift/

# ### 3.2.Cyclomatic Complexity metric
# * Not unexpectedly `gearshift/core/model/calculateShiftpointsNdvFullPC/corrections/__init__.py:applyCorrection4f()` is highly complex (110).

# !radon cc -s --show-closures --total-average   gearshift/

# !cat gearshift/___init__.py

# ### 3.3.Halstead complexity metdic
# (included in Maintainability index)
#
# Expectedely, gear-corrections are the most difficult bc they are non-vetorials. but loops.
#
# #### 3.3.1.Explanation:
# * $n_1$ = the number of distinct operators
# * $n_2$ = the number of distinct operands
# * $N_1$ = the total number of operators
# * $N_2$ = the total number of operands
#
# From these numbers, several measures can be calculated:
#
# * Program vocabulary: $n = n_1 + n_2$
# * Program length: $N = N_1 + N_2$
# * Calculated estimated program length: $\hat{N} = n_1 \ln{n_1} + n_2 \ln{n_2}$
# * Volume: $V = N × \ln{n}$
# * Difficulty : $D = \frac{n_1}{2} × \frac{N_2}{n_2}$
# * Effort: $E = D × V$
# * Time required to program: $T=\frac{E}{18} seconds$
# * Number of delivered bugs: $B=\frac{V}{3000}$
#
#

# +
## Print Halstead metrics only for "difficult" functions.
#  (instead of `!radon hal -f gearshift` for all)
#
from radon.complexity import SCORE
from radon.cli import Config
from radon.cli import HCHarvester

def dump_halstead(*paths, min_attr="difficulty", min_val=6):
    cfg = Config(exclude=(),
            ignore=(),
            by_function=True,
            order=SCORE,
            no_assert=False,
            show_closures=False,
            min='A',
            max='F',
                )
    h = HCHarvester(paths, cfg)

    for file, tfile in h.results:
        for fun, tfun in tfile.functions:
            if getattr(tfun, min_attr) > min_val:
                print(f"{file}:{fun}()")
                for key in tfun._fields:
                    print(f"    {key:22}:{getattr(tfun, key)}")

dump_halstead("gearshift/")
# -

# ## 4.Code inspection
# * Complex functions identified have very good readability.

# +
from gearshift.core.model import calculateShiftpointsNdvFullPC

# calculateShiftpointsNdvFullPC.determine_initial_gears??

# +
from gearshift.core.model.calculateShiftpointsNdvFullPC import corrections

# corrections.applyCorrection4f??
# -

# ## 5.Usability
# * Missing `--version` option (important for when when bugfixes have been applied).
# * Typically `-v` should accept no-level (and enable DEBUG) or verbosity-levels also numerically (pass argument through `logging.getLevelName()`)
#   * Actually not any logs produced.
# * `demo` cmd leaves a temporary file `~$gs_input_demo.xlsx`.

!!gearshift --version

# !gearshift -v 0 demo

# !gearshift -v demo

# !gearshift -v DEBUG demo

# ls ./inputs

# !gearshift run --help

# !gearshift -v DEBUG DEBUG run ./inputs

# ### 5.1.Input file
# * Q: in the excel help-text, did you copy the descriptions from Matlab?  If so, some are not valid (i.e. you have to dig into the code to see what if a column works/is deprecated).
