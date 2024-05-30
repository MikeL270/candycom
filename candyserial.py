# candyserial Circuit Python Library ((ROUGH DRAFT))
# By Michael Lance
# 2/7/2024
# Updated 3/8/2024
#------------------------------------------------------------------------#
import sys
import serial 
import serial.tools.list_ports
import asyncio
import time
#------------------------------------------------------------------------#
# Create function to determine the platform that the library is ran from
# and select an available Serial Port

class usb_serial:
    def __init__(self, baudrate=9600):
        ports = list(serial.tools.list_ports.comports())
        self.port = None
        self.ser = None
        
        for port_info in ports:
            port = port_info.device  # Use the port name (string)
            print(f"Trying {port}...")
            try:
                ser = serial.Serial(port, baudrate, timeout=1)
                ser.write(b"correct port")  # Ensure bytes are sent
                time.sleep(1)
                resp = ser.read(12)  # Adjust size according to the expected response length
                if resp == b"correct port":
                    print(f"Correct port found: {port}")
                    self.port = port_info
                    self.ser = ser
                    break  # Exit the loop if the correct port is found
                else:
                    ser.close()  # Close the serial connection if it's not the correct port
            except Exception as e:
                print(f"Error on port {port}: {e}")

        if self.ser and self.ser.is_open:
            print(f"Connected to {self.port.device} at {baudrate} baud.")
        else:
            print("Failed to open serial port or correct port not found.")
            exit()


    def flush_ser_buffer(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def write(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8') 
        self.ser.write(data)
    
    def read(self, nbytes=32):
        """Read data from the USB serial connection."""
        data = self.ser.read(nbytes)
        if data:
            return data.decode('utf-8') 
        return None 

    def check_ser_buffer(self):
        """Check if there's data waiting in the serial buffer."""
        return self.ser.in_waiting > 0