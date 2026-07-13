"""
Long-duration timelapse recorder for a Daheng (GXIPY) camera.
Captures one frame every N seconds for a specified duration and
writes them incrementally to an HDF5 file on the Desktop.
"""

import os
import time
import datetime
import traceback

import numpy as np
import h5py

from imswitch.imcontrol.model.interfaces.gxipyCamera import CameraGXIPY  # adjust import path to match your project

# CAM Settings
CAMERA_NO       = 1          
EXPOSURE_TIME   = 10000      
GAIN            = 0
BINNING         = 1

# ROI
ROI_HPOS = 0
ROI_VPOS = 0
ROI_HSIZE = 1024
ROI_VSIZE = 1024

INTERVAL_S      = 10.0        # seconds between frames
DURATION_HOURS  = 6.0         # total recording duration

OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop")


def main():
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTPUT_DIR, f"timelapse_{timestamp_str}.h5")

    print(f"Opening camera {CAMERA_NO} ...")
    cam = CameraGXIPY(
        cameraNo=CAMERA_NO,
        exposure_time=EXPOSURE_TIME,
        gain=GAIN,
        frame_rate=-1,       
        binning=BINNING,
    )

    cam.set_continuous_acquisition()

    hpos, vpos, hsize, vsize = cam.setROI(
        hpos=ROI_HPOS, vpos=ROI_VPOS, hsize=ROI_HSIZE, vsize=ROI_VSIZE
    )
    print(f"ROI set to hpos={hpos}, vpos={vpos}, hsize={hsize}, vsize={vsize}")

    n_frames_planned = int((DURATION_HOURS * 3600) / INTERVAL_S)
    print(f"Planning to record ~{n_frames_planned} frames over {DURATION_HOURS} h "
          f"(1 frame / {INTERVAL_S:.0f} s) -> {out_path}")

    h5_file = None
    img_dataset = None
    ts_dataset = None
    frame_count = 0

    try:
        cam.start_live()
        # let acquisition stabilize / discard first frame's warm-up latency
        time.sleep(0.5)

        start_time = time.time()
        next_capture_time = start_time
        end_time = start_time + DURATION_HOURS * 3600

        while time.time() < end_time:
            frame = cam.getLast(timeout=5)

            if frame is None:
                print("Warning: frame grab timed out, skipping this slot.")
            else:
                frame = np.asarray(frame)

                if h5_file is None:
                    # create file & resizable datasets now that we know the frame shape
                    h5_file = h5py.File(out_path, "w")
                    img_dataset = h5_file.create_dataset(
                        "frames",
                        shape=(0,) + frame.shape,
                        maxshape=(None,) + frame.shape,
                        dtype=frame.dtype,
                        chunks=(1,) + frame.shape,
                        compression="gzip",
                        compression_opts=4,
                    )
                    ts_dataset = h5_file.create_dataset(
                        "timestamps",
                        shape=(0,),
                        maxshape=(None,),
                        dtype="float64",
                    )
                    # metadata
                    h5_file.attrs["interval_s"] = INTERVAL_S
                    h5_file.attrs["roi_hpos"] = hpos
                    h5_file.attrs["roi_vpos"] = vpos
                    h5_file.attrs["roi_hsize"] = hsize
                    h5_file.attrs["roi_vsize"] = vsize
                    h5_file.attrs["exposure_time_us"] = EXPOSURE_TIME
                    h5_file.attrs["gain"] = GAIN
                    h5_file.attrs["start_time_unix"] = start_time

                idx = img_dataset.shape[0]
                img_dataset.resize(idx + 1, axis=0)
                ts_dataset.resize(idx + 1, axis=0)
                img_dataset[idx] = frame
                ts_dataset[idx] = time.time()
                h5_file.flush()

                frame_count += 1
                if frame_count % 10 == 0:
                    elapsed_h = (time.time() - start_time) / 3600
                    print(f"[{elapsed_h:.2f} h] captured frame {frame_count}")

            # sleep until the next scheduled capture time (accounts for grab duration)
            next_capture_time += INTERVAL_S
            sleep_time = next_capture_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # we're behind schedule; just continue immediately
                next_capture_time = time.time()

    except KeyboardInterrupt:
        print("Recording interrupted by user.")
    except Exception:
        print("Unexpected error during recording:")
        traceback.print_exc()
    finally:
        print("Stopping camera and closing file...")
        try:
            cam.stop_live()
        except Exception:
            pass
        try:
            cam.close()
        except Exception:
            pass
        if h5_file is not None:
            h5_file.close()
        print(f"Recording finished. {frame_count} frames saved to {out_path}")


if __name__ == "__main__":
    main()