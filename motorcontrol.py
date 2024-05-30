# Experimental Stepper Motor Control Library for GIRRLS
# Written by Michael Lance
# 3/5/2024
# Updated: 3/14/2024
#------------------------------------------------------#

# Import Libraries needed to interact with micro controller
from digitalio import DigitalInOut, Direction, Pull
import time
import asyncio
import supervisor

#------------------------------------------------------#

# Create Stepper Motor Class
class StepperMotor:
    def __init__(self, board_config):
        # configure candy dispense pins
        self.candy_dispensed = DigitalInOut(board_config["candy_dispensed_pin"])
        self.candy_dispensed.direction = Direction.INPUT
        self.candy_dispensed.pull = Pull.UP

        # configure candy taken pins
        self.candy_taken_trigger = DigitalInOut(board_config["candy_taken_pin"])
        self.candy_taken_trigger.direction = Direction.INPUT
        self.candy_taken_trigger.pull = Pull.UP

        # track if candy_taken should be tracked
        self.watch_for_taken = False
        self.track_num_dispnesed = 0
        self.candy_taken = False

        # Define boolean to denote whether or not candy has been dispensed
        self.led = DigitalInOut(board_config["candy_dispensed_led_pin"])
        self.led.direction = Direction.OUTPUT

        # Define GPIO Pins to interact with the stepper motor
        self.motor_pin_1 = DigitalInOut(board_config["stepper_coil_4_blue_pin"])
        self.motor_pin_1.direction = Direction.OUTPUT
        self.motor_pin_1.value = False

        self.motor_pin_2 = DigitalInOut(board_config["stepper_coil_2_pink_pin"])
        self.motor_pin_2.direction = Direction.OUTPUT
        self.motor_pin_2.value = False

        self.motor_pin_3 = DigitalInOut(board_config["stepper_coil_3_yellow_pin"])
        self.motor_pin_3.direction = Direction.OUTPUT
        self.motor_pin_3.value = False

        self.motor_pin_4 = DigitalInOut(board_config["stepper_coil_1_orange_pin"])
        self.motor_pin_4.direction = Direction.OUTPUT
        self.motor_pin_4.value = False

        self.cur_step_index = 0
        self.successful_dispense = False

        self.steps = [
            [True, False, False, True],
            [True, True, False, False],
            [False, True, True, False],
            [False, False, True, True],
        ]
        self.motor_off = [False, False, False, False] # OFF

    async def watch_taken(self):
        if self.watch_for_taken == True:
            while self.track_num_dispnesed > 0:
                while self.candy_taken_trigger.value == True:
                    await asyncio.sleep(0.25)
                print("triggered")
                self.candy_taken = True
                await asyncio.sleep(0.25)
                self.track_num_dispnesed -= 1
                self.candy_taken = False
            self.watch_for_taken = False
        else:
            print("candy has not been dispensed")

    # Had to use to following logic as time.sleep was causing odd effects to the motor stepping when on battery and with ble connected
    def blocking_delay(self, delay):
        cur = supervisor.ticks_ms()
        next = cur + delay
        while (next > cur and abs(next - cur) <= delay):
            cur = supervisor.ticks_ms()

    async def rotate_motor(self):
        while not self.successful_dispense:
            for step_index in range(len(self.steps)):
                self.motor_pin_1.value = self.steps[step_index][0]
                self.motor_pin_2.value = self.steps[step_index][1]
                self.motor_pin_3.value = self.steps[step_index][2]
                self.motor_pin_4.value = self.steps[step_index][3]
                self.blocking_delay(3)

            if self.candy_dispensed.value:
                self.led.value = False
            else:
                self.led.value = True
                self.successful_dispense = True

        self.motor_pin_1.value = self.motor_off[0]
        self.motor_pin_2.value = self.motor_off[1]
        self.motor_pin_3.value = self.motor_off[2]
        self.motor_pin_4.value = self.motor_off[3]
        self.track_num_dispnesed += 1
        self.watch_for_taken = True
        self.taken_watch = asyncio.create_task(self.watch_taken())
        self.successful_dispense = False
        self.led.value = False

