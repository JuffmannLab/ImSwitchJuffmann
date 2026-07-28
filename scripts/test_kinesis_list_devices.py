import sys
from pathlib import Path

kinesis_path = Path(r"C:\Program Files\Thorlabs\Kinesis")
sys.path.append(str(kinesis_path))

import clr

clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.DeviceManagerCLI.dll"))

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI

print("Building Kinesis device list...")
DeviceManagerCLI.BuildDeviceList()

devices = list(DeviceManagerCLI.GetDeviceList())

print(f"Number of devices found: {len(devices)}")

for dev in devices:
    print(dev)