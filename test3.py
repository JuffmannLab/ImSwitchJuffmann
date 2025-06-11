import numpy as np
frames = []

a1 = np.array([[1, 1],
               [1, 1]])

a2 = np.array([[2, 2],
               [2, 2]])

rec_frames = 10
n = 0
currentframe = 0

while currentframe < rec_frames:
    if isinstance(a1, np.ndarray):
        frames.append(a1)
        vid = np.array(frames)
        n = len(vid)
        
    if n > 0:
        it = currentframe
        currentframe += 1
        print(currentframe)

print(vid.shape)
