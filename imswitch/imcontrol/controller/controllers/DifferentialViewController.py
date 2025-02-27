import numpy as np

from imswitch.imcommon.framework import Signal, Thread, Worker, Mutex
from imswitch.imcontrol.view import guitools
from ..basecontrollers import LiveUpdatedController

class DifferentilViewController(LiveUpdatedController):
    "Linked to DifferentialViewWidget"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)