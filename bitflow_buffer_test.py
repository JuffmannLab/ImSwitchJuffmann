""" Tests how large the ring buffer of the PhotonFocus camera / BitFlow frame grabber can be,
and whether a continuous acquisition loses frames at the current settings.

Run on the lab PC with ImSwitch closed (the camera can only be opened once):
    venv\\Scripts\\python.exe bitflow_buffer_test.py
Options:
    --port N       PhotonFocus port (cameraListIndex in the setup file), default 0
    --seconds S    duration of the continuous acquisition test, default 5
    --buffer N     buffer size for the continuous test, default: largest size that worked
"""
import argparse
import os
import time

for dllDir in (r'C:\BitFlow SDK 6.5\Bin64', r'C:\Program Files\CameraLink\Serial'):
    if os.path.isdir(dllDir):
        os.add_dll_directory(dllDir)

from pylablib.devices import PhotonFocus

BUFFER_SIZES = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=0)
parser.add_argument('--seconds', type=float, default=5)
parser.add_argument('--buffer', type=int, default=None)
args = parser.parse_args()

cam = PhotonFocus.PhotonFocusBitFlowCamera(0, None, args.port)
try:
    cam.open()
    framePeriod = cam.get_frame_period()
    print(f'Camera:        {cam.get_attribute_value("CameraName")}')
    print(f'ROI:           {cam.get_roi()}  (data dimensions {cam.get_data_dimensions()})')
    print(f'Exposure:      {cam.get_exposure() * 1e3:.3f} ms')
    print(f'Frame period:  {framePeriod * 1e3:.3f} ms  ({1 / framePeriod:.0f} fps)')
    print()

    # 1) Largest buffer the frame grabber accepts
    largestOk = None
    for nframes in BUFFER_SIZES:
        try:
            cam.setup_acquisition(mode='sequence', nframes=nframes)
            cam.start_acquisition()
            cam.wait_for_frame(timeout=5)
            frame = cam.read_newest_image()
            status = cam.get_frames_status()
            cam.stop_acquisition()
            mb = status.buffer_size * frame.nbytes / 1e6
            print(f'buffer {nframes:6d} frames: OK   (allocated {status.buffer_size} frames, '
                  f'frame_merge {cam._frame_merge}, {mb:8.1f} MB, '
                  f'{status.buffer_size * framePeriod * 1e3:8.0f} ms at current frame rate)')
            largestOk = nframes
        except Exception as e:
            print(f'buffer {nframes:6d} frames: FAIL ({type(e).__name__}: {e})')
            break

    # 2) Continuous acquisition: read all frames like the recording does, count lost frames
    nframes = args.buffer or largestOk
    if nframes:
        print(f'\nContinuous acquisition for {args.seconds:.0f} s with buffer {nframes} frames...')
        cam.setup_acquisition(mode='sequence', nframes=nframes)
        cam.start_acquisition()
        read = 0
        start = time.time()
        while time.time() - start < args.seconds:
            read += len(cam.read_multiple_images())
            time.sleep(0.01)
        read += len(cam.read_multiple_images())
        status = cam.get_frames_status()
        cam.stop_acquisition()
        elapsed = time.time() - start
        print(f'acquired {status.acquired} frames ({status.acquired / elapsed:.0f} fps), read {read}, '
              f'lost (overwritten) {status.skipped}')
finally:
    cam.close()
