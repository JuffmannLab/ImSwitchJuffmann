import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import cv2
import platform
if(platform.system() == 'Windows'):
    import msvcrt
    
    if (sys.version_info.major >= 3 and sys.version_info.minor >= 8):
        import os
        #Following lines specifying, the location of DLLs, are required for Python Versions 3.8 and greater
        os.add_dll_directory('C:\BitFlow SDK 6.5\Bin64')
        os.add_dll_directory('C:\Program Files\CameraLink\Serial')

from pylablib.devices import PhotonFocus

cam = PhotonFocus.PhotonFocusBitFlowCamera(bitflow_idx = 0, pfcam_port = 0, )

cam.open()
cam.start_acquisition()
cam.setup_acquisition(mode='sequence', nframes=1000)
cam.BufferManager(cam).reset()
vid = cam.grab(nframes=1000, frame_timeout=1)
print(np.shape(vid))
test = cam.get_frames_status()
print(cam.BufferManager(cam).is_running())
print(test)
cam.stop_acquisition()
cam.close()
