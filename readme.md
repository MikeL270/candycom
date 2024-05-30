# CandyCom

CandyCom is an asynchronous communication protocal for a candy machine controlled by a circuit python device. This small protocal makes use of Asyncio to automate sending/recieving and connection management. The end result is a simple, easy to use module which leads to easy to read code. 

## Use Case

CandyCom was originally designed to assist in PST (Probalistic Selection Task) research by integrating with PshycoPy based game which presented the player with the selection tasks. From the start candyCom was designed to be massively extensible and versatile. If your research project needs reliable and fast dispensing of rewards (candy?) look no further than the GIRRLS dispenser communicating over candycom.

GIRRLS dispenser: https://github.com/cwcpalmer/candy_dispenser_enhancement, https://www.girrls-project.com/

## Installation

CandyCom is planned to be released on PyPi so that it may be installed via pip, Please be patient while we work this out.

## Quickstart

CandyCom makes use of roles, where the host is your pc and the client is the candy machine. Each role is its own **class** within candycom which has its own set of incoming and outgoing circular buffers of 64 bytes each. It is important to note that an instance of candycom uses two buffers, not four as candycom is instanced according to its role.  

### Client Side

First, import the required modules. Please note that this example is pulled from the GIRRLS project, not all modules are included in this repository. 

```python
import candycom
import asyncio
import board
from modeswitch import ModeSwitch #Found in the GIRRLS project itself, used for switching between serial and ble.
```

Next construct a dictionary to contain your board's config, this tells candycom exactly how your board is set up.

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

Next you want to create your instance of the **ClientComms Class** and pass your board config to its initizialization. 

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