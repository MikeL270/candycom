# CandyCom

CandyCom is an asynchronous communication protocal for a candy machine controlled by a circuit python device. This small protocal makes use of Asyncio to automate sending/recieving and connection management. The end result is a simple, easy to use module which leads to easy to read code. 

## Use Case

CandyCom was originally designed to assist in PST (Probalistic Selection Task) research by integrating with PshycoPy based game which presented the player with the selection tasks. From the start candyCom was designed to be massively extensible and versatile. If your research project needs reliable and fast dispensing of rewards (candy?) look no further than the GIRRLS dispenser communicating over candycom.

GIRRLS dispenser: https://github.com/cwcpalmer/candy_dispenser_enhancement, https://www.girrls-project.com/

## Installation

CandyCom is planned to be released on PyPi so that it may be installed via pip, Please be patient while we work this out.

## Quickstart

First, import the modlue

```python
import candycom