# Juffmann Lab custom ImSwitch implementation

This branch (`iscat_interferometer`) contains the ImSwitch implementation developed for the Juffmann Lab microscope setup.

The main additions are support for FLIR Blackfly cameras through the Spinnaker/PySpin SDK, simultaneous dual-camera operation, software camera ROIs, live intensity profiles, image/profile saving tools, and control of a Thorlabs BPC303 piezo controller.

The dual-camera implementation and the functionality described below were tested with the physical cameras on the laboratory Windows computer in August 2026.

## Quick start

The configuration used for the laboratory setup is:

```text
imswitch/_data/user_defaults/imcontrol_setups/blackfly_dual_test.json
```

This setup currently defines:

- two FLIR Blackfly cameras (`Blackfly1` and `Blackfly2`);
- the lasers used by the microscope;
- a Thorlabs BPC303 piezo controller with PX, PY and PZ axes;
- the Settings, View, Recording, Image, Positioner and LiveProfile widgets.

The two cameras are assigned through:

```text
Blackfly1 -> cameraListIndex: 0
Blackfly2 -> cameraListIndex: 1
```

Both cameras require the FLIR Spinnaker SDK and the Python `PySpin` bindings.

The configuration assumes that the required hardware drivers, including Thorlabs Kinesis for the BPC303, are installed on the laboratory Windows computer.

## Dual-camera LiveView

`BlackflyManager` supports simultaneous acquisition from two FLIR Blackfly cameras.

Both acquisition detectors are displayed in the same LiveView. The images are arranged vertically so that they do not overlap.

The detector layers are scaled in the viewer to have the same displayed width and height. This scaling is **visual only**. It does not change the camera acquisition resolution or the pixel values stored in the acquired images.

Therefore:

> Equal display size does not imply equal acquisition resolution.

The original detector arrays are preserved for acquisition and saving.

## Camera software ROI

The Blackfly implementation supports software cropping.

The camera continues acquiring its full frame and the selected ROI is applied to the NumPy image before it is sent to LiveView/Snap.

ROI position and size can be controlled from the detector settings.

This should not be confused with the separate **LiveProfile ROI**, described below.

## LiveProfile

The `LiveProfile` widget provides live one-dimensional intensity profiles from a user-selectable region of each camera.

When **Live ROI** is enabled:

- one independent ROI is shown for each acquisition detector;
- each detector has its own LiveProfile data;
- both detector profiles are plotted simultaneously in the same graph;
- the graph legend identifies the corresponding detector;
- the ROI and graph curve belonging to a detector use the same color.

The profile can be calculated in two modes:

- **Horizontal:** intensity along the local horizontal axis of the ROI;
- **Vertical:** intensity along the local vertical axis of the ROI.

A thin central band of pixels is averaged to reduce noise.

### Moving and resizing the LiveProfile ROI

The ROI can be:

- dragged from inside to move it;
- dragged from its corner handle to resize it;
- rotated using **Shift + drag** on the corner handle.

Horizontal and vertical profiles are defined in the **local coordinate system of the rotated ROI**, rather than the fixed camera x/y axes.

Each detector has an independent ROI.

### LiveProfile with different camera sizes

Because the detector images may be visually rescaled in LiveView, LiveProfile converts the displayed ROI coordinates back to the corresponding raw detector coordinates before sampling the image.

This allows the ROI to remain correctly associated with its detector even when the two cameras have different image dimensions.

## Recording and data saving

The Recording widget contains the standard `SNAP` and `REC` controls together with the profile saving tools.

The following additional buttons are available:

- `Save horizontal profile`
- `Save vertical profile`
- `Save LiveProfile profile`
- `Save LiveProfile ROI image`

These actions use the detector selection in **Detector(s) to capture**.

Therefore, selecting:

- **Current detector at start** applies the action to the current detector;
- **All acquisition detectors** applies it to both Blackfly cameras;
- **Specific detector(s)** applies it to the explicitly selected detector(s).

This behavior is shared by SNAP and the profile/ROI saving controls.

### SNAP

When multiple acquisition detectors are selected, SNAP acquires and saves one image for each detector.

TIFF snapshots preserve the original detector data. No contrast stretching or conversion to 8-bit is applied before the TIFF is written.

The detector name is included in the filename, for example:

```text
..._snap_Blackfly1.tiff
..._snap_Blackfly2.tiff
```

Contrast adjustment in LiveView is therefore independent from the scientific data saved to disk.

### Horizontal and vertical profiles

`Save horizontal profile` and `Save vertical profile` operate on the latest frame of each selected detector.

For each detector, the software saves:

```text
..._Blackfly1_profile_horizontal.csv
..._Blackfly1_profile_horizontal.png
```

or the corresponding vertical files.

The CSV contains pixel position and gray value. The PNG provides a quick visualization of the saved profile.

### LiveProfile profile

`Save LiveProfile profile` saves the latest profile calculated inside the LiveProfile ROI.

For each selected detector, both a CSV file and a PNG plot are generated.

The detector name is included in the filename so data from `Blackfly1` and `Blackfly2` cannot overwrite each other.

### LiveProfile ROI image

`Save LiveProfile ROI image` saves the image used for the LiveProfile calculation as a TIFF.

**Important:** this file is not necessarily a raw rectangular subarray of the camera sensor.

The LiveProfile ROI can be translated, resized and rotated. Its image is sampled using coordinate mapping and interpolation. The saved LiveProfile ROI TIFF therefore represents the image used for the LiveProfile calculation and may contain interpolated pixel values.

For unmodified detector data, use the standard **SNAP TIFF** instead.

## Output location

SNAP, profiles and LiveProfile data are saved using the folder selected in the Recording widget.

Detector names are included in detector-specific output filenames to keep data from both cameras separate.

## Thorlabs BPC303 control

This branch also contains a positioner manager for the Thorlabs BPC303 piezo controller.

The laboratory configuration exposes three axes:

```text
PX
PY
PZ
```

Communication uses the Thorlabs Kinesis libraries installed on the Windows laboratory computer.

The corresponding implementation is located in the ImSwitch positioner managers.

## Relevant implementation files

The main files added or modified for this implementation are:

```text
imswitch/imcontrol/model/managers/detectors/BlackflyManager.py
```

FLIR Blackfly camera control, software ROI, detector profiles and LiveProfile saving.

```text
imswitch/imcontrol/model/liveprofile_state.py
```

Stores the latest LiveProfile profile, ROI image, mode and timestamp independently for each detector.

```text
imswitch/imcontrol/controller/controllers/LiveProfileController.py
```

Connects live camera frames to the detector-specific ROIs and calculates the horizontal/vertical LiveProfile data.

```text
imswitch/imcontrol/view/widgets/LiveProfileWidget.py
```

LiveProfile user interface, detector-specific ROIs and multi-camera profile graph.

```text
imswitch/imcontrol/view/widgets/ImageWidget.py
```

Arrangement and visual scaling of multiple detector layers in LiveView.

```text
imswitch/imcontrol/controller/controllers/RecordingController.py
```

Connects the Recording controls to SNAP, recording and detector-specific profile/ROI saving.

```text
imswitch/imcontrol/model/managers/RecordingManager.py
```

Handles recording and snapshot storage, including raw TIFF snapshot output.

```text
imswitch/_data/user_defaults/imcontrol_setups/blackfly_dual_test.json
```

Laboratory hardware configuration for the dual-Blackfly setup, lasers and BPC303 positioner.

## Tested functionality

The following functionality was tested with the physical dual-camera setup on the laboratory Windows computer:

- simultaneous connection to both Blackfly cameras;
- simultaneous LiveView;
- independent detector operation;
- equal-size visual arrangement of both camera images;
- independent LiveProfile ROIs;
- simultaneous detector-specific LiveProfile curves;
- moving, resizing and rotating the LiveProfile ROI;
- horizontal and vertical intensity profiles;
- detector-specific profile and ROI saving;
- dual-camera SNAP and recording controls.

## Known limitations and future work

The current implementation was developed for the Juffmann Lab setup and should be tested again if camera models, drivers or hardware configuration are changed.

In particular:

- camera assignment currently relies on `cameraListIndex`; using camera serial numbers would provide more robust camera identification if USB enumeration order changes;
- LiveView equal-size scaling is intended for convenient visualization and should not be interpreted as a physical registration between the two cameras;
- LiveProfile ROI images may contain interpolated values and should not be used as raw detector data;
- hardware-specific paths and device configuration are defined in the laboratory setup JSON and may need to be adapted on another computer.

For quantitative analysis requiring original camera values, use the raw TIFF files produced by SNAP.

---
