import pyvcam
from pyvcam import pvc
from pyvcam.camera import Camera

pvc.init_pvcam()      # Initialize PVCAM

available_cameras = pyvcam.camera.Camera.get_available_camera_names()
for i, camera in enumerate(available_cameras):
    c = Camera.select_camera(camera)
    c.open()
    print(c.scan_line_time)
    c.close()
cam = next(Camera.detect_camera()) # Use generator to find first camera
cam2 = next(Camera.detect_camera())
print(available_cameras)                    # Open the camera