# --------------------------------------------------------------------------------- #
#                                                                                   #
#    Project:          Base Robot With Sensors                                      #
#    Module:           main.py                                                      #
#    Author:           VEX                                                          #
#    Created:          Fri Aug 05 2022                                              #
#    Description:      Base IQ Gen 2 robot with controls and with sensors           #
#                                                                                   #
#    Configuration:                                                                 #
#                      TouchLED in Port 2                                           #
#                                                                                   #
# --------------------------------------------------------------------------------- #

# Library imports
from vex import *

# Brain should be defined by default
brain=Brain()

# Robot configuration code
brain_inertial = Inertial()
#left_drive_smart = Motor(Ports.PORT1, 1, False)
#right_drive_smart = Motor(Ports.PORT6, 1, True)

#drivetrain = SmartDrive(left_drive_smart, right_drive_smart, brain_inertial, 200)
touchled_2 = Touchled(Ports.PORT2)
#optical_3 = Optical(Ports.PORT3)
#distance_7 = Distance(Ports.PORT7)
#bumper_8 = Bumper(Ports.PORT8)

''''
def calibrate_drivetrain():
    # Calibrate the Drivetrain Inertial
    sleep(200, MSEC)
    brain.screen.print("Calibrating")
    brain.screen.next_row()
    brain.screen.print("Inertial")
    brain_inertial.calibrate()
    while brain_inertial.is_calibrating():
        sleep(25, MSEC)
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
'''

# Begin project code
# ---------------------------------------------------------------------------- #
#                                                                              #
# 	Module:       main.py                                                      #
# 	Author:       robpoulter                                                   #
# 	Created:      07/02/2024, 10:46:09                                         #
# 	Description:  IQ2 project                                                  #
#                                                                              #
#   Modified:     Damien Kee - 12/2/24                                         #
#                 Added motor control                                          #
# ---------------------------------------------------------------------------- #


try:
    import uasyncio as asyncio
except ImportError:
    try:
        import asyncio
    except ImportError:
        print("asyncio not available")
        raise SystemExit

class SerialMonitor:
  def __init__(self, brain, touchled_2):
    self.serial_port = None
    self.brain = brain
    self.buffer = "" # incoming string buffer
    self.packets = [] # complete packets
    self.read_errors = 0 # exceptions from serial read or decode
    self.encode_errors = 0 # invalid packet encoding
    try:
      self.serial_port = open('/dev/serial1', 'r+b')
    except:
      self.brain.screen.print("Serial port not available")
      raise SystemExit

  async def read_serial(self):
    """
    Constantly read lines from the serial port and add them to the
    buffer. There's some basic error monitoring here, but it seems
    fairly reliable so far at low volumes (tested processing 10 messages
    per second so far without issue)
    """
    while True:
      try:
        line = self.serial_port.readline()
        if line:
          self.buffer += line.decode().strip()
      except:
        self.read_errors += 1
      await asyncio.sleep(0)

  async def report_serial(self):
    """
    Check the contents of the serial buffer to see if any complete
    packets are available, and then process any complete packets.
    """

    while True:
      if len(self.buffer) > 0:
        # check for a complete packet, see if we have an end marker
        b = self.buffer.split(":E", 1)
        if len(b) > 1:
          # if we have a start marker, add the contents to the packets
          # list, log any bad packets to the counter
          if b[0].startswith("M:"):
            self.packets.append(b[0][2:])
          else:
            self.encode_errors += 1
          # reset the buffer to the rest of the string, this should
          # discard any invalid packets
          self.buffer = b[1]

      # If there are any packets on the queue, pop off the first packet
      # and process it. This example prints the x and y coordinates to
      # separate lines on the screen and also controls the two motors
      # to move the camera.
      if len(self.packets) > 0:
        packet = self.packets.pop(0)
        systolic, diastolic, pulse = packet.split(",")
        self.brain.screen.clear_screen()
        self.brain.screen.set_cursor(1, 1)
        self.brain.screen.print("Systolic: {}".format(systolic))
        self.brain.screen.set_cursor(2, 1)
        self.brain.screen.print("Diastolic: {}".format(diastolic))
        self.brain.screen.set_cursor(3, 1)
        self.brain.screen.print("Pulse: {}".format(pulse))
        systolic = int(systolic)
        diastolic = int(diastolic)
        pulse = int(pulse)
        self.brain.screen.set_cursor(4, 1)
        if systolic > 140: 
          self.brain.screen.print("HIGH")
          touchled_2.set_color(Color.RED)
          touchled_2.set_brightness(100)
        elif systolic >= 120 and systolic <= 129 and diastolic >= 80 and diastolic <= 84:
          self.brain.screen.print("NORMAL")
          touchled_2.set_color(Color.GREEN)
          touchled_2.set_brightness(100)
        elif systolic < 120 and diastolic < 80:
          self.brain.screen.print("OPTIMAL")
          touchled_2.set_color(Color.YELLOW)
          touchled_2.set_brightness(100)
        else:
          self.brain.screen.print("Retake... ERROR")
          touchled_2.set_color(Color.BLUE)
          touchled_2.set_brightness(100)

        try:
          systolic = int(systolic)
          diastolic = int(diastolic)
        except ValueError:
          continue

      # give control back to the async loop
      await asyncio.sleep(0)

  def write_serial(self, msg):
    """
    Since we're using serial access over regular file access, probably
    best to flush every time.
    """
    self.serial_port.write("{}\r\n".format(msg).encode("utf-8"))
    self.serial_port.flush()


  def __del__(self):
    self.serial_port.close()


msg = "Starting up..."
brain.screen.print(msg)

# set up the serial monitor and provide it with the VEX objects
monitor = SerialMonitor(brain, touchled_2)

# Set up the async tasks which each run forever - potentially
# add another dummy task with other robot controls and that
# way we get to leave this part of the program alone?
loop = asyncio.get_event_loop()
loop.create_task(monitor.read_serial())
loop.create_task(monitor.report_serial())
loop.run_forever()