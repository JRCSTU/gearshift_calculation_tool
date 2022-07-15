# -*- coding: utf-8 -*-
#
# Copyright 2013-2021 European Commission (JRC);
# Licensed under the EUPL, Version 1.2 or – as soon they will be approved by the European Commission
# – subsequent versions of the EUPL (the "Licence");
#
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
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

proj_ver = "1.4.0"

def read_file(fpath):
    with open(fpath) as fd:
        return fd.read()
    
url = f"https://github.com/JRCSTU/{name}"
download_url = f"{url}/tarball/{proj_ver}"
project_urls = {
    "Documentation": "https://gearshift-calculation-tool.readthedocs.io/en/latest/",
    "Sources": "https://github.com/JRCSTU/gearshift_calculation_tool",
    "Bug Tracker": f"{url}/issues",
    "Live Demo": "https://mybinder.org/v2/gh/JRCSTU/gearshift_calculation_tool/HEAD?urlpath=lab/tree/Notebooks/GUI_binder_interface.ipynb",
}


setup(
    name=name,
    version=proj_ver,
    packages=find_packages(exclude=["test", "test.*", "doc", "doc.*", "appveyor"]),
    license="EUPL 1.1+",
    author="GEARSHIFT-Team",
    author_email="jrc-ldvs-co2@ec.europa.eu",
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
        "Development Status :: 7 - Inactive",
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
    install_requires=["jrshift"],
    entry_points={"console_scripts": [f"{module_name} = {module_name}.cli:cli"]},
    tests_require=["nose>=1.0", "ddt"],
    test_suite="nose.collector",
    package_data={"gearshift": ["demos/*.xlsx", "core/load/speed_phases/*.ftr"]},
    zip_safe=True,
    options={"bdist_wheel": {"universal": True}},
    platforms=["any"],
)
