import sys
import time
from pathlib import Path

kinesis_path = Path(r"C:\Program Files\Thorlabs\Kinesis")
sys.path.append(str(kinesis_path))

import clr

clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.DeviceManagerCLI.dll"))
clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.GenericPiezoCLI.dll"))
clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.Benchtop.PiezoCLI.dll"))

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.Benchtop.PiezoCLI import BenchtopPiezo


SERIAL_NO = "71877822"


def to_float(value):
    return float(str(value).replace(",", "."))


def main():
    print("Building device list...")
    DeviceManagerCLI.BuildDeviceList()

    print(f"Connecting to BPC device {SERIAL_NO}...")
    device = BenchtopPiezo.CreateBenchtopPiezo(SERIAL_NO)
    device.Connect(SERIAL_NO)

    channels = []

    try:
        for channel_number in [1, 2, 3]:
            channel = device.GetChannel(channel_number)

            if not channel.IsSettingsInitialized():
                channel.WaitForSettingsInitialized(10000)

            channel.StartPolling(250)
            time.sleep(0.3)
            channel.EnableDevice()
            time.sleep(0.3)

            voltage = to_float(channel.GetOutputVoltage())
            max_voltage = to_float(channel.GetMaxOutputVoltage())

            print(
                f"Channel {channel_number}: "
                f"voltage={voltage:.6f} V, "
                f"max={max_voltage:.6f} V"
            )

            channels.append(channel)

    finally:
        for channel in channels:
            try:
                channel.StopPolling()
            except Exception:
                pass

        print("Disconnecting...")
        device.Disconnect()
        print("Done.")


if __name__ == "__main__":
    main()