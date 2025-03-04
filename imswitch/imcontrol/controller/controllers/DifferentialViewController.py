import numpy as np
import cv2
from collections import deque

from imswitch.imcommon.framework import Signal, Thread, Worker, Mutex
from imswitch.imcontrol.view import guitools
from ..basecontrollers import LiveUpdatedController

"""
Controller for showing differential imaging. 
Right now, the Widget is in hybrid mode with the napari viewer, showing the diff img in the viewer.
For more controllability I think it would be benefitial to show it in the widget itself. 
Also enables us to add colorbars etc. 
"""


class DifferentialViewController(LiveUpdatedController):
    "Linked to DifferentialViewWidget"

    sigImageReceived = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updateRate = 10

        self._commChannel.sigUpdateImage.connect(self.update)

        self._widget.sigShowToggled.connect(self.setShowDifferentialView)

        self.setShowDifferentialView(self._widget.getDifferentialViewChecked())

    def setShowDifferentialView(self, enabled):

        self.active = enabled

    def update(self, detectorName, im, init, isCurrentDetector):
        def process_image(img, batch_size=1, previous_batches=[deque(maxlen=2)]):

            if previous_batches[0].maxlen != 2:
                previous_batches[0] = deque(maxlen=2)  # Store only the last two averaged batches

            if "batch_store" not in process_image.__dict__:
                process_image.batch_store = deque(maxlen=batch_size)

            process_image.batch_store.append(img.astype(np.float32))

            if len(process_image.batch_store) < batch_size:
                return img

            batch1 = np.mean(np.stack(process_image.batch_store), axis=0)
            previous_batches[0].append(batch1)

            if len(previous_batches[0]) < 2:
                return img

            batch2 = previous_batches[0][0]
            batch2 = np.where(batch2 == 0, 1e-6, batch2)
            diff_img = (batch1 / batch2) - 1
            diff_img = np.clip(diff_img * 255, 0, 255).astype(np.uint8) #puts the pixel values in range of 0 to 255 to make sure it is compatible with the napari viewer

            return diff_img  
        
        if self.active:
            diff_img = process_image(im)
            self._widget.setImage(diff_img)