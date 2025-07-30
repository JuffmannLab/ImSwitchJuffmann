# Documentation of ImSwitch setup
This documentation guide aims to explain how to use imswitch at the Juffmann Laboratories. <br>
It is assumed that ImSwitch is already installed on your device. 
+   [Section 0: Configuration JSON files](#0-configuration-json-files) <br> This section covers the 
    JSON setup files that contain the specific configuration of devices in the current experiment. 
    Since JSON does not allow comments, this section explains which parameters are mandatory for specific devices
    and covers the units of certain parameters.  

+   [Section 1: Monaco Laser](#1-monaco-laser-) <br>
    1.1:  Operating requirements <br>
    1.2: GUI explanation ⚠️🥽 **WARNING: Laser Safety Rules!** 🥽⚠️ <br>
    1.3: Important files 
+   [Section 2: Photometrics BSI Prime](#2-photometrics-bsi-prime) <br>
    2.1: Operating requirements <br>
    2.2: Additional package installation 💻🚫 <br>
    2.3: Important files
    
## 0. Configuration JSON files

Imswitch configuration files are found under `Documents/ImSwitchConfig/imcontrol_setups`. <br>
To load the wanted configuration pass the filename in the `setupFileName` paramater in `Documents/ImSwitchConfig/config/imcontrol_options.json`. <br>

To add a device to your configuration you need to add it in the JSON setup file.
The out-of-the-box ImSwitch implementation supports the following devices: 
+ `detectors`
+ `lasers`
+ `positioners`


**General Device Properties**

| Property            | Required | JSON type           | Explanation                                                                                                                       |
|---------------------|----------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `analogChannel`     | No       | string              | Channel for analog communication. ``null`` if the device is digital ordoesn't use NI-DAQ. If an integer is specified, it will be translated to Dev1/ao{analogChannel} |
| `digitalLine`       | No       | int                 | Line for digital communication. ``null`` if the device is analog ordoesn't use NI-DAQ. If an integer is specified, it will be translated to Dev1/port0/line{digitalLine} | 
| `managerName`       | Yes      | string              | Manager Class name                                                                                                                |
| `managerProperties` | Yes      | (nested) dictionary |  Properties to be read by the manager                                                                                             | 

**Detector Properties**

| Property            | Required | JSON type           | Explanation                                               |
|---------------------|----------|---------------------|-----------------------------------------------------------|
| `forAcquisition`    | Yes      | bool                | True if detector is used for acquisition of images/frames |
| `forFocusLock`      | Yes      | bool                | True if detector is used for the FocusLock                |  

**Laser Properties**

| Property            | Required | JSON type           | Explanation                                               |
|---------------------|----------|---------------------|-----------------------------------------------------------|
| `forAcquisition`    | Yes      | bool                | True if detector is used for acquisition of images/frames |
| `forFocusLock`      | Yes      | bool                | True if detector is used for the FocusLock                |  

**Positioner Properties**

| Property        | Device Type Specific | Optional         | Units | Explanation                                        |
|-----------------|----------------------|------------------|-------|----------------------------------------------------|
| `powerLevel`    | No                   | Laser            |       | Sets the output power of the laser (e.g., "high")  |
| `coolingMode`   | Yes                  | Laser            |       | Controls cooling system (e.g., "auto" or "manual") | 
| `firmwareVer`   | No                   | All Devices      |       | Required firmware version (e.g., "v2.1.0")         |
| `diagnostics`   | Yes                  | Diagnostic Tool  |       | Enables self-checks and status logging             |
| `safetyProtocol`| No                   | Laser Controller |       | Defines safety behavior on fault or overheating    | 

## 1. Monaco Laser 
To operate Monaco via imswitch the PC running imswitch needs to be in the same local network (192.168.0.X)
as communication is done via Telnet (over ethernet). The connection is opened and closed with each seperate interaction.

## 2. Photometrics BSI Prime
There exists a Python wrapper to enable communication with the BSI Prime camera, found on: https://github.com/Photometrics/PyVCAM. 
This is a custom Python package and cannot be installed via pip directly. Custom packages are found in the "vendor" folder. 
In the terminal from the main imswitch directory run the following to install: 

```
cd vendor/PyVCAM-master
python -m pip install .
```
Don't forget the "." (dot) at the end. From GitHub it requires Python version 3.9, the imswitch version of the pyvcam `pyproject.toml` file
is altered to allow version 3.8 as well. So far no bugs. 