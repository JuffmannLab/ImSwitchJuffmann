import napari
import numpy as np
import matplotlib.pyplot as plt

def add_handler(detector, liveView=False):

    test_main_handler = {}
    handler = np.random.randint(2**31)

    if detector not in test_main_handler:
        test_main_handler[detector] = set()

    test_main_handler[detector].add(handler)

    return test_main_handler

my_dict = {'Cam1': 564784558
           }
print(my_dict)
def reading_dict(dict):
    handles = [value if isinstance(value, set) else {value} for value in dict.values()]
    values = [next(iter(value_set)) for value_set in handles]
    for value in values:
        print(value)

reading_dict(my_dict)
