def round_to_step_with_bound(value, step=8, upper_bound=None):
    """
    Rounds a number to the nearest multiple of step (default 8),
    while ensuring it doesn't exceed an optional upper bound.
    
    Args:
        value (int/float): Input value to round
        step (int): Step size to round to (default 8)
        upper_bound (int/float): Maximum allowed value (optional)
    
    Returns:
        int: Rounded value that is a multiple of step and ≤ upper_bound (if specified)
    """
    # Round to nearest step
    rounded = round(value / step) * step
    
    # If we have an upper bound and exceeded it, round down instead
    if upper_bound is not None and rounded > upper_bound:
        rounded = (upper_bound // step) * step
    
    return int(rounded) if isinstance(value, int) else rounded

test = round_to_step_with_bound(50, upper_bound=42)
print(test)
