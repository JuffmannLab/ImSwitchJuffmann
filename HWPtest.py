# print_hwp_angle_com3_libximc.py
import libximc.highlevel as ximc

DEVICE_URI = r"xi-com:\\.\COM3"  # Windows COM3

def microstep_divisor(microstep_mode):
    # Map enum to numeric divisor
    return {
        ximc.MicrostepMode.MICROSTEP_MODE_FULL: 1,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_2: 2,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_4: 4,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_8: 8,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_16: 16,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_32: 32,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_64: 64,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_128: 128,
        getattr(ximc.MicrostepMode, "MICROSTEP_MODE_FRAC_256", None): 256,
    }.get(microstep_mode, 1)

def get_usteps_per_rev(axis):
    # Full steps/rev from motor settings
    ms = axis.get_motor_settings()
    full_steps = getattr(ms, "FullStepsPerRev", 200)

    # Microstep mode (engine settings preferred; fall back to motor settings if needed)
    try:
        es = axis.get_engine_settings()
        micro_mode = getattr(es, "MicrostepMode", ximc.MicrostepMode.MICROSTEP_MODE_FULL)
    except Exception:
        micro_mode = getattr(ms, "MicrostepMode", ximc.MicrostepMode.MICROSTEP_MODE_FULL)
    micro_div = microstep_divisor(micro_mode)

    # Gear ratio (if any)
    gs = axis.get_gears_settings()
    ratio_num = getattr(gs, "GearRatio_Mul", 1)
    ratio_den = getattr(gs, "GearRatio_Div", 1) or 1

    usteps_per_motor_rev = full_steps * micro_div
    usteps_per_output_rev = int(usteps_per_motor_rev * ratio_num / ratio_den)
    return max(1, usteps_per_output_rev)

def read_counts(axis):
    pos = axis.get_position()
    # Try common field names across firmware/SDK versions
    for field in ("CurPosition", "Position", "position"):
        if hasattr(pos, field):
            return int(getattr(pos, field))
    # Fallback: some wrappers store it under 'Pos'
    for field in ("Pos", "cur_position"):
        if hasattr(pos, field):
            return int(getattr(pos, field))
    raise RuntimeError("Could not find position field in get_position() result")

def counts_to_degrees(counts, usteps_per_rev):
    # θ = (c mod U) * 360 / U
    return (counts % usteps_per_rev) * 360.0 / usteps_per_rev

def main():
    axis = ximc.Axis(DEVICE_URI)
    axis.open_device()
    try:
        upr = get_usteps_per_rev(axis)
        counts = read_counts(axis)
        angle_deg = counts_to_degrees(counts, upr)

        print(f"Device: {DEVICE_URI}")
        print(f"Raw counts: {counts}")
        print(f"Microsteps per revolution: {upr}")
        print(f"Current angle: {angle_deg:.2f}°")
    finally:
        axis.close_device()

if __name__ == "__main__":
    main()