import PySpin
system = PySpin.System.GetInstance()
print(f"Found {system.GetCameras().GetSize()} cameras")
system.ReleaseInstance()