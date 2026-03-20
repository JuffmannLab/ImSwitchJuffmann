from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import PyDAQmx as pd
import numpy as np

reset_line = "Dev1/port1/line1" #pin 4
HV_line = "Dev1/port1/line2" #pin 5

class PockelCellManager(SignalInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        self.reset_line = reset_line
        self.HV_line = HV_line
        self.digital_lines = ",".join([self.reset_line, self.HV_line])

        self.hv = False
        self.reset = False

        self.samplesWritten = pd.int32()
        self.analogOutTask = pd.Task()
        self.digitalOutTask = pd.Task()
        # DAQmx Configure Code
        try:
            self.analogOutTask.CreateAOVoltageChan(b"Dev1/ao1", "", -10.0, 10.0, pd.DAQmx_Val_Volts, None)
            self.digitalOutTask.CreateDOChan(self.digital_lines, "", pd.DAQmx_Val_ChanForAllLines)
            # DAQmx Start Code
            self.analogOutTask.StartTask()
            self.digitalOutTask.StartTask()
        except Exception as e:
            self.__logger.error(f"Exception caught when connecting to NIDAQ device: {e}")

    def __del__(self):
        #Make sure that control lines and voltage are set to zero when imswitch quits.
        data = np.array([False, False])
        self.digitalOutTask.WriteDigitalLines(1, 1, 10.0, pd.DAQmx_Val_GroupByChannel, data, pd.byref(self.samplesWritten), None)
        self.analogOutTask.WriteAnalogScalarF64(1, 10.0, 0, None)
        self.analogOutTask.StopTask()
        self.digitalOutTask.StopTask()

    def sendVoltage(self, control_voltage):
        pass

    def setHV(self, HV_ON):
        pass

    def sendReset(self):
        pass


