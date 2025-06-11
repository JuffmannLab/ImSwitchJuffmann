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

vid_length = 1000
currentframe = {}

currentframe = 0 
camera = Pylablib.Devices.PhotonPhocus.PhotonPhocusBitFlow

while currentframe < vid_length:

    camera.wait_for_frame()
    pf_newframe = camera.read_newest_image()

    if isinstance(pf_newframe, np.ndarray):  
        newFrames = np.expand_dims(pf_newframe, axis=0)  
        
    newFrames = np.array(newFrames)
    n = len(newFrames)

    if n > 0:
        if self.saveFormat == SaveFormat.NPY:
                try:
                    filePath = filenames[detectorName]
                    np.save(filePath, newFrames)
                except ValueError:
                    self.__logger.error("NPY File exceeds available Storage.")
                    if self.saveFormat == SaveFormat.NPY:
                        filePath = self.__recordingManager.getSaveFilePath(
                        f'{self.savename}_{detectorName}.{fileExtension}', False, False)
                        continue
                    
        __recordingManager.sigRecordingFrameNumUpdated.emit(
        min(list(currentFrame.values()))
        )
    time.sleep(0.0001)  # Prevents freezing for some reason

    __recordingManager.sigRecordingFrameNumUpdated.emit(0)


