# Copyright 2015-2019 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
GEARSHIFT setup.
"""
import io
import os
import collections
import os.path as osp
import functools
from setuptools import setup, find_packages

name = "wltp-gearshift"

module_name = "gearshift"

mydir = osp.dirname(__file__)


def read_project_version():
    fglobals = {}
    with io.open(os.path.join(mydir, module_name, "_version.py")) as fd:
        exec(fd.read(), fglobals)  # To read __version__
    return fglobals["__version__"]


def read_file(fpath):
    with open(fpath) as fd:
        return fd.read()


proj_ver = read_project_version()
url = f"https://github.com/JRCSTU/{name}"
download_url = f"{url}/tarball/{proj_ver}"
project_urls = collections.OrderedDict(
    (
        (
            "Documentation",
            "https://gearshift-calculation-tool.readthedocs.io/en/latest/",
        ),
        ("Issue tracker", f"{url}/issues"),
    )
)

extras = {
    "cli": ["click", "click-log"],
    "sync": ["syncing>=1.0.4", "pandas>=0.21.0", "ruamel.yaml>=0.16.5"],
    "plot": [
        "flask",
        "regex",
        "graphviz",
        "Pygments",
        "lxml",
        "beautifulsoup4",
        "jinja2",
        "docutils",
        "plotly",
    ],
    "io": [
        "pandas>=0.21.0",
        "dill",
        "regex",
        "pandalone[xlrd]<0.3",
        "xlrd",
        "asteval",
        "ruamel.yaml>=0.16.5",
    ],
}
# noinspection PyTypeChecker
extras["all"] = list(functools.reduce(set.union, extras.values(), set()))
extras["dev"] = extras["all"] + [
    "wheel",
    "sphinx",
    "gitchangelog",
    "mako",
    "sphinx_rtd_theme",
    "setuptools>=36.0.1",
    "sphinxcontrib-restbuilder",
    "nose",
    "coveralls",
    "ddt",
    "sphinx-click",
]

setup(
    name=name,
    version=proj_ver,
    packages=find_packages(exclude=["test", "test.*", "doc", "doc.*", "appveyor"]),
    license="EUPL 1.1+",
    author="GEARSHIFT-Team",
    author_email="Andres.LAVERDE-MARIN@ext.ec.europa.eu",
    description="Gearshift tool implement the Sub-Annex 1 and Sub-Annex 2 of the"
    "COMMISSION REGULATION (EU) 2017/1151 of 1 June 2017 - Annex XXI",
    long_description=read_file("README.rst"),
    keywords="""GEARSHIFT WLTP vehicle automotive EU JRC IET
    policy monitoring simulator
    """.split(),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Manufacturing",
        "Environment :: Console",
        "License :: OSI Approved :: European Union Public Licence 1.1 " "(EUPL 1.1)",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.5",
    install_requires=[
        "PyYAML",
        "click",
        "pandas",
        "schedula>=1.1.1",
        "click_log",
        "tqdm",
        "regex",
        "numpy!=1.19.3",
        "scipy",
        "pyarrow",
        "XlsxWriter",
        "ruamel.yaml",
        "openpyxl",
        "xlrd",
    ],
    entry_points={"console_scripts": [f"{module_name} = {module_name}.cli:cli"]},
    extras_require=extras,
    tests_require=["nose>=1.0", "ddt"],
    test_suite="nose.collector",
    package_data={"gearshift": ["demos/*.xlsx", "core/load/speed_phases/*.ftr"]},
    zip_safe=True,
    options={"bdist_wheel": {"universal": True}},
    platforms=["any"],
)
