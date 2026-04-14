# print_hwp_angle_com3_highlevel.py
import libximc.highlevel as ximc

DEVICE_URI = r"xi-com:\\.\COM3"

def microstep_divisor(mode):
    # Map enum to numeric microstep divisor
    return {
        ximc.MicrostepMode.MICROSTEP_MODE_FULL: 1,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_2: 2,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_4: 4,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_8: 8,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_16: 16,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_32: 32,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_64: 64,
        ximc.MicrostepMode.MICROSTEP_MODE_FRAC_128: 128,
        getattr(ximc.MicrostepMode, "MICROSTEP_MODE_FRAC_256", None): 256,  # some firmwares
    }.get(mode, 1)

def counts_to_degrees(counts, usteps_per_rev):
    # θ = (c mod U) * 360 / U
    return (counts % usteps_per_rev) * 360.0 / usteps_per_rev

def main():
    axis = ximc.Axis(DEVICE_URI)
    axis.open_device()
    try:
        # Read microstep mode (engine settings); assume 200 full steps/rev and no gearbox
        es = axis.get_engine_settings()
        micro_div = microstep_divisor(getattr(es, "MicrostepMode", ximc.MicrostepMode.MICROSTEP_MODE_FULL))
        full_steps = 200
        ratio_num, ratio_den = 1, 1
        usteps_per_rev = int(full_steps * micro_div * ratio_num / ratio_den) or 1

        # Read raw position counts
        pos = axis.get_position()
        # Handle possible field name variations
        for field in ("CurPosition", "Position", "position"):
            if hasattr(pos, field):
                counts = int(getattr(pos, field))
                break
        else:
            raise RuntimeError("Position field not found in axis.get_position() result")

        angle_deg = counts_to_degrees(counts, usteps_per_rev)
        print(f"Microsteps per revolution: {usteps_per_rev}")
        print(f"Raw counts: {counts}")
        print(f"Current angle (COM3): {angle_deg:.2f}°")
    finally:
        axis.close_device()

if __name__ == "__main__":
    main()