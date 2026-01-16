import imslib as ims
from imswitch.imcommon.model import initLogger

class SynthControlManager:
    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self.__logger.info(f"Targeted Scanning for IsoMet System with ID: {self._setupInfo.systemID}")
        self.connection = ims.ConnectionList(max_discover_timeout_ms=100) #milliseconds
        self.synth = self.targeted_system_scan(setupInfo.systemID)


    def targeted_system_scan(self, systemID):
        synth = self.connection.Find("CM_USBLITE", systemID)
        if synth is None:
            self.__logger.error(f"Targeted system {systemID} not found.")
        else:
            self.__logger.info(f"Targeted system {systemID} found.")
        return synth




