#This is a file for testing things out in the ImSwitch environment.

import pylablib

pylablib.par['devices/dlls/pco_sc2']='C:\Program Files\PCO Digital Camera Toolbox\pco.camware'

from pylablib.devices import PCO

cam = PCO.SC2.PCOSC2Camera()

print(cam.get_device_info())
print(cam.get_capabilities())
print(cam.get_internal_buffer_status())
print(cam.get_frame_timings())
print(cam.get_detector_size())
print(cam.get_roi())
print(cam.requires_symmetric_roi())
print(cam.get_roi_limits())
#print(cam.get_acquisition_parameters())
print(cam.get_settings())