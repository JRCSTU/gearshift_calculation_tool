# -*- coding: utf-8 -*-
#
# Copyright 2015-2020 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
r"""
Define gearshift command line interface.

.. click:: gearshift.cli:cli
   :prog: gearshift
   :show-nested:
"""

import os
import click
import logging
import click_log
import schedula as sh
from gearshift import dsp as _process

log = logging.getLogger("gearshift.cli")
CO2MPAS_HOME = os.environ.get("CO2MPAS_HOME", ".")

log_config = dict(format="%(asctime)-15s:%(levelname)5.5s:%(name)s:%(message)s")


class _Logger(logging.Logger):
    # noinspection PyMissingOrEmptyDocstring
    def setLevel(self, level):
        super(_Logger, self).setLevel(level)
        logging.basicConfig(level=level, **log_config)
        rlog = logging.getLogger()
        # because `basicConfig()` does not reconfig root-logger when re-invoked.
        rlog.level = level
        logging.captureWarnings(True)


logger = _Logger("cli")
click_log.basic_config(logger)


@click.group("gearshift", context_settings=dict(help_option_names=["-h", "--help"]))
# @click.version_option(__version__) TODO: Create a version file.
@click_log.simple_verbosity_option(logger)
def cli():
    """
    GEARSHIFT command line tool.
    """


@cli.command("run", short_help="Run GEARSHIFT tool.")
@click.argument("input-files", nargs=-1, type=click.Path(exists=True))
@click.option(
    "-O",
    "--output-folder",
    help="Output folder.",
    default="./outputs",
    type=click.Path(file_okay=False, writable=True),
    show_default=True,
)
@click.option(
    "-OT", "--output-template", help="Template output.", type=click.Path(exists=True)
)
@click.option(
    "-PL",
    "--plot-workflow",
    is_flag=True,
    help="Open workflow-plot in browser, after run finished.",
)
def run(input_files, output_folder, plot_workflow, **kwargs):
    """
    Run GEARSHIFT for all files into INPUT_FILES.

    INPUT_FILES: List of input files and/or folders
                 (format: .xlsx).
    """
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    inputs = dict(
        input_files=input_files,
        cmd_flags=kwargs,
        output_folder=output_folder,
        plot_workflow=plot_workflow,
        **{sh.START: kwargs}
    )
    os.makedirs(inputs.get("output_folder") or ".", exist_ok=True)
    return _process(inputs)


if __name__ == "__main__":
    cli()
