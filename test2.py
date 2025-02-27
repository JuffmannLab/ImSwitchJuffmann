def setROI(hstart, hend, vstart, vend):
    # Ensure ROI values are within allowed constraints
    def clamp(value, min_val, max_val, step=1):
        value = max(min_val, min(max_val, value))  # Clamp within range
        return round(value / step) * step  # Snap to nearest step

    # Define constraints
    hstart = clamp(hstart, 0, 2560 - 160, step=1)
    hend = clamp(hend, 160, 2560, step=160)+hstart
    vstart = clamp(vstart, 0, 2160 - 16, step=1)
    vend = clamp(vend, 16, 2160, step=16)+vstart
    
    # Ensure hstart < hend and vstart < vend
    if hstart >= hend:
        hstart = hend - 160  # Maintain minimum width constraint
    if vstart >= vend:
        vstart = vend - 16  # Maintain minimum height constraint
    
    # Apply symmetric ROI constraints if required
    requires_h_symmetry, requires_v_symmetry = (True, False)
    if requires_h_symmetry:
        h_center = (hstart + hend) // 2
        h_width = (hend - hstart) //2
        hstart = h_center - h_width
        hend = h_center + h_width
    if requires_v_symmetry:
        v_center = (vstart + vend) // 2
        v_height = (vend - vstart) // 2
        vstart = v_center - v_height
        vend = v_center + v_height
    
    roi_values = (hstart, hend, vstart, vend)
    return roi_values

def clamp(value, min_val, max_val, step=1):
    value = max(min_val, min(max_val, value))  # Clamp within range
    return round(value / step) * step  # Snap to nearest step

print(round((max(16, min(2160, 30)))))

print(setROI(7, 1000, 5, 40))