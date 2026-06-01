from qtpy import QtCore, QtWidgets

from imswitch.imcommon.model.shortcut import shortcut
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class ViewWidget(Widget):
    """ View settings (liveview, grid, crosshair). """

    sigGridToggled = QtCore.Signal(bool)  # (enabled)
    sigCrosshairToggled = QtCore.Signal(bool)  # (enabled)
    sigLiveviewToggled = QtCore.Signal(bool)  # (enabled)
    sigSetCrosshair = QtCore.Signal(int)
    sigCountUV = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Graphical elements
        # Grid
        self.gridButton = guitools.BetterPushButton('Grid')
        self.gridButton.setCheckable(True)
        self.gridButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Expanding)

        # Crosshair
        self.crosshairButton = guitools.BetterPushButton('Crosshair')
        self.crosshairButton.setCheckable(True)
        self.crosshairButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                           QtWidgets.QSizePolicy.Expanding)
        # liveview
        self.liveviewButton = guitools.BetterPushButton('LIVEVIEW')
        self.liveviewButton.setStyleSheet("font-size:20px")
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Expanding)
        self.liveviewButton.setEnabled(True)

        #crosshair position
        self.InfoLabel = QtWidgets.QLabel("")
        self.InfoLabel.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        self.val1 = QtWidgets.QSpinBox()
        self.val1.setRange(-1000, 3000)
        self.val1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val1.setValue(0)
        self.val1.setKeyboardTracking(False)

        self.val2 = QtWidgets.QSpinBox()
        self.val2.setRange(-1000, 3000)
        self.val2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val2.setValue(0)
        self.val2.setKeyboardTracking(False)

        # Add elements to GridLayout
        self.viewCtrlLayout = QtWidgets.QGridLayout()
        self.setLayout(self.viewCtrlLayout)
        self.viewCtrlLayout.addWidget(self.liveviewButton, 0, 0, 1, 2)
        self.viewCtrlLayout.addWidget(self.gridButton, 1, 0)
        self.viewCtrlLayout.addWidget(self.crosshairButton, 1, 1)
        self.viewCtrlLayout.addWidget(self.val1, 2, 0, 1, 1)
        self.viewCtrlLayout.addWidget(self.val2, 2, 1, 1, 1)
        self.viewCtrlLayout.addWidget(self.InfoLabel, 2, 2, 1, 2)

        # Connect signals
        self.gridButton.toggled.connect(self.sigGridToggled)
        self.crosshairButton.toggled.connect(self.sigCrosshairToggled)
        self.liveviewButton.toggled.connect(self.sigLiveviewToggled)

    def currentCrosshair(self, pos):
        # Format each value in pos with 2 decimal places; handle scalar fallback
        try:
            formatted = "(" + ", ".join(f"{float(v):.2f}" for v in pos) + ")"
        except TypeError:
            formatted = f"{float(pos):.2f}"
        self.InfoLabel.setText(formatted)

    def getLiveViewActive(self):
        return self.liveviewButton.isChecked()

    def setViewToolsEnabled(self, enabled):
        self.crosshairButton.setEnabled(enabled)
        self.gridButton.setEnabled(enabled)

    def setLiveViewActive(self, active):
        """ Sets whether the LiveView is active. """
        self.liveviewButton.setChecked(active)

    def setLiveViewGridVisible(self, visible):
        """ Sets whether the LiveView grid is visible. """
        self.crosshairButton.setChecked(visible)

    def setLiveViewCrosshairVisible(self, visible):
        """ Sets whether the LiveView crosshair is visible. """
        self.gridButton.setChecked(visible)

    @shortcut('Ctrl+L', "Liveview")
    def toggleLiveviewButton(self):
        self.liveviewButton.toggle()

    @shortcut('Ctrl+G', "Grid")
    def toggleGridButton(self):
        self.gridButton.toggle()

    @shortcut('Ctrl+H', "Crosshair")
    def toggleCrosshairButton(self):
        self.crosshairButton.toggle()