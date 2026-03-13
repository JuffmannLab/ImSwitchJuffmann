import imslib as imslib
from pathlib import Path
import numpy as np

from imslib import kHz, Percent, PointClock, ImageTrigger, StopStyle

from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.model.managers.ims_events import EventWaiter, WaitOnEventsThenPrint, EVENT_MESSAGES


class SynthControlManager:
    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self.__logger.info(f"Targeted Scanning for Isomet System with ID: {self._setupInfo.systemID}")
        self.connection = imslib.ConnectionList(max_discover_timeout_ms=100) #milliseconds
        self.player = None
        synth = self.targeted_system_scan(setupInfo.systemID)
        if synth is not None:
            self.ims = synth
            self.ims.Connect()
            self.downloadImages()
        else:
            self.ims = None

    def __del__(self):
        self.ims.Disconnect()

    def downloadImages(self):
        imagePath = Path(__file__).resolve().parents[4]
        imagePath = imagePath / "synthImages"
        for imagefile in imagePath.glob("*.iip"):
            prj = imslib.ImageProject(str(imagefile))
            group = prj.ImageGroupContainer[0]
            for image in group:
                dl = imslib.ImageDownload(self.ims, image)
                waiter = EventWaiter()
                waiter.listen_for(list(EVENT_MESSAGES.keys()))
                for evt in waiter._watched:
                    dl.ImageDownloadEventSubscribe(evt, waiter)
                dl.StartDownload()
                WaitOnEventsThenPrint(waiter, EVENT_MESSAGES, timeout=5.0)

                for evt in waiter._watched:
                    dl.ImageDownloadEventUnsubscribe(evt, waiter)


        self.__logger.debug(f"{imslib.ImageTableViewer(self.ims)}")
        return

    def getImageTable(self):
        if self.ims is None:
            return None
        else:
            table = imslib.ImageTableViewer(self.ims)
            tableSize = table.Entries()
            imageInfo = list()
            for i in range(tableSize):
                infoList = list()
                image = table[i]
                infoList.append(str(image.Handle))
                infoList.append(str(image.NPts))
                infoList.append(str(image.Name))
                imageInfo.append(infoList)
            return imageInfo


    def targeted_system_scan(self, systemID):
        synth = self.connection.Find("CM_USBLITE", systemID)
        if synth is None:
            self.__logger.error(f"Targeted system {systemID} not found.")
        else:
            self.__logger.info(f"Targeted system {systemID} found.")
        return synth

    def startPlayer(self, config):
        if self.ims is None:
            self.__logger.info(f"No iMS system connected.")
            return None
        sp = imslib.SignalPath(self.ims)
        sp.UpdateDDSPowerLevel(Percent(80.0))
        sp.UpdateRFAmplitude(imslib.SignalPath.AmplitudeControl_INDEPENDENT, Percent(80.0))
        sp.SwitchRFAmplitudeControlSource(imslib.SignalPath.AmplitudeControl_INDEPENDENT)

        sp.ClearTone()

        table = imslib.ImageTableViewer(self.ims)
        imageID = config["imageID"]
        playerConfig = imslib.ImagePlayerConfiguration()
        playerConfig.Clock = PointClock.INTERNAL
        playerConfig.Trig = config["trigger"]
        playerConfig.rpts = config["repeatOption"]
        playerConfig.n_rpts = config["repeats"]

        self.player = imslib.ImagePlayer(self.ims, table[imageID], config["clockrate"])
        self.player.Config = playerConfig
        self.player.Play()
    def stopPlayer(self):
        if self.player is None:
            return
        else:
            self.player.Stop()
            self.player = None






