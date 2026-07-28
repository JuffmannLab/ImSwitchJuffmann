from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger
import PyDAQmx as pd
import numpy as np
import time
import atexit

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
        atexit.register(self.cleanup)

    def cleanup(self):
        #Make sure that control lines and voltage are set to zero when imswitch quits.
        self.__logger.info("Clean up function called")
        data = np.array([False, False], dtype=np.uint8)
        self.digitalOutTask.WriteDigitalLines(1, 1, 10.0, pd.DAQmx_Val_GroupByChannel, data, pd.byref(self.samplesWritten), None)
        self.analogOutTask.WriteAnalogScalarF64(1, 10.0, 0, None)
        self.analogOutTask.StopTask()
        self.digitalOutTask.StopTask()

    def sendVoltage(self, control_voltage):
        #make sure voltage stays within limits of pockelcell
        voltage = max(0, min(control_voltage, 5))
        self.analogOutTask.WriteAnalogScalarF64(1, 10.0, voltage, None)

    def setHV(self, HV):
        self.hv = HV
        data = np.array([self.reset, self.hv], dtype=np.uint8)
        self.digitalOutTask.WriteDigitalLines(1, 1, 10.0, pd.DAQmx_Val_GroupByChannel, data, pd.byref(self.samplesWritten), None)



    def sendReset(self):
        data = np.array([True, self.hv], dtype=np.uint8)
        self.digitalOutTask.WriteDigitalLines(1, 1, 10.0, pd.DAQmx_Val_GroupByChannel, data, pd.byref(self.samplesWritten), None)
        self.__logger.info("Reset triggered! Sleeping for 2s for signal to propagate to PSU...")
        time.sleep(2)
        data[0] = False
        self.digitalOutTask.WriteDigitalLines(1, 1, 10.0, pd.DAQmx_Val_GroupByChannel, data, pd.byref(self.samplesWritten), None)
        self.__logger.info("Reset line put back to 0")



