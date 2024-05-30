# CandyCom

CandyCom is an asynchronous communication protocol for a candy machine controlled by a CircuitPython device. This small protocol makes use of asyncio to automate sending/receiving and connection management. The end result is a simple, easy-to-use module that leads to easy-to-read code.

## Use Case

CandyCom was originally designed to assist in PST (Probabilistic Selection Task) research by integrating with a PsychoPy-based game that presented the player with selection tasks. From the start, CandyCom was designed to be massively extensible and versatile. If your research project needs reliable and fast dispensing of rewards (candy?), look no further than the GIRRLS dispenser communicating over CandyCom.

GIRRLS dispenser: https://github.com/cwcpalmer/candy_dispenser_enhancement, https://www.girrls-project.com/

## Installation

CandyCom is planned to be released on PyPi so that it may be installed via pip, Please be patient while we work this out.

## Quickstart

CandyCom makes use of roles, where the host is your PC and the client is the candy machine. Each role is its own class within CandyCom, each with its own set of incoming and outgoing circular buffers of 64 bytes each. It is important to note that an instance of CandyCom uses two buffers, not four, as CandyCom is instantiated according to its role. 

### Client Side

First, import the required modules. Please note that this example is pulled from the GIRRLS project, and not all modules are included in this repository.

```python
import candycom
import asyncio
import board
from modeswitch import ModeSwitch #Found in the GIRRLS project itself, used for switching between serial and ble.
```

Next, construct a dictionary to contain your board's config. This tells CandyCom exactly how your board is set up.

```python
board_config = { # this is the default config for the GIRRLS candy machine
    mode_switch_pin": board.D5,
    "connected_led_pin": board.BLUE_LED,
    "neopixel_pin": board.NEOPIXEL,
    "candy_dispensed_pin": board.A0,
    "candy_dispensed_led_pin": board.D3,
    "candy_taken_pin": board.A1,
    "stepper_coil_1_orange_pin": board.D6,
    "stepper_coil_2_pink_pin": board.D10,
    "stepper_coil_3_yellow_pin": board.D9,
    "stepper_coil_4_blue_pin": board.D11
}
```

Next, create your instance of the ClientComms Class and pass your board config to its initialization. 

```python
ex_instance = candycom.ClientComms(board_config)
```

It is advised that you run CandyCom inside of an async function by awaiting **establish_connection** and wrapping your execution loop inside of a **while (YourInstance).is_connected:** loop with an **asyncio.sleep(time)** inside of it to allow candycom to run in the background "alongside" (async) your other code.

```python
async def main():
    # await the connection with the host
    await ex_instance.establish_connection('serial') 
    while ex_instance.is_connected:
        await asyncio.sleep(0.05) # sleep to allow the coroutines to run
        # Here you can do other things that do not interfere with candycom's operations
        # Keep your execution time in mind as it effects the performance of CandyCom
```

Finally, run your async function.

```python
asyncio.run(main())
```

### Host Side

How you engineer your "host" program depends upon your usecase. If you write your code around asyncio then implementing CandyCom will be a breeze. It is not in the perview of this project to provide a tutorial on writing asyncio code. Instead consult the python documentation: https://docs.python.org/3/library/asyncio.html

If you are integrating CandyCom into an existing project, like was done for the GIRRLS project, it is advised to make use of the multiprocessing module and communicating between your processes with **Pipes**.

First, import everything you will be using from multiprocessing, for the GIRRLS project we used:

```python
from multiprocessing import Process, freeze_support, Event, Value, Pipe
import candycom
import asyncio
```

The intention is to run your main code and CandyCom as two seperate processes that communicate using Pipe objects. This is very simple to do in python. As always is the case with multiprocessing, the example is simple and the impelmentation is painful. We feel you.

First, you want to create **Pipe** instances and declare an empty com object.

```python
parent_conn, child_conn = Pipe()
com = None # We will use this in a minute
candycom_process = None
main_process = None
```

Next you want to create a function that works as your main execution loop for CandyCom, again we are going to use the **.is_connected** method in a while loop. We are going to do some asyncio shennanigans to get the two modules to play nice. 

```python
async def connect_to_candy_machine(): # cheaky async function to wrap conneciton establisment
    await com.establish_connection()

def candycom_process_func(conn): #conn is one of the two Pipe objects we instanced earlier
    global com
    com = candycom.HostComms('serial')
    asyncio.run(connect_to_candy_machine())
    while com.is_connected:
        if conn.poll():
            message = conn.recv()

            if message == "dispense_candy":
                asyncio.run(com.dispense_candy())

        if com.candy_taken:
            conn.send("candy_taken")
```

Now we will create and run CandyCom's process. 

```python
def start_candycom():
    global candycom_process
    candycom_process = Process(target=candycom_process, args=(child_conn,), daemon=True)
    candycom_process.start()
    return candycom_process

start_candycom()
```

This will spawn a process that you can interact with by using the host_conn object.

```python
    while True:
        # Example: send a dispense candy command every 5 seconds
        parent_conn.send("dispense_candy")
        print("Sent: dispense_candy")
        
        # Wait for a response
        if parent_conn.poll():
            response = parent_conn.recv()
            if response == "candy_taken":
                print("Received: candy_taken")
        
        # Sleep for 5 seconds before next command
        time.sleep(5)
```
