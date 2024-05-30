# Asyncio based rewrite of candycom
# Written by Michael Lance & Thomas Baker
# 3/5/2024
# Updated: 5/30/2024
#---------------------------------------------------------------------------------------------------#
import asyncio
import sys
import time
from .candyble import *
# import different libraries depending upon platform
if sys.implementation.name != 'circuitpython':
    from .candyserial import *
    usb_cdc = None # Used to appease the python interpreter
    motorcontrol = None
    digitalio = None
    neopixel = None
    is_arduino = False
    microcontroller = None
elif sys.implementation.name == 'circuitpython':
    import usb_cdc
    import motorcontrol
    import digitalio
    import neopixel
    import microcontroller
    candyserial = None  # Used to appease the python interpreter
    is_arduino = True

#---------------------------------------------------------------------------------------------------#
# Create dictionaries to store command, event, and acks

comm_dict = {
    # Commands
    "establish_connection" : "~ES",
    "dispense_candy"       : "~ID",
    "reset_dispenser"      : "~QD",
    "maintain_connection"  : "~RS",
    "disconnect"           : "~FL",

    # Events
    "jam_or_empty"    : "%JP",
    "candy_taken"     : "$FD",
}

ack_dict = {
    # Command Acks
    "~ES" : "@es", # Establish conenction ack
    "~ID" : "@iD", # Dispense candy ack
    "~QD" : "@qD", # Reset dispenser ack
    "~RS" : "@rs", # Maintain Connection ack
    "~FL" : "@fl", # Disconnect ack

    # Event Acks
    "%JP"   : "@jp", # Jam ack
    "$FD"   : "@fd", # Candy taken ack
}

#---------------------------------------------------------------------------------------------------#
# Create Circular Buffers to be used by each role

class CircBuffer:
    def __init__(self, capacity: int):
        self.buffer = [None] * capacity
        self.capacity = capacity
        self.start = 0
        self.end = 0
        self.size = 0

    def is_full(self) -> bool: # Return true if buffer is full
        return self.size == self.capacity

    def is_empty(self) -> bool: # Inverse of is_full
        return self.size == 0

    def enqueue(self, item):
        if self.is_full():
            print(f'Warning: Buffer Filled, Data Lost: {item}')
        self.buffer[self.end] = item
        self.end = (self.end + 1) % self.capacity
        self.size += 1

    def dequeue(self):
        if self.is_empty():
            return None
        item = self.buffer[self.start]
        self.buffer[self.start] = None
        self.start = (self.start + 1) % self.capacity
        self.size -= 1
        return item

    def check_data(self) -> bool: # Check if data is on the buffer
        return not self.is_empty()

    def peek(self): # Returns data but does not remove data
        if self.is_empty():
            return None
        return self.buffer[self.start]

    def flush(self): #Clears all data from buffer
        while not self.is_empty():
            print('removing from buffer')
            self.dequeue()
#---------------------------------------------------------------------------------------------------#
# Create Class for the client side of the protocol

class ClientComms:
    def __init__(self, board_config, comm_mode="serial", buffer_size=64):
        # Configure conection leds
        self.connected_led = digitalio.DigitalInOut(board_config["connected_led_pin"])
        self.connected_led.direction = digitalio.Direction.OUTPUT
        self.timeout = time.monotonic()
        self.pixels = neopixel.NeoPixel(board_config["neopixel_pin"], 1)
        # Configure beam breakers for candy taken

        # Create two buffer instances
        self.IncommingBuffer = CircBuffer(buffer_size)
        self.OutgoingBuffer = CircBuffer(buffer_size)
        self.stepper_motor = motorcontrol.StepperMotor(board_config)
        self.comm_mode = comm_mode

        # Create watchdog management variables
        self.watchdog_timeout = 16 # Roughly every second
        self.watchdog_timer = 0
        # Create flag management dict and total flag count
        # Flag system not fully developed, subject to deprecation
        self.is_connected = False
        self.flag_count = 0
        self.client_flags = {
        "@jp": 0, # Jam flag
        "@ir": 0, # Candy taken flag
        "@fd": 0,
        #"report_battery_flag": 0
        }
#---------------------------------------------------------------------------------------------------#
    # Create methods for interacting with buffers
    def check_data_on_serial(self) -> bool: # Return True if atleast 3 bytes are on serial buffer
        if self.comm_mode == "serial": # Use different commands for different methods of connection
            if usb_cdc.data.in_waiting >= 3:
                return True
            else:
                return False
        elif self.comm_mode == "ble":
            if self.ble_ser.uart.in_waiting >= 3:
                return True
            else:
                return False

    def check_data_outgoing(self) -> bool: # Return True if there is data to send
        return self.OutgoingBuffer.check_data()

    def check_data_incoming(self) -> bool: # Return True if we recieved data
        return self.IncommingBuffer.check_data()

    def enqueue_message(self, message): # Add message to client outgoing buffer
        # Set flag if the message is recognized format
        if message in comm_dict.values(): # Defend against non candycom data
            self.client_flags[ack_dict[message]] += 1
            self.flag_count += 1
            self.OutgoingBuffer.enqueue(message)
        elif message in ack_dict.values():
            self.OutgoingBuffer.enqueue(message)
        else:
            return

    def dequeue_message(self): # Pull message from incoming buffer
        if self.IncommingBuffer.check_data(): # Defend against non candycom data
            message = self.IncommingBuffer.dequeue()
            if message in self.client_flags.keys():
                self.client_flags[message] -= 1
                self.flag_count -= 1
            if message in comm_dict.keys():
                self.enqueue_message(ack_dict[message])

            return message

    # Create async methods for transmitting data
    async def receive_message(self): # Pull message from serial to incoming buffer
        if self.comm_mode == "serial":
            message = usb_cdc.data.read(3).decode('utf-8')
        elif self.comm_mode == "ble":
            message = self.ble_ser.read()
        print(f'recieved: {message}')
        self.IncommingBuffer.enqueue(message)

    async def transmit_message(self): # write message from outoing to serial buffer
        message = self.OutgoingBuffer.dequeue()
        print(f'transmitted: {message}')
        if self.comm_mode == "serial":
            usb_cdc.data.write(message.encode('utf-8'))
        elif self.comm_mode == 'ble':
            self.ble_ser.write(message)

    # Create async watchdog method to maintain the connection
    async def connection_watchdog(self): # counts up every 5 seconds, resets script in timeout achieved
        while self.is_connected:
            if not self.check_data_incoming():
                self.watchdog_timer += 1
                print(f"watchdog {self.watchdog_timer}/{self.watchdog_timeout}")

            if self.watchdog_timer == self.watchdog_timeout:
                self.is_connected = False
                #if self.comm_mode == 'ble':
                 #   self.ble_ser.disconnect()
                self.run_comm_handler.cancel()
            await asyncio.sleep(5)
        print("watchdog exited successfully")
        microcontroller.reset() # reset the board

    async def reset_watchdog(self): # reset the watchdog counter if the right message is recieved
        self.watchdog_timer = 0
        self.enqueue_message(ack_dict[comm_dict["maintain_connection"]])

    # Create async method used to handle communications
    async def comm_handler(self): # daemon-esq process which automates sending and recieving data over serial/ble
        print("running comm_handler")
        # Declare two async funcitons for incoming and outgoing to run in asyncio.gather() to run them "toghether"
        async def incoming_comm_handler():
            if self.check_data_on_serial():
                await self.receive_message()
            else:
                await asyncio.sleep(0.01)

        async def outgoing_comm_handler():
            if self.check_data_outgoing():
                await self.transmit_message()
            else:
                await asyncio.sleep(0.01)

        while self.is_connected:
            await asyncio.gather( # Run both comm_handler sub methods at the "same time"
                incoming_comm_handler(),
                outgoing_comm_handler(),
            )

            if time.monotonic() > self.timeout: # determine if the neopixels need shut off
                self.pixels[0] = (0, 0, 0)

            if self.check_data_incoming():
                await self.mesage_interpreter() # If a message was recieved, execute its function

        print("comm_handler exited")

    # Create async method to handle connection establishment
    async def establish_connection(self): # Ensures that there is someone to talk to
        if self.comm_mode == "serial":
            #while usb_cdc.data.in_waiting: # Flush the serial buffer
            #    usb_cdc.read(usb_cdc.data.in_waiting)  
            found_port = False 
            print("Attemptin to connect to PC")
            while not found_port:
                bob = usb_cdc.data.read(12)
                if bob == b"correct port":
                    usb_cdc.data.write(b"correct port")
                    print("Found port, connecting")
                    found_port = True
            
        elif self.comm_mode == "ble":
            print("BLE enabled: waiting for host...")
            self.ble_ser = BleClient()
            self.ble_ser.connect()

        print("Waiting for connection to be established")
        self.connected_led.value = False

        while not self.is_connected: # wait for the host to send the proper command to start
            if self.check_data_on_serial():
                await self.receive_message()
                if self.dequeue_message() == comm_dict["establish_connection"]:
                    self.enqueue_message(ack_dict["~ES"])
                    await self.transmit_message()
                    print("Connetion Established by host")
                    self.is_connected = True
                    self.IncommingBuffer.flush()
                    self.connected_led.value = True

            await asyncio.sleep(0.5) # wait half a second after connecting

        # Spawn background tasks to manage transmission and connection maintenance
        self.run_comm_handler = asyncio.create_task(self.comm_handler())
        self.run_connection_watchdog = asyncio.create_task(self.connection_watchdog())

    async def dispense_candy(self): # Called when dispense_candy command is sent from host
        self.timeout = time.monotonic() +0.5
        self.pixels[0] = (0, 10, 0)
        await self.stepper_motor.rotate_motor()
        watch_taken =  asyncio.create_task(self.watch_for_taken())
        self.enqueue_message(ack_dict[comm_dict["dispense_candy"]])

    def alert_candy_taken(self): # Inform the host that candy has been taken
        self.enqueue_message(comm_dict["candy_taken"])

    async def watch_for_taken(self): # watch for a beam break
        while self.stepper_motor.watch_for_taken:
            while self.stepper_motor.track_num_dispnesed > 0:
                if self.stepper_motor.candy_taken:
                    self.alert_candy_taken()
                    await asyncio.sleep(1)
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.2)

    async def disconnect(self): #disconnect from the host and reset the board
        self.is_connected = False
        self.enqueue_message(ack_dict[comm_dict["disconnect"]])
        await self.transmit_message()
        self.run_comm_handler.cancel()
        self.run_connection_watchdog.cancel()
        if self.comm_mode == "ble":
            self.ble_ser = None
        microcontroller.reset() # reset the board


    async def mesage_interpreter(self): # pull a message from the buffer and figure out what it means
        message_interpertations = {
            "~ID"   :   self.dispense_candy,
            "~RS"   :   self.reset_watchdog,
            "~FL"   :   self.disconnect,

        }

        message = self.dequeue_message()
        if message in message_interpertations:
            await message_interpertations[message]()

#---------------------------------------------------------------------------------------------------#
# Create Class for the Host side of the protocal

class HostComms:
    def __init__(self, comm_mode="serial", buffer_size=64):
       # determine the means of communications to be used
        self.comm_mode = comm_mode

        # configure host based on platform
        global is_arduino
        self.is_arduino = is_arduino
        if is_arduino: # condititional config to allow another arduino to act as host
            self.connected_led = digitalio.DigitalInOut(board_config["connected_led_pin"])
            self.connected_led.direction = digitalio.Direction.OUTPUT
            self.timeout = time.monotonic()
            self.pixels = neopixel.NeoPixel(board_config["neopixel_pin"], 1)

        # Create two buffer instances
        self.IncommingBuffer = CircBuffer(buffer_size)
        self.OutgoingBuffer = CircBuffer(buffer_size)

        # Create watchdog management variables
        self.watchdog_timeout = 16
        self.watchdog_timer = 0

        # Create flag management system
        self.is_connected = False
        self.flag_count = 0
        self.host_flags = {
            "@es": 0, # Establish connection flag
            "@ir": 0, # Candy taken flag
            "@mc": 0, # Candy dispensed flag
            "@rs": 0, # Maintain Conneciton flag
            "@iD": 0, # Candy Dispense flag
            "@fl": 0, # Disconnect flag ?
        }

        # Create booleans to be accessed outside candycom by other programs
        self.candy_dispensed = False
        self.candy_taken = False

        self.candy_stats = {
            "candy_disepnsed"   :   0,
            "candy_taken"       :   0,
        }

    # Create methods for interacting with buffers
    def check_data_on_serial(self) -> bool:  # Return True if atleast 3 bytes are on serial buffer
        if self.comm_mode == 'serial': # Use different commands for different methods of connection
            return self.candyser.check_ser_buffer()
        elif self.comm_mode == 'ble':
            if self.ble_ser.uart_service.in_waiting >= 3:
                return True

    def check_data_outgoing(self) -> bool: # Return True if there is data to send
        return self.OutgoingBuffer.check_data()

    def check_data_incoming(self) -> bool:  # Return True if we recieved data
        return self.IncommingBuffer.check_data()

    def enqueue_message(self, message):  # Add message to host outgoing buffer
        # Set flag if the message is recognized format
        if message in comm_dict.values(): # Defend against non candycom data
            self.host_flags[ack_dict[message]] += 1
            self.flag_count += 1
            self.OutgoingBuffer.enqueue(message)
        elif message in ack_dict.values():
            self.OutgoingBuffer.enqueue(message)
        else:
            print("Warning: Unrecognized message, nothing enqeued")

    def dequeue_message(self): #Pull message from incoming buffer
        if self.IncommingBuffer.check_data(): # Defend against non candycom data
            message = self.IncommingBuffer.dequeue()
            if message in self.host_flags.keys():
                self.host_flags[message] -= 1
                self.flag_count -= 1
            return message
        else:
            return

    # Create async methods for transmitting data
    async def receive_message(self): # Pull message from serial to incoming buffer
        if self.comm_mode == 'serial':
            message = self.candyser.read(3)
        elif self.comm_mode == 'ble' :
            message = self.ble_ser.read()
        print(f'recieved: {message}')
        self.IncommingBuffer.enqueue(message)

    async def transmit_message(self): # write message from outoing to serial buffer
        message = self.OutgoingBuffer.dequeue()
        print(f'transmitted: {message}')
        if self.comm_mode == 'serial':
            self.candyser.write(message)
        elif self.comm_mode == 'ble':
            self.ble_ser.write(message)

    # Create async method used to handle communications
    async def connection_watchdog(self): # counts up every 5 seconds, resets script in timeout achieved
        while self.is_connected:
            if not self.check_data_incoming():
                self.watchdog_timer += 1
                print(f"watchdog {self.watchdog_timer}/{self.watchdog_timeout}")
                self.enqueue_message(comm_dict["maintain_connection"])

            if self.watchdog_timer == self.watchdog_timeout:
                self.is_connected = False
                if self.comm_mode == 'ble':
                    self.ble_ser.disconnect()
            await asyncio.sleep(5)
        print("watchdog exited successfully")


    async def reset_watchdog(self): # Reset the watchdog is the right ack is sent by client
        self.watchdog_timer = 0

    async def comm_handler(self):
        print("running comm_handler")
        # Declare two async funcitons for incoming and outgoing to run in asyncio.gather() to run them "toghether"
        async def incoming_comm_handler():
            if self.check_data_on_serial():
                await self.receive_message()
            else:
                await asyncio.sleep(0.01)

        async def outgoing_comm_handler():
            if self.check_data_outgoing():
                await self.transmit_message()
            else:
                await asyncio.sleep(0.01)
        while self.is_connected:
            await asyncio.gather( # Run both comm_handler sub methods at the "same time"
                incoming_comm_handler(),
                outgoing_comm_handler()
            )
            #if time.monotonic() > self.timeout: # Commented out due to weird freezing issue !BUG!
            #    if self.is_arduino:
            #        self.pixels[0] = (0, 0, 0)

            if self.check_data_incoming():
                await self.message_interpreter() # If a message was recieved, execute its function
        print("comm_handler exited")

    # Create Async Method to handle the connection
    async def establish_connection(self): # Send "connect" command until ack is sent back
        if self.comm_mode == "serial":
            self.candyser = usb_serial()
            self.candyser.flush_ser_buffer()
        elif self.comm_mode == "ble":
            print("BLE enabled... Searching for client...")
            self.ble_ser = BleHost()
            self.ble_ser.connect()
        print("attempting to establish connection")
        if is_arduino:
            self.connected_led.value = False
        while not self.is_connected:
            self.enqueue_message(comm_dict["establish_connection"])
            await self.transmit_message()
            if self.check_data_on_serial():
                print("message recieved")
                await self.receive_message()
                message = self.dequeue_message()
                print(message)
                if message == ack_dict["~ES"]:
                    # Run comm_handler and connection_watchdog as background tasks
                    self.is_connected = True
                    if is_arduino:
                        self.connected_led.value = True
                    pass
            await asyncio.sleep(1)
        print("Connection Established")
        # Create background tasks to handle communication and connection maintenance
        self.run_comm_handler = asyncio.create_task(self.comm_handler())
        self.run_connection_watchdog = asyncio.create_task(self.connection_watchdog())
        self.OutgoingBuffer.flush()

    # Create method to dispense candy
    def dispense_candy(self): # Called to tell the cilent to dispense candy
        global is_arduino
        if is_arduino:
            self.timeout = time.monotonic() + 0.5
            self.pixels[0] = (10, 0, 0)
        self.enqueue_message(comm_dict["dispense_candy"])

    async def disconnect(self):
        self.enqueue_message(comm_dict["disconnect"])

    # Create method to recognize dispense operation
    async def dispense_recognized(self): # Acknowledge a successful dispense
        # set bool for succecssful dispense to true
        print("successful dispense")
        self.candy_dispensed = True
        #self.candy_stats["candy_dispensed"] += 1
        return

    async def taken_candy(self): # Acknowledge that candy has been taken
        print("candy taken")

        self.enqueue_message(ack_dict[comm_dict["candy_taken"]])
        self.candy_taken = True

    async def disconnect_recognized(self): #disconnect from the client
        print("Disconnected")
        self.is_connected = False
        self.run_comm_handler.cancel()
        self.run_connection_watchdog.cancel()
        if self.comm_mode == 'ble':
            self.ble_ser.disconnect()
            self.ble_ser = None

    async def message_interpreter(self):  # pull a message from the buffer and figure out what it means
        message_interpertations = {
            "@iD"   :   self.dispense_recognized,
            "$FD"   :   self.taken_candy,
            "@rs"   :   self.reset_watchdog,
            "@fl"   :   self.disconnect_recognized,

        }
        message = self.dequeue_message()
        if message in message_interpertations:
            try:
                await asyncio.wait_for((message_interpertations[message]()), timeout=2)
            except asyncio.TimeoutError:
                print("The task did not complete in time and was cancelled.")

            print("message interpreted")

#---------------------------------------------------------------------------------------------------#
