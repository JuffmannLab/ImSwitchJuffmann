import imslib as imslib
from pathlib import Path

from imswitch.imcommon.model import initLogger

class SynthControlManager:
    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self.__logger.info(f"Targeted Scanning for Isomet System with ID: {self._setupInfo.systemID}")
        self.connection = imslib.ConnectionList(max_discover_timeout_ms=100) #milliseconds
        synth = self.targeted_system_scan(setupInfo.systemID)
        if synth is not None:
            self.ims = synth
            self.ims.Connect()
            self.downloadImages()


    def downloadImages(self):
        imagePath = Path(__file__).resolve().parents[4]
        imagePath = imagePath / "synthImages"
        for imagefile in imagePath.glob("*.iip"):
            name = imagefile.name
            prj = imslib.ImageProject(str(imagefile))
            group = prj.ImageGroupContainer[0]
            for image in group:
                dl = imslib.ImageDownload(self.ims, image)
                dl.StartDownload()

        print(imslib.ImageTableViewer(self.ims))
        return

    def targeted_system_scan(self, systemID):
        synth = self.connection.Find("CM_USBLITE", systemID)
        if synth is None:
            self.__logger.error(f"Targeted system {systemID} not found.")
        else:
            self.__logger.info(f"Targeted system {systemID} found.")
        return synth




