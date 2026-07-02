from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController


class SemSLMController(ImConWidgetController):
    """Linked to SemSLMWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._widget.sigSetPresetClicked.connect(self.applyMask)
        self._widget.sigPresetChanged.connect(self.presetChanged)


    def presetChanged(self, bpm_file):
        presetPath = self._widget.getPresetPath()
        mask = str(presetPath) + "/" + bpm_file
        self._widget.updatePixmap(mask)

    def applyMask(self, clicked):
        #manager needs to apply mask to slm
        pass