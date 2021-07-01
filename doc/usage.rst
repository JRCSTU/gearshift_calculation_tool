Input File
----------

.. image:: ../doc/_static/images/about_sheet.*

The input file of the gearshift tool is an excel file, structured in different sheets.

  - **Case sheet:** The case sheet contains a list of cases that the tool will run.
  - **Vehicle sheet:** The vehicle sheet contains a list of vehicles along with their characteristics.
  - **Engine sheet:** The engine sheet contains the vehicle’s full load curves.
  - **Gearbox Ratios sheet:** The gearbox ratios sheet contains the gearbox transmission ratios.

.. include:: ../README.rst
    :start-after: .. _start-usage:
    :end-before: .. _end-usage:

.. include:: ../README.rst
    :start-after: .. _start-library:
    :end-before: .. _end-library:

.. include:: ../README.rst
    :start-after: .. _start-dispacher1:
    :end-before: .. _end-dispacher1:

* Plot workflow of the core model from the dispatcher

  .. code-block:: python

      core.plot()

  This will automatically open an internet browser and show the work flow of the core model as below.
  You can click all the rectangular boxes to see in detail sub models like load, model, write and plot.

    .. figure:: ./_static/images/core_plot.PNG
        :align: center
        :alt: alternate text
        :figclass: align-center

  The load module

    .. figure:: ./_static/images/load_core_plot.PNG
        :align: center
        :alt: alternate text
        :figclass: align-center

.. include:: ../README.rst
    :start-after: .. _start-dispacher2:
    :end-before: .. _end-dispacher2:

.. include:: ../README.rst
    :start-after: .. _start-sub:
    :end-before: .. _end-sub:
