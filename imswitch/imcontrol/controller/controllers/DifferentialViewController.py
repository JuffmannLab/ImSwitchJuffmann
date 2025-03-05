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

    # creating a signal for receiving an image
    sigImageReceived = Signal()

    # initializing class and base class
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # internal state:
        self.active = self._widget.getDifferentialViewChecked()
        self.batch_size = self._widget.getBatchsize()
        self.batch_store = deque(maxlen=self.batch_size)
        self.previou_batches = deque(maxlen=2)

        # connect signals
        self._commChannel.sigUpdateImage.connect(self.update)
        self._widget.sigshowpushed.connect(self.setShowDifferentialView)
        self._widget.sigbatchsize.connect(self.updateBatchSize)

        self.setShowDifferentialView(self.active)
        self.updateBatchSize(self.batch_size)

        # prepare worker thread
        self.imageprocessingthread = Thread()
        self.imageprocessingworker = DifferentialImageWorker()
        self.imageprocessingworker.moveToThread(self.imageprocessingthread)
        self.imageprocessingworker.sigDiffImageComputed.connect(self.displayImage)
        self.sigImageReceived.connect(self.imageprocessingworker.process_image)
        self.imageprocessingthread.start()

    def setShowDifferentialView(self, enabled):

        self.active = enabled
        if not enabled:
            self._widget.setImage(np.zeros((100, 100), dtype=np.uint8))

    def updateBatchSize(self, batch_size):

        self.batch_size = batch_size
        self.batch_store = deque(maxlen=batch_size)

    def displayImage(self, im):
        """Displays the processed differential image in the widget."""
        prevIm = self._widget.getImage()
        shapeChanged = prevIm is None or im.shape != prevIm.shape
        self._widget.setImage(im)

        if shapeChanged or not self.init:
            self.adjustFrame()

    def adjustFrame(self):
        """Adjusts the view frame based on the image size."""
        im = self._widget.getImage()
        if im is None:
            return

        self._widget.updateImageLimits(im.shape[1], im.shape[0])

    def update(self, detectorName, im, init, isCurrentDetector):

        if self.active:
            self.imageprocessingworker.prepareForNewImage(im, self.batch_size)
            self.sigImageReceived.emit()


class DifferentialImageWorker(Worker):
    """Worker for computing the differential image in a separate thread."""
    
    sigDiffImageComputed = Signal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._numQueuedImages = 0
        self._numQueuedImagesMutex = Mutex()
        self.batch_store = deque(maxlen=1)
        self.previous_batches = deque(maxlen=2)

    def process_image(self, img, batch_size):
        """Processes the image and computes the differential image."""
        self._numQueuedImagesMutex.lock()
        if self._numQueuedImages > 1:
            self._numQueuedImagesMutex.unlock()
            return  # Skip frame to avoid backlog
        self._numQueuedImagesMutex.unlock()

        self.batch_store.append(img.astype(np.float32))

        if len(self.batch_store) < batch_size:
            self.sigDiffImageComputed.emit(img)
            return

        batch1 = np.mean(np.stack(self.batch_store), axis=0)
        self.previous_batches.append(batch1)

        if len(self.previous_batches) < 2:
            self.sigDiffImageComputed.emit(img)
            return

        batch2 = self.previous_batches[0]
        batch2 = np.where(batch2 == 0, 1e-6, batch2)  # Avoid division by zero

        diff_img = (batch1 / batch2) - 1
        diff_img = np.clip(diff_img * 255, 0, 255).astype(np.uint8)  # Normalize for display

        self.sigDiffImageComputed.emit(diff_img)

    def prepareForNewImage(self, image, batch_size):
        """Updates the image queue and triggers processing."""
        self._numQueuedImagesMutex.lock()
        self._numQueuedImages += 1
        self._numQueuedImagesMutex.unlock()
        self.process_image(image, batch_size)
        self._numQueuedImagesMutex.lock()
        self._numQueuedImages -= 1
        self._numQueuedImagesMutex.unlock()