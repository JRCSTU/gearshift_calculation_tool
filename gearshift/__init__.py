# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Defines the file processing chain model `dsp`.

.. currentmodule:: gearshift

.. autosummary::
    :nosignatures:
    :toctree: _build/gearshift/

    ~core
    ~cli
    ~utils
    ~defaults
"""
import os
import tqdm
import logging
import webbrowser
import os.path as osp
import schedula as sh

log = logging.getLogger(__name__)
dsp = sh.BlueDispatcher(name="process")


def init_conf(inputs):
    """
    Initialize GEARSHIFT model configurations.

    :param inputs:
         Initialization inputs.
    :type inputs: dict | schedula.Token

    :return:
        Initialization inputs.
    :rtype: dict | schedula.Token
    """
    return inputs


def _yield_files(*paths, cache=None, ext=("xlsx")):
    import glob

    cache = set() if cache is None else cache
    for path in paths:
        path = osp.abspath(path)
        if path in cache or osp.basename(path).startswith("~"):
            continue
        cache.add(path)
        if osp.isdir(path):
            yield from _yield_files(
                *filter(osp.isfile, glob.glob(osp.join(path, "*"))), cache=cache
            )
        elif osp.isfile(path) and path.lower().endswith(ext):
            yield path
        else:
            log.info('Skipping file "%s".' % path)


dsp.add_data(sh.START, filters=[init_conf, lambda x: sh.NONE])


@sh.add_function(dsp, outputs=["core_model"])
def register_core():
    """
    Register core model.

    :return:
        CO2MPAS core model.
    :rtype: schedula.Dispatcher
    """
    from .core import dsp

    return dsp.register(memo={})


class _ProgressBar(tqdm.tqdm):
    def __init__(self, *args, _format_meter=None, **kwargs):
        if _format_meter:
            self._format_meter = _format_meter
        super(_ProgressBar, self).__init__(*args, **kwargs)

    @staticmethod
    def _format_meter(bar, data):
        return "%s: Processing %s\n" % (bar, data)

    # noinspection PyMissingOrEmptyDocstring
    def format_meter(self, n, *args, **kwargs):
        bar = super(_ProgressBar, self).format_meter(n, *args, **kwargs)
        try:
            return self._format_meter(bar, self.iterable[n])
        except IndexError:
            return bar


@sh.add_function(dsp, outputs=["core_solutions"])
def run_core(core_model, input_files, output_folder, cmd_flags, **kwargs):
    """
    Run core model.

    :param core_model:
        CO2MPAS core model.
    :type core_model: schedula.Dispatcher

    :param cmd_flags:
        Command line options.
    :type cmd_flags: dict

    :param timestamp:
        Run timestamp.
    :type timestamp: str

    :param input_files:
        List of input files and/or folders.
    :type input_files: iterable

    :return:
        Core model solutions.
    :rtype: dict[str, schedula.Solution]
    """
    solutions, it = {}, list(_yield_files(*input_files))
    if it:
        for fp in _ProgressBar(it):
            solutions[fp] = core_model(
                dict(input_file_name=fp, cmd_flags=cmd_flags), **kwargs
            )
    return solutions
