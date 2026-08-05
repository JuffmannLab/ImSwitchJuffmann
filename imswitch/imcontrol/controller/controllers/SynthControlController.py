from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class SynthControlController(ImConWidgetController):
    """Linked to SynthControlWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self.populateWidget()

        #connect signal widgets
        self._widget.sigRepeatOptionChanged.connect(self.setRepeatOption)
        self._widget.sigStartPlayerClicked.connect(self.startPlayer)
        self._widget.sigStopPlayerClicked.connect(self.stopPlayer)
        self._widget.sigDownloadClicked.connect(self.download)


    def setRepeatOption(self, index):
        #self._master.synthControlManager.setRepeatOption(index)
        if index == 1:
            self._widget.enableRepeatSpinBox(True)
        else:
            self._widget.enableRepeatSpinBox(False)

    def startPlayer(self, checked):
        config = self._widget.getConfig()
        self._master.synthControlManager.startPlayer(config)

    def stopPlayer(self, checked):
        if self._widget.isPlaying():
            self._master.synthControlManager.stopPlayer()
            self._widget.stopClicked()

    def download(self):
        self._master.synthControlManager.downloadImages()
        imgTable = self._master.synthControlManager.getImageTable()
        if imgTable is not None:
            self._widget.setImageTable(imgTable)

    def populateWidget(self):

        clockrate, trigger, repeatID = self._master.synthControlManager.getConfig()
        self._widget.setConfig(clockrate, trigger, repeatID)

        imgTable = self._master.synthControlManager.getImageTable()
        if imgTable is not None:
            self._widget.setImageTable(imgTable)






