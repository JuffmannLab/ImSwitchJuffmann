import serial
from imswitch.imcommon.model import initLogger

"""
Manager for controlling home built Shutter via Arduino Serial commands
"""

class ShutterManager: 
    def __init__(self, setupInfo):
        self._setupInfo = setupInfo
        
        if setupInfo.shutter:
            self.comchannel = setupInfo.shutter.ComChannel
            self.Baudrate = setupInfo.shutter.Baudrate
            self.timeout = setupInfo.shutter.timeout
        else:
            self.comchannel = "COM4"
            self.Baudrate = 9600
            self.timeout = 1

        self.arduino = serial.Serial(port=self.comchannel, baudrate=self.Baudrate, timeout=self.timeout)
        #self.arduino.flush()

    def send_command(self, command):
        self.arduino.write(f"{command}\n".encode())

    def open_shutter(self, delay):
        if delay:
            self.send_command(f"ONETURN {delay}")
        else:
            self.send_command("OPEN")

    def close_shutter(self):
            self.send_command("CLOSE") 

    def loop_shutter(self, delay):
        if delay:
            self.send_command(f"LOOP {delay}") 
        else:
            self.send_command("LOOP")