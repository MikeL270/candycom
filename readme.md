# CandyCom

CandyCom is an asynchronous communication protocal for a candy machine controlled by a circuit python device. This small protocal makes use of Asyncio to automate sending/recieving and connection management. The end result is a simple, easy to use module which leads to easy to read code. 

## Use Case

CandyCom was originally designed to assist in PST (Probalistic Selection Task) research by integrating with PshycoPy based game which presented the player with the selection tasks. From the start candyCom was designed to be massively extensible and versatile. If your research project needs reliable and fast dispensing of rewards (candy?) look no further than the GIRRLS dispenser communicating over candycom.

GIRRLS dispenser: https://github.com/cwcpalmer/candy_dispenser_enhancement, https://www.girrls-project.com/

## Installation

CandyCom is planned to be released on PyPi so that it may be installed via pip, Please be patient while we work this out.

## Quickstart

CandyCom makes use of roles, where the host is your pc and the client is your device

### Client Side

First, import the modlue

```python
import candycom
import asyncio
import board
from modeswitch import ModeSwitch #Found in the GIRRLS project itself, used for switching between serial and ble.

#construct your board configuration
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

#instance the module

ex_instance = candycom.ClientComms(board_config)

async def main():
    # await the connection with the host
    await ex_instance.establish_connection('serial') 
    while ex_instance.is_connected:
        await asyncio.sleep(0.05) # sleep to allow the coroutines to run


```