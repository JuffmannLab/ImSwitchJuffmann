import pyvcam
from pyvcam import pvc
from pyvcam.camera import Camera

pvc.init_pvcam()      # Initialize PVCAM

available_cameras = pyvcam.camera.Camera.get_available_camera_names()
for i, camera in enumerate(available_cameras):
    c = Camera.select_camera(camera)
    c.open()
    print(c.name)
    print(c.serial_no)
    print(c.chip_name)
    c.close()
cam = next(Camera.detect_camera()) # Use generator to find first camera
cam2 = next(Camera.detect_camera())
print(available_cameras)                    # Open the camera