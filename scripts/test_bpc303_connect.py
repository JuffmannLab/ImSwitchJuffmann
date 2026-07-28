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


def test_channel(device, channel_number):
    print(f"\n--- Channel {channel_number} ---")

    channel = device.GetChannel(channel_number)

    if not channel.IsSettingsInitialized():
        print("Waiting for settings...")
        channel.WaitForSettingsInitialized(10000)

    print("Settings initialized:", channel.IsSettingsInitialized())

    channel.StartPolling(250)
    time.sleep(0.5)

    channel.EnableDevice()
    time.sleep(0.5)

    info = channel.GetDeviceInfo()
    print("Description:", info.Description)

    max_voltage = channel.GetMaxOutputVoltage()
    current_voltage = channel.GetOutputVoltage()

    print("Max output voltage:", max_voltage)
    print("Current output voltage:", current_voltage)

    channel.StopPolling()


def main():
    print("Building device list...")
    DeviceManagerCLI.BuildDeviceList()

    print(f"Connecting to BPC device {SERIAL_NO}...")
    device = BenchtopPiezo.CreateBenchtopPiezo(SERIAL_NO)
    device.Connect(SERIAL_NO)

    try:
        for channel_number in [1, 2, 3]:
            test_channel(device, channel_number)

    finally:
        print("\nDisconnecting...")
        device.Disconnect()
        print("Done.")


if __name__ == "__main__":
    main()