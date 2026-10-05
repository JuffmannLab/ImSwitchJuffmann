from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger

class DDSManager(SignalInterface):

    def __init__(self, *args, **kwargs):
        self.__logger = initLogger(self)

