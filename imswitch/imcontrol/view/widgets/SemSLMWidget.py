from qtpy import QtWidgets
from imswitch.imcontrol.view import guitools as guitools


class SemSLMWidget(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)
        slmLayout = QtWidgets.QGridLayout()


        self.applyBtn = guitools.BetterPushButton("Set selected mask")
        self.maskSelect = QtWidgets.QComboBox()

        self.maskPreview = QtWidgets.QLabel()
        self.fSlider = guitools.BetterSlider()

        slmLayout.addWidget(self.maskSelect, 0, 0)
        slmLayout.addWidget(self.applyBtn, 0, 1)
        slmLayout.addWidget(self.maskPreview, 0, 2, 2, 2)
        slmLayout.addWidget(self.fSlider, 1, 0, 1, 2)

        self.layout().addWidget(self.slmLayout)









