#This is a file for testing things out in the ImSwitch environment.

def setROI(hstart, hend, vstart, vend):
    def clamp_and_snap(value, min_val, max_val, step, snap=True):
        value = max(min_val, min(max_val, value))  # Clamp value within range
        return round(value / step) * step if snap else value  # Snap to nearest step if required

    hstart = clamp_and_snap(hstart, 0, 1024 - 128, 128, snap=False)
    vstart = clamp_and_snap(vstart, 0, 1024 - 128, 128, snap=False)
    hend = clamp_and_snap(hend, 128, 1024, 128)
    vend = clamp_and_snap(vend, 128, 1024, 128)

    return hstart, hend, vstart, vend

print(setROI(5, 200, 6, 200))