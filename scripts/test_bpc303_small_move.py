import sys
import time
from pathlib import Path

kinesis_path = Path(r"C:\Program Files\Thorlabs\Kinesis")
sys.path.append(str(kinesis_path))

import clr

clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.DeviceManagerCLI.dll"))
clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.GenericPiezoCLI.dll"))
clr.AddReference(str(kinesis_path / "Thorlabs.MotionControl.Benchtop.PiezoCLI.dll"))

from System import Decimal
from System.Globalization import CultureInfo
from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.Benchtop.PiezoCLI import BenchtopPiezo


SERIAL_NO = "71877822"
CHANNEL_NUMBER = 1
STEP_V = 0.1

INV = CultureInfo.InvariantCulture


def to_float(value):
    """Convert .NET Decimal/string-like values to Python float."""
    return float(str(value).replace(",", "."))


def to_decimal(value):
    """Convert Python float to .NET Decimal using invariant culture."""
    return Decimal.Parse(f"{value:.6f}", INV)


def main():
    print("Building device list...")
    DeviceManagerCLI.BuildDeviceList()

    print(f"Connecting to BPC device {SERIAL_NO}...")
    device = BenchtopPiezo.CreateBenchtopPiezo(SERIAL_NO)
    device.Connect(SERIAL_NO)

    channel = None

    try:
        channel = device.GetChannel(CHANNEL_NUMBER)

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

        max_voltage = to_float(channel.GetMaxOutputVoltage())
        initial_voltage = to_float(channel.GetOutputVoltage())

        # Clamp the initial value to the physical/software range.
        safe_initial_voltage = max(0.0, min(initial_voltage, max_voltage))
        target_voltage = max(0.0, min(safe_initial_voltage + STEP_V, max_voltage))

        print(f"Max voltage: {max_voltage:.6f} V")
        print(f"Initial voltage: {initial_voltage:.6f} V")
        print(f"Safe initial voltage: {safe_initial_voltage:.6f} V")
        print(f"Target voltage: {target_voltage:.6f} V")

        input(
            "\nAbout to move channel "
            f"{CHANNEL_NUMBER} by +{STEP_V:.3f} V. "
            "Press Enter to continue, or Ctrl+C to cancel."
        )

        channel.SetOutputVoltage(to_decimal(target_voltage))
        time.sleep(1.0)

        after_move = to_float(channel.GetOutputVoltage())
        print(f"Voltage after move: {after_move:.6f} V")

        input(
            "\nAbout to return channel "
            f"{CHANNEL_NUMBER} to {safe_initial_voltage:.6f} V. "
            "Press Enter to continue, or Ctrl+C to leave it there."
        )

        channel.SetOutputVoltage(to_decimal(safe_initial_voltage))
        time.sleep(1.0)

        after_return = to_float(channel.GetOutputVoltage())
        print(f"Voltage after return: {after_return:.6f} V")

    finally:
        if channel is not None:
            try:
                channel.StopPolling()
            except Exception:
                pass

        print("\nDisconnecting...")
        device.Disconnect()
        print("Done.")


if __name__ == "__main__":
    main()