import sys
import time
from pathlib import Path

from imswitch.imcommon.model import initLogger
from .PositionerManager import PositionerManager


class ThorlabsBPC303Manager(PositionerManager):
    """PositionerManager for a Thorlabs benchtop piezo controller.

    Positions are represented as output voltages in volts.
    """

    def __init__(self, positionerInfo, name, **lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        self.__logger.debug("Initializing Thorlabs BPC303 manager")

        props = positionerInfo.managerProperties

        self._serialNumber = str(props.get("serialNumber", "71877822"))
        self._kinesisPath = Path(
            props.get("kinesisPath", r"C:\Program Files\Thorlabs\Kinesis")
        )

        self._minVolt = float(props.get("minVolt", 0.0))
        self._maxVolt = float(props.get("maxVolt", 75.0))
        self._pollingIntervalMs = int(props.get("pollingIntervalMs", 250))

        defaultChannels = {
            axis: index + 1
            for index, axis in enumerate(positionerInfo.axes)
        }
        self._channelMap = props.get("channels", defaultChannels)

        self._device = None
        self._channels = {}

        self._loadKinesis()
        self._connectDevice()

        initialPosition = {}

        for axis in positionerInfo.axes:
            channelNumber = int(self._channelMap[axis])
            channel = self._device.GetChannel(channelNumber)

            if not channel.IsSettingsInitialized():
                self.__logger.info(f"Waiting for settings for axis {axis}")
                channel.WaitForSettingsInitialized(10000)

            channel.StartPolling(self._pollingIntervalMs)
            time.sleep(0.3)

            channel.EnableDevice()
            time.sleep(0.3)

            measuredVoltage = self._toFloat(channel.GetOutputVoltage())
            displayVoltage = self._clamp(measuredVoltage)

            self._channels[axis] = channel
            initialPosition[axis] = displayVoltage

            self.__logger.info(
                f"Axis {axis}: channel {channelNumber}, "
                f"voltage={measuredVoltage:.6f} V"
            )

        super().__init__(
            positionerInfo,
            name,
            initialPosition=initialPosition
        )

    def _loadKinesis(self):
        """Load the required Thorlabs Kinesis .NET assemblies."""
        sys.path.append(str(self._kinesisPath))

        import clr

        clr.AddReference(
            str(self._kinesisPath / "Thorlabs.MotionControl.DeviceManagerCLI.dll")
        )
        clr.AddReference(
            str(self._kinesisPath / "Thorlabs.MotionControl.GenericPiezoCLI.dll")
        )
        clr.AddReference(
            str(self._kinesisPath / "Thorlabs.MotionControl.Benchtop.PiezoCLI.dll")
        )

        from System import Decimal
        from System.Globalization import CultureInfo
        from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
        from Thorlabs.MotionControl.Benchtop.PiezoCLI import BenchtopPiezo

        self._Decimal = Decimal
        self._DeviceManagerCLI = DeviceManagerCLI
        self._BenchtopPiezo = BenchtopPiezo
        self._invariantCulture = CultureInfo.InvariantCulture

    def _connectDevice(self):
        """Connect to the BPC controller."""
        self.__logger.info("Building Kinesis device list")
        self._DeviceManagerCLI.BuildDeviceList()

        self.__logger.info(f"Connecting to BPC device {self._serialNumber}")
        self._device = self._BenchtopPiezo.CreateBenchtopPiezo(self._serialNumber)
        self._device.Connect(self._serialNumber)

    def _toFloat(self, value):
        """Convert .NET decimal/string-like values to Python float."""
        return float(str(value).replace(",", "."))

    def _toDecimal(self, value):
        """Convert Python float to .NET Decimal."""
        return self._Decimal.Parse(f"{value:.6f}", self._invariantCulture)

    def _clamp(self, voltage):
        """Clamp voltage to the configured safe range."""
        return max(self._minVolt, min(float(voltage), self._maxVolt))

    def move(self, dist, axis):
        """Move axis relatively by dist volts."""
        currentPosition = self._position[axis]
        self.setPosition(currentPosition + dist, axis)

    def setPosition(self, position, axis):
        """Set axis output voltage."""
        if axis not in self._channels:
            raise ValueError(f"Unknown piezo axis: {axis}")

        voltage = self._clamp(position)

        self.__logger.info(f"Setting axis {axis} to {voltage:.6f} V")
        self._channels[axis].SetOutputVoltage(self._toDecimal(voltage))

        time.sleep(0.1)

        measuredVoltage = self._toFloat(
            self._channels[axis].GetOutputVoltage()
        )

        self._position[axis] = self._clamp(measuredVoltage)

    def finalize(self):
        """Stop polling and disconnect from the BPC controller."""
        self.__logger.info("Closing Thorlabs BPC303 manager")

        for axis, channel in self._channels.items():
            try:
                channel.StopPolling()
                self.__logger.info(f"Stopped polling axis {axis}")
            except Exception as exc:
                self.__logger.warning(
                    f"Could not stop polling axis {axis}: {exc}"
                )

        if self._device is not None:
            try:
                self._device.Disconnect()
                self.__logger.info("Disconnected BPC device")
            except Exception as exc:
                self.__logger.warning(f"Could not disconnect BPC device: {exc}")