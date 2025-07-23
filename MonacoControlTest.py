import telnetlib as tn
import time
MONACO = "192.168.0.5"
PORT = 23                   #default telnet port
SHELL_PROMPT = b'Monaco>'
CMD = "?ALL"
if __name__ == "__main__":
    connection = tn.Telnet(MONACO, PORT)
    output = connection.read_until(SHELL_PROMPT).decode('ascii')
    # print(output)

    tosend = CMD.encode('ascii') + b'\r\n'
    connection.write(tosend)
    buffer = connection.read_until(SHELL_PROMPT, timeout=5).decode('ascii')
    print(buffer)

    connection.write("RL=50".encode('ascii')+b'\r\n')
    IP = connection.read_until(SHELL_PROMPT, timeout=5).decode('ascii')
    print(IP)
    connection.close()
