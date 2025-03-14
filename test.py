import napari
import numpy as np
import matplotlib.pyplot as plt

# Create the viewer
viewer = napari.Viewer()

# Dummy image
image = np.random.random((512, 512))

# Add image to Napari
layer = viewer.add_image(image, colormap='magma', contrast_limits=[0, 1])

# Create a Matplotlib figure for the colorbar
fig, ax = plt.subplots(figsize=(1, 5))
im = ax.imshow(image, cmap='magma', vmin=np.min(image), vmax=np.max(image))
cb = plt.colorbar(im, ax=ax)
ax.axis('off')

# Convert the colorbar figure to an image
fig.canvas.draw()
colorbar_image = np.array(fig.canvas.renderer.buffer_rgba())

# Add as an image overlay in Napari
viewer.add_image(colorbar_image, name="Colorbar", opacity=0.7, colormap='gray')

napari.run()
