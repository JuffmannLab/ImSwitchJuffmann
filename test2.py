import numpy as np
import matplotlib.pyplot as plt

def lissajous_figure (fx, fy, N):
    
    # constants for our setup:
    
    lbd = 465e-9
    theta_deflected = 4.1
    center_frequency = 100e6
    max_frequency = 50e6

    # objective constants:
    
    FOV = 0.44e-3
    Magn = 60
    focal_length = 3e-3

    FOV_Backside = FOV / Magn
    Angular_Range = FOV_Backside / focal_length

    # angle modulation to cover full FOV:
    
    angular_modulation = (Angular_Range / theta_deflected) * 2 * max_frequency

    t_max = N / np.gcd(int(fx), int(fy))
    t = np.linspace(0, t_max, int(t_max*center_frequency))

    X = center_frequency + angular_modulation/2 * np.sin(2*np.pi*fx*t)
    Y = center_frequency + angular_modulation/2 * np.sin(2*np.pi*fy*t)

    plt.figure(figsize=(6,6))

    plt.plot(X, Y)
    plt.show()

