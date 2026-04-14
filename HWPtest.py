# print_hwp_angle_com3.py
from ctypes import byref, c_int
from pyximc import *

def open_on_com3(lib):
    enum = lib.enumerate_devices(EnumerateFlags.ENUMERATE_PROBE, b"")
    n = lib.get_device_count(enum)
    if n == 0:
        raise RuntimeError("No XiLab/ximc devices found.")
    target = b"COM3"
    for i in range(n):
        name = lib.get_device_name(enum, i)  # e.g., b"xi-com:\\\\.\\COM3"
        if b"xi-com" in name and target in name:
            return lib.open_device(name), name.decode(errors="ignore")
    raise RuntimeError("No device on COM3 found. Is it listed in XiLab?")

def get_usteps_per_rev(lib, dev):
    ms = motor_settings_t()
    lib.get_motor_settings(dev, byref(ms))
    full_steps = getattr(ms, "FullStepsPerRev", 200)
    microstep_mode = getattr(ms, "MicrostepMode", MicrostepMode.MICROSTEP_MODE_FULL)
    micro_div = {
        MicrostepMode.MICROSTEP_MODE_FULL: 1,
        MicrostepMode.MICROSTEP_MODE_FRAC_2: 2,
        MicrostepMode.MICROSTEP_MODE_FRAC_4: 4,
        MicrostepMode.MICROSTEP_MODE_FRAC_8: 8,
        MicrostepMode.MICROSTEP_MODE_FRAC_16: 16,
        MicrostepMode.MICROSTEP_MODE_FRAC_32: 32,
        MicrostepMode.MICROSTEP_MODE_FRAC_64: 64,
        MicrostepMode.MICROSTEP_MODE_FRAC_128: 128,
    }.get(microstep_mode, 1)

    gs = gears_settings_t()
    lib.get_gears_settings(dev, byref(gs))
    ratio_num = getattr(gs, "GearRatio_Mul", 1)
    ratio_den = getattr(gs, "GearRatio_Div", 1) or 1

    usteps_per_motor_rev = full_steps * micro_div
    usteps_per_output_rev = int(usteps_per_motor_rev * ratio_num / ratio_den)
    return max(1, usteps_per_output_rev)

def read_position_counts(lib, dev):
    pos = get_position_t()
    res = lib.get_position(dev, byref(pos))
    if res != Result.Ok:
        raise RuntimeError("get_position failed")
    if hasattr(pos, "CurPosition"):
        return int(pos.CurPosition)
    if hasattr(pos, "Position"):
        return int(pos.Position)
    raise RuntimeError("Position field not found")

def counts_to_degrees(counts, usteps_per_rev):
    # Convert counts modulo one full revolution to degrees
    return (counts % usteps_per_rev) * 360.0 / usteps_per_rev

if __name__ == "__main__":
    lib = ximc  # provided by pyximc
    dev = None
    try:
        dev, name = open_on_com3(lib)
        print(f"Opened device: {name}")

        upr = get_usteps_per_rev(lib, dev)
        counts = read_position_counts(lib, dev)
        angle_deg = counts_to_degrees(counts, upr)

        print(f"Raw counts: {counts}")
        print(f"Microsteps per revolution: {upr}")
        print(f"Current angle (COM3): {angle_deg:.2f} degrees")
    finally:
        if dev is not None:
            try:
                lib.close_device(byref(c_int(dev)))
            except Exception:
                pass