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
# This notebook requires:
# * [`pip install 'jupyterlab>=3' jupytext`](https://jupytext.readthedocs.io/en/latest/)
#   install them before launching jupyter and track `<this notebook>.py` in `review` git-branch.
# * `pip install radon`
# * `pip install -e .[all]`  needed to view files & generate docs
#
# Navigate it using the "contents tab", at the left.
#
# ## 0.Installation
# I had problem installing on Linux due to `pyarrows` custom numpy==1.16 requirement, so did a partial install:
# ```python
# pip install -e . --no-deps
# pip install  click syncing pandas ruamel.yaml tqdm flask beautifulsoup4 jinja2 docutils plotly  pandalone[xlrd] regex dill click-log wheel sphinx sphinxcontrib-restbuilder graphviz Pygments lxml sphinx_rtd_theme ddt sphinx-click gitchangelog mako
# ```

# !cat setup.py

# %%writefile radon.cfg
[radon]
# Empty module
exclude = gearshift/core/model/__init__.py


# ## 1.Packages structure
#
# * No TestCases or assertions :-(
# * The following packages with a single module `__init__.py` could be transformed to same-named modules: 
#   * `gearshift/cli/__init__.py`
#   * `gearshift/core/model/calculateShiftpointsNdvFullPC/corrections/__init__.py`
#

# !ls -l

# !find gearshift -name '*.py'

# !grep -R assert gearshift/

# ## 2.Documentation
# * `sphinx_rtd_theme` is not needed 9included by default since ~6 yeras now)

pip show numpy

# !cat setup.py

pip install pyarrow==1.0.1

pip install -e .[all]

# ## 3.Code review
# See [`radon` library](https://radon.readthedocs.io/en/latest/commandline.html).

# ## 3.1.Maintainability metric
# * All well

# !radon mi -s gearshift/

# ## 3.2.Cyclomatic Complexity metric
# * Not unexpectedly `gearshift/core/model/calculateShiftpointsNdvFullPC/corrections/__init__.py:applyCorrection4f()` is highly complex (110).

# !radon cc -s --show-closures --total-average   gearshift/

# !cat gearshift/___init__.py

# ## 3.3.Halstead complexity metdic
# (included in Maintainability index)
#
# Expectedely, gear-corrections are the most difficult bc they are non-vetorials. but loops.
#
# ### 3.3.1.Explanation:
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

# ## 3.4.Code inspection
# Inspect functions identified above.

# +
from gearshift.core.model import calculateShiftpointsNdvFullPC

# calculateShiftpointsNdvFullPC.determine_initial_gears??
