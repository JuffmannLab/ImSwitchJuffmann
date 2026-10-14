import imslib as imslib
from pathlib import Path
import atexit

from imslib import Percent, PointClock, StopStyle

from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.model.managers.ims_events import EventWaiter, WaitOnEventsThenPrint, EVENT_MESSAGES


class SynthControlManager:
    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self.__logger.info(f"Targeted Scanning for Isomet System with ID: {self._setupInfo.systemID}")
        self.connection = imslib.ConnectionList(max_discover_timeout_ms=100) #milliseconds
        self.player = None
        self.clockrate = setupInfo.clockrate
        self.trigger = setupInfo.trigger
        self.repeatID = setupInfo.repeatID

        synth = self.targeted_system_scan(setupInfo.systemID)
        if synth is not None:
            self.ims = synth
            self.ims.Connect()
            #self.downloadImages()
        else:
            self.ims = None

        atexit.register(self.cleanup)

    def cleanup(self):
        """ Stops the output and disconnects, like the iMS examples on exit: without ClearTone
        the DDS keeps outputting the last frequency (e.g. the zero position of the image).
        Called when ImSwitch closes and again at exit; does nothing the second time. """
        if self.ims is None:
            return
        try:
            if self.player is not None:
                self.player.Stop(StopStyle.IMMEDIATELY)
                self.player = None
            imslib.SignalPath(self.ims).ClearTone()
        except Exception as e:
            self.__logger.error(f'Could not stop the synthesizer output: {e}')
        try:
            self.ims.Disconnect()
        except Exception as e:
            self.__logger.error(f'Could not disconnect the synthesizer: {e}')
        self.ims = None
        self.__logger.info('Synthesizer output stopped and disconnected')

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
        """ Stops the image playback and switches the output off (ClearTone, like the iMS
        examples): otherwise the synthesizer stays at the last frequency and the beam stays on
        one spot (which saturated the iScat camera). """
        if self.player is None:
            return
        self.player.Stop(StopStyle.IMMEDIATELY)
        self.player = None
        try:
            imslib.SignalPath(self.ims).ClearTone()
        except Exception as e:
            self.__logger.error(f'Could not switch the synthesizer output off: {e}')

    def getConfig(self):
        return self.clockrate, self.trigger, self.repeatID

    def test(self):
        print("test")






