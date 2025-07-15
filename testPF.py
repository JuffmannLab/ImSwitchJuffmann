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
for i in range(10):
    frame = cam.snap()
    plt.imshow(frame)
    plt.show()
cam.stop_acquisition()
cam.close()

