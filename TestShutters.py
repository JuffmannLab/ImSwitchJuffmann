import serial
import time

#change the COM port to whatever number the Arduino is connected to
arduino_port = "COM11"
baud_rate = 9600

def send_command(cmd):
    with serial.Serial(arduino_port, baud_rate, timeout=1) as ser:
        ser.write((cmd + "\n").encode())
        time.sleep(0.1)  # Give Arduino a bit of time to respond
        response = ser.readline().decode().strip()
        if response:
            print("Arduino:", response)

def IROff():
    send_command("IR_OFF")

def IROn():
    send_command("IR_ON")

def UVOn():
    send_command("UV_ON")

def UVOff():
    send_command("UV_OFF")