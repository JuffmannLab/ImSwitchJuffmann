#!/usr/bin/env python3
import sys
import time
import traceback

try:
    import PySpin
except Exception:
    print("ERROR: PySpin is not available. Install FLIR Spinnaker SDK and PySpin.", file=sys.stderr)
    sys.exit(1)


def read_tl_string(tl_map, name, default=""):
    try:
        node = PySpin.CStringPtr(tl_map.GetNode(name))
        if PySpin.IsAvailable(node) and PySpin.IsReadable(node):
            return node.GetValue()
    except Exception:
        pass
    return default


def list_cameras(system):
    cam_list = system.GetCameras()
    cams = []
    try:
        count = cam_list.GetSize()
        for i in range(count):
            cam = cam_list.GetByIndex(i)
            tl = cam.GetTLDeviceNodeMap()
            info = {
                "index": i,
                "vendor": read_tl_string(tl, "DeviceVendorName", ""),
                "model": read_tl_string(tl, "DeviceModelName", ""),
                "serial": read_tl_string(tl, "DeviceSerialNumber", ""),
                "version": read_tl_string(tl, "DeviceVersion", ""),
                "user_id": read_tl_string(tl, "DeviceUserID", ""),
                "access_status": "Unknown",
            }
            try:
                access = PySpin.CEnumerationPtr(tl.GetNode("DeviceAccessStatus"))
                if PySpin.IsAvailable(access) and PySpin.IsReadable(access):
                    val = access.GetIntValue()
                    en = access.GetEntry(val)
                    if PySpin.IsAvailable(en) and PySpin.IsReadable(en):
                        info["access_status"] = en.GetSymbolic()
            except Exception:
                pass
            cams.append(info)
    finally:
        cam_list.Clear()
    return cams


def try_device_reset(cam):
    """
    Attempt DeviceReset via device node map (requires Init), then fallback to TLDevice node map.
    Returns (ok, message).
    """
    # 1) Try device node map (requires Init)
    try:
        dev_map = cam.GetNodeMap()
        cmd = PySpin.CCommandPtr(dev_map.GetNode("DeviceReset"))
        if PySpin.IsAvailable(cmd) and PySpin.IsWritable(cmd):
            cmd.Execute()
            return True, "DeviceReset executed via Device node map"
    except Exception:
        pass

    # 2) Try TLDevice node map (does not require Init)
    try:
        tl_map = cam.GetTLDeviceNodeMap()
        cmd = PySpin.CCommandPtr(tl_map.GetNode("DeviceReset"))
        if PySpin.IsAvailable(cmd) and PySpin.IsWritable(cmd):
            cmd.Execute()
            return True, "DeviceReset executed via TLDevice node map"
    except Exception:
        pass

    return False, "DeviceReset command not available or not writable"


def reset_camera_by_index(system, index):
    cam_list = system.GetCameras()
    try:
        if cam_list.GetSize() <= index:
            return False, f"No camera at index {index}"

        cam = cam_list.GetByIndex(index)
        tl = cam.GetTLDeviceNodeMap()
        model = read_tl_string(tl, "DeviceModelName", "Unknown")
        serial = read_tl_string(tl, "DeviceSerialNumber", "Unknown")

        # Print identity
        access_str = "Unknown"
        try:
            access = PySpin.CEnumerationPtr(tl.GetNode("DeviceAccessStatus"))
            if PySpin.IsAvailable(access) and PySpin.IsReadable(access):
                val = access.GetIntValue()
                en = access.GetEntry(val)
                if PySpin.IsAvailable(en) and PySpin.IsReadable(en):
                    access_str = en.GetSymbolic()
        except Exception:
            pass

        print(f"[{index}] {model} (S/N {serial}) — Access: {access_str}")

        initialized = False
        try:
            # Try to Init (preferred: allows reset from device map)
            try:
                cam.Init()
                initialized = True
            except PySpin.SpinnakerException as e:
                # Could be in use by another process; we’ll try TLDevice reset
                print(f"  Warning: Init failed ({e}); trying TLDevice reset if available")

            # Attempt reset (device map first if initialized; else TLDevice map)
            ok, how = try_device_reset(cam)
            if ok:
                print(f"  Reset command executed ({how}).")
                return True, how
            else:
                print(f"  Reset not available: {how}")
                return False, how

        except Exception as e:
            print(f"  ERROR resetting camera {index}: {e}")
            traceback.print_exc()
            return False, str(e)

        finally:
            # Always DeInit if we initialized the camera
            if initialized:
                try:
                    cam.DeInit()
                except Exception:
                    pass

    finally:
        cam_list.Clear()


def main():
    system = PySpin.System.GetInstance()
    try:
        print("Enumerating FLIR/Spinnaker cameras...")
        cams = list_cameras(system)
        if not cams:
            print("No cameras found.")
            return 0

        print("Found cameras:")
        for c in cams:
            print(f"  [{c['index']}] {c['vendor']} {c['model']}  "
                  f"S/N: {c['serial']}  Access: {c['access_status']}")

        print("\nIssuing reset to all cameras (attempting Init or TL reset as needed)...")
        any_reset = False
        for c in cams:
            ok, msg = reset_camera_by_index(system, c["index"])
            any_reset = any_reset or ok

        if any_reset:
            wait_s = 8
            print(f"\nWaiting {wait_s} seconds for cameras to reboot...")
            time.sleep(wait_s)

            print("Re-enumerating...")
            cams2 = list_cameras(system)
            if not cams2:
                print("No cameras detected after reset. If USB, try replug or longer wait.")
            else:
                print("Cameras after reset:")
                for c in cams2:
                    print(f"  [{c['index']}] {c['vendor']} {c['model']}  "
                          f"S/N: {c['serial']}  Access: {c['access_status']}")
        else:
            print("\nNo cameras were reset (not accessible or reset not supported).")

        return 0
    finally:
        try:
            system.ReleaseInstance()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())