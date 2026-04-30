import lib_KDC101 as Motor
import time

Motor.Open()

Motor.PrintPos()
Motor.Move(5)
time.sleep(5)
Motor.PrintPos()
time.sleep(5)
Motor.Home()
time.sleep(5)
Motor.PrintPos()

Motor.Close()