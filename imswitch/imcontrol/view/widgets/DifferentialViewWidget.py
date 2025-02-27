import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from imswitch.imcommon.view.guitools import pyqtgraphtools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget

class DifferentialViewWidget(Widget):
    """ Displays the differential image for iScat measurements. """

    