###############
Gearshift Model
###############

.. module:: gearshift.core.model
   :noindex:

GEARSHIFT model is plotted here below: you can explore the diagram nests by
clicking on them.

.. _model_diagram:

.. raw:: html

    <iframe frameBorder="0" src="https://andreslaverdemarin.github.io/gearshift.github.io/" height="500px" width="100%" allowfullscreen></iframe>

The execution of gearshift model for a single vehicle is a procedure in three
sequential stages:

  - **Calculate Speed Trace**: Scales down specified sections of a given trace by
    the given downscale factor (see next section `Model structure`_).
  - **Calculate shift points, Ndv and full power curve**: Determines shift-points over trace-time
    (see next section `Model structure`_).

Model structure
===============
The model is structured in two dispachers:

    - scaleTrace: This dispacher is responsible to apply the all requirements defined
      in the Sub-Annex 1 in the Commission Regulation (EU) 2017/1151 of 1 June 2017.

    - calculateShiftpointsNdvFullPC:  This dispacher is responsible to apply the all
      requirements defined in the Sub-Annex 2 in the Commission Regulation (EU)
      2017/1151 of 1 June 2017.
