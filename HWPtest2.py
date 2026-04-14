# add_10deg_com3_highlevel.py
import time
import libximc.highlevel as ximc

DEVICE_URI = r"xi-com:\\.\COM3"
DELTA_DEG = 10.0
TIMEOUT_S = 60

def microstep_divisor(mode):
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
    }.get(mode, 1)

def get_upr(axis):
    # Assume 200 full steps per rev and no gearbox
    es = axis.get_engine_settings()
    micro_div = microstep_divisor(getattr(es, "MicrostepMode", ximc.MicrostepMode.MICROSTEP_MODE_FULL))
    full_steps = 200
    return int(full_steps * micro_div) or 1

def get_counts(axis):
    pos = axis.get_position()
    for field in ("CurPosition", "Position", "position"):
        if hasattr(pos, field):
            return int(getattr(pos, field))
    raise RuntimeError("Position field not found in axis.get_position() result")

def counts_to_deg(counts, upr):
    return (counts % upr) * 360.0 / upr

def wait_for_stop(axis, timeout_s=TIMEOUT_S):
    t0 = time.time()
    while True:
        st = axis.get_status()
        # Try common fields that indicate motion state
        moving = False
        # libximc often uses 'MvCmdSts' bitmask; 0 means stopped
        if hasattr(st, "MvCmdSts"):
            moving = getattr(st, "MvCmdSts") != 0
        elif hasattr(st, "IsMoving"):
            moving = bool(getattr(st, "IsMoving"))
        # If we cannot detect, assume a short delay is enough
        if not moving:
            return
        if time.time() - t0 > timeout_s:
            raise TimeoutError("Movement timeout")
        time.sleep(0.05)

def main():
    axis = ximc.Axis(DEVICE_URI)
    axis.open_device()
    try:
        # Compute microsteps/rev and set calibration so 1 microstep = 360/U degrees
        U = get_upr(axis)
        es = axis.get_engine_settings()
        micro_mode = getattr(es, "MicrostepMode", ximc.MicrostepMode.MICROSTEP_MODE_FULL)
        axis.set_calb(360.0 / U, micro_mode)

        # Read current angle in degrees (calibrated)
        pos_deg = axis.get_position_calb()
        cur_deg = None
        for field in ("Position", "CurPosition", "position"):
            if hasattr(pos_deg, field):
                cur_deg = float(getattr(pos_deg, field))
                break
        if cur_deg is None:
            # Fallback: compute from raw counts if calibrated read is unavailable
            counts = get_counts(axis)
            cur_deg = counts_to_deg(counts, U)

        target_deg = (cur_deg + DELTA_DEG) % 360.0

        print(f"Current angle: {cur_deg:.2f}°  ->  Target angle: {target_deg:.2f}°")

        # Use absolute move in degrees via calibration
        axis.command_move_calb(target_deg)

        # Wait for motion to finish
        wait_for_stop(axis)

        # Read back and report
        pos_deg = axis.get_position_calb()
        new_deg = None
        for field in ("Position", "CurPosition", "position"):
            if hasattr(pos_deg, field):
                new_deg = float(getattr(pos_deg, field))
                break
        if new_deg is None:
            new_deg = counts_to_deg(get_counts(axis), U)

        print(f"New angle: {new_deg:.2f}°")

    finally:
        axis.close_device()

if __name__ == "__main__":
    main()