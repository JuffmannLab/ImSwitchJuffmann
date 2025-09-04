import time
import numpy as np
from lantz import Q_

from imswitch.imcommon.framework import Thread, Timer
from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

logger = initLogger(__name__)


class MCLFocusController(ImConWidgetController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_x = None
        self.stage_y = None
        self.stage_z = None
        self._connect_signals()

    def _connect_signals(self):
        self._widget.sigMoveStage.connect(self.move_stage)

    def activate(self):
        logger.info("MCLFocusController activated")
        self.stage_x = self.hardware_manager.get_hardware('x')
        self.stage_y = self.hardware_manager.get_hardware('y')
        self.stage_z = self.hardware_manager.get_hardware('z')

        if self.stage_x and self.stage_y and self.stage_z:
            logger.info("MCL individual axis stages connected.")
        else:
            logger.warning("One or more MCL stage axes not connected. Using mock movement.")

    def move_stage(self, x, y, z):
        logger.info(f"Moving stage to X: {x} µm, Y: {y} µm, Z: {z} µm")

        if self.stage_x:
            try:
                self.stage_x.move(x)
            except Exception as e:
                logger.error(f"Error moving stage X: {e}")
        else:
            logger.warning("[Mock] X axis not connected. Skipping.")

        if self.stage_y:
            try:
                self.stage_y.move(y)
            except Exception as e:
                logger.error(f"Error moving stage Y: {e}")
        else:
            logger.warning("[Mock] Y axis not connected. Skipping.")

        if self.stage_z:
            try:
                self.stage_z.move(z)
            except Exception as e:
                logger.error(f"Error moving stage Z: {e}")
        else:
            logger.warning("[Mock] Z axis not connected. Skipping.")

    def apply_pid_correction(self, x, y, z):
        logger.info(f"Applying PID correction: X={x:.2f} µm, Y={y:.2f} µm, Z={z:.2f} µm")
        self.move_stage(x, y, z)

    def deactivate(self):
        logger.info("MCLFocusController deactivated")