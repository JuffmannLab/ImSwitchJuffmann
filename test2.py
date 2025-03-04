import tkinter as tk
import serial

# Set up the serial connection to the Arduino
arduino = serial.Serial('COM4', 9600, timeout=1)
arduino.flush()

# Function to send commands to the Arduino
def send_command(command):
    arduino.write(f"{command}\n".encode())  # Send command as a string

# Function to open the shutter
def open_shutter():
    delay = delay_input.get()
    if delay:  # If there is a delay value
        send_command(f"ONETURN {delay}")
    else:
        send_command("OPEN")  # Send command without delay

# Function to close the shutter
def close_shutter():
        send_command("CLOSE")  # Close the shutter

# Function to loop the shutter
def loop_shutter():
    delay = delay_input.get()
    if delay:  # If there is a delay value
        send_command(f"LOOP {delay}")  # Send LOOP with delay time
    else:
        send_command("LOOP")  # Send LOOP without delay
        
# Create the GUI window
window = tk.Tk()
window.title("Shutter Control")

# Create the "Open" button
open_button = tk.Button(window, text="OPEN", command=open_shutter, width=20)
open_button.pack(pady=10)

# Create the "Close" button
close_button = tk.Button(window, text="CLOSE", command=close_shutter, width=20)
close_button.pack(pady=10)

# Create the "Loop" button
close_button = tk.Button(window, text="LOOP", command=loop_shutter, width=20)
close_button.pack(pady=10)

# Create the delay input field
delay_input = tk.Entry(window, width=10)
delay_input.pack(pady=10)

# Run the GUI loop
window.mainloop()