#!/usr/bin/python3
"""
Author:	Nathan Baker
Date:	February 24th, 2013
Name:	tea5767.py
About:	python code for controlling TEA5767 FM radio module
		
		project from:
		http://emmanuelgranatello.blogspot.it/2013/02/fm-radio-receiver-on-raspberry-pi.html
		
		code converted from:
		http://www.electronicsblog.net/arduino-fm-receiver-with-tea5767/
		
		datasheet:
		http://www.sparkfun.com/datasheets/Wireless/General/TEA5767.pdf
		
TODO:
		set the devices information
		put the device into scan mode
		
		
"""
# ----< Table 1 >---------------------------------------------------------------
#
#	[ SSL1 ]	[ SSL0 ]	[	Search Stop Level	]
#		0			0		not allowed in search mode
#		0			1		low;  level ADC output =  5
#		1			0		mid;  level ADC output =  7
#		1			1		high; level ADC output = 10
#
# ----< Table 2 >---------------------------------------------------------------
#
#	[ PLL/REF ]	[ XTAL ]	[	Clock Frequency 	]
#		0			0			13.000	MHz
#		0			1			32.768	kHz
#		1			0			 6.500	MHz
#		1			1			not allowed
#
# ------------------------------------------------------------------------------

# import the sleep library so we don't have to eat cpu cycles on this device
from time import sleep
import sys

# import the quick2wire library to access the i2c bus
import quick2wire.i2c as i2c
from quick2wire.i2c import I2CMaster, writing_bytes, reading


def get_bit(byteval, idx):
    return ((byteval & (1 << idx)) != 0)

class tea5767:
    """Class to control the operation of a TEA5767 FM radio module over I2C using the quick2wire python3 library"""

    def __init__(self):
        """class constructor"""

        # devices i2c address
        self.address = 0x60

        self.crystalOscillatorFrequency = 32768

        self.FMstation = 88.1

        # number of bytes that can be read and written
        self.numReadBytes = 5
        self.numWriteBytes = 5

        # data that is to be written to the device
        # first byte data
        self.mute = 1
        self.searchMode = 0
        # upper frequency byte defined below

        # second byte data
        # lower frequency byte defined below

        # third byte data
        self.SUD = 1  # 1 = search up					0 = search down
        self.searchStopLevel = 1  # 2 bits; see table 1 above		range ( 1 - 3 )
        self.HLSI = 1  # 1 = high side LO injection	0 = low side LO injection
        self.mono = 0  # 1 = forced mono				0 = stereo mode allowed
        self.muteRight = 0  # 1 = right channel muted		0 = right channel not muted
        self.muteLeft = 0  # 1 = left channel muted		0 = left channel not muted
        self.SWP1 = 0  # 1 = port 1 HIGH				0 = port 1 LOW

        # fourth byte data
        self.SWP2 = 0  # 1 = port 2 HIGH				0 = port 2 LOW
        self.standby = 0  # 1 = standby mode				0 = not in standby mode
        self.bandLimits = 0  # 1 = Japanese FM Band			0 = US/European FM Band
        self.XTAL = 1 if self.crystalOscillatorFrequency == 32768 else 0  # see table 2 above
        self.softMute = 0  # 1 = soft mute on				0 = soft mute off
        self.HCC = 0  # 1 = high cut control is ON	0 = high cut control is OFF
        self.SNC = 0  # 1 = stereo noise canceling	0 = no stereo noise canceling
        self.SI = 0  # 1 = SWPORT1 is ready output	0 = SWPORT1 is software programmable

        # fifth byte data
        self.PLL = 1 if self.crystalOscillatorFrequency == 6500000 else 0  # see table 2 above
        self.DTC = 0  # 1 = de-emphasis time constant = 75us
        # 0 = de-emphasis time constant = 50us

        # status read from device
        # first byte data
        self.readyFlag = 0
        self.bandLimitFlag = 0
        self.upperFrequencyByte = 0x00

        # second byte data
        self.lowerFrequencyByte = 0x00

        # third byte data
        self.stereoFlag = 0
        self.IFcounter = 0x00

        # fourth byte data
        self.levelADCoutput = 0x00
        self.chipID = 0x00
        # chip ID is set to 0
        # bit 0 is unused

        # fifth byte data
        # these are unused on the 5767

        self.readBytes()
        self.calculateByteFrequency()

    def readBytes(self):
        """read the devices current state"""
        with i2c.I2CMaster() as bus:
            results = bus.transaction(
                reading(self.address, self.numReadBytes)
            )
            # bc = 'on' if c.page=='blog' else 'off'

            # first byte data
            self.readyFlag = 1 if results[0][0] & 0x80 else 0
            self.bandLimitFlag = 1 if results[0][0] & 0x40 else 0
            self.upperFrequencyByte = results[0][0] & 0x3F

            # second byte data
            self.lowerFrequencyByte = results[0][1]

            # third byte data
            self.stereoFlag = 1 if results[0][2] & 0x80 else 0
            self.IFcounter = results[0][2] & 0x7F

            # fourth byte data
            self.levelADCoutput = results[0][3] >> 4
            self.chipID = results[0][3] & 0x0E

            self.calculateFrequency()

    def writeBytes(self):
        """write the data to the device"""

        self.calculateByteFrequency()

        # make sure we initialize everything to avoid possible issues
        byteOne = 0x00
        byteTwo = 0x00
        byteThree = 0x00
        byteFour = 0x00
        byteFive = 0x00

        # first byte
        byteOne = byteOne + 0x80 if self.mute == 1 else byteOne
        byteOne = byteOne + 0x40 if self.searchMode == 1 else byteOne
        byteOne = byteOne + self.upperFrequencyByte

        # second byte
        byteTwo = self.lowerFrequencyByte

        # third byte
        byteThree = byteThree + 0x80 if self.SUD == 1 else byteThree
        byteThree = byteThree + (self.searchStopLevel << 5)
        byteThree = byteThree + 0x10 if self.HLSI == 1 else byteThree
        byteThree = byteThree + 0x08 if self.mono == 1 else byteThree
        byteThree = byteThree + 0x04 if self.muteRight == 1 else byteThree
        byteThree = byteThree + 0x02 if self.muteLeft == 1 else byteThree
        byteThree = byteThree + 0x01 if self.SWP1 == 1 else byteThree

        # fourth byte
        byteFour = byteFour + 0x80 if self.SWP2 == 1 else byteFour
        byteFour = byteFour + 0x40 if self.standby == 1 else byteFour
        byteFour = byteFour + 0x20 if self.bandLimits == 1 else byteFour
        byteFour = byteFour + 0x10 if self.XTAL == 1 else byteFour
        byteFour = byteFour + 0x08 if self.softMute == 1 else byteFour
        byteFour = byteFour + 0x04 if self.HCC == 1 else byteFour
        byteFour = byteFour + 0x02 if self.SNC == 1 else byteFour
        byteFour = byteFour + 0x01 if self.SI == 1 else byteFour

        # fifth byte data
        byteFive = byteFive + 0x80 if self.PLL == 1 else byteFive
        byteFive = byteFive + 0x40 if self.DTC == 1 else byteFive

        with i2c.I2CMaster() as bus:
            bus.transaction(
                writing_bytes(self.address, byteOne, byteTwo, byteThree, byteFour, byteFive)
            )

    def calculateByteFrequency(self):
        """calculate the upper and lower bytes needed to set the frequency of the FM radio module"""

        frequency = int(4 * (self.FMstation * 1000000 + 225000) / self.crystalOscillatorFrequency)

        self.upperFrequencyByte = int(frequency >> 8)
        self.lowerFrequencyByte = int(frequency & 0xFF)

    def calculateFrequency(self):
        """calculate the station frequency based upon the upper and lower bits read from the device"""

        frequency = (int(self.upperFrequencyByte) << 8) + int(self.lowerFrequencyByte)
        # Determine the current frequency using the same high side formula as above
        # self.FMstation = round(frequency * self.crystalOscillatorFrequency / 4 - 225000, 1) / 1000000

        # this is probably not the best way of doing this but I was having issues with the
        # frequency being off by as much as 1.5 MHz
        self.FMstation = round((float(round(int(frequency*self.crystalOscillatorFrequency/4-22500)/100000)/10)-.2)*10)/10

    def getTuned(self):
        with i2c.I2CMaster() as bus:
            results = bus.transaction(
                reading(self.address, self.numReadBytes)
            )
            elem = results[0][0]
            print("0 bits", int(get_bit(elem, 0)), int(get_bit(elem, 1)), int(get_bit(elem, 2)), int(get_bit(elem, 3)),
                  int(get_bit(elem, 4)), int(get_bit(elem, 5)), int(get_bit(elem, 6)), int(get_bit(elem, 7)))

            elem = results[0][1]
            print("1 bits", int(get_bit(elem, 0)), int(get_bit(elem, 1)), int(get_bit(elem, 2)), int(get_bit(elem, 3)),
                  int(get_bit(elem, 4)), int(get_bit(elem, 5)), int(get_bit(elem, 6)), int(get_bit(elem, 7)))

            elem = results[0][2]
            print("2 bits", int(get_bit(elem, 0)), int(get_bit(elem, 1)), int(get_bit(elem, 2)), int(get_bit(elem, 3)),
                  int(get_bit(elem, 4)), int(get_bit(elem, 5)), int(get_bit(elem, 6)), int(get_bit(elem, 7)))

            elem = results[0][3]
            print("3 bits", int(get_bit(elem, 0)), int(get_bit(elem, 1)), int(get_bit(elem, 2)), int(get_bit(elem, 3)),
                  int(get_bit(elem, 4)), int(get_bit(elem, 5)), int(get_bit(elem, 6)), int(get_bit(elem, 7)))

        return int(get_bit(elem, 7))

    def scan(self, direction):
        i = False
        fadd = 0
        softMute = 0

        self.readBytes()
        self.calculateByteFrequency()

        if direction == 1:
            fadd = 0.1
            self.FMstation = 87.5
        else:
            fadd = -0.1
            self.FMstation = 107.9

        f = open('telek.txt', 'w')

        while (i == False):

            print("FMstation1", self.FMstation)
            self.FMstation = self.FMstation + fadd

            if self.FMstation < 87.5:
                self.FMstation = 108
                i = True
            elif self.FMstation > 107.9:
                self.FMstation = 87.5
                i = True

            self.calculateByteFrequency()
            self.writeBytes()

            # give time to finish writing, and then read status
            sleep(0.2)

            self.readBytes()
            self.calculateByteFrequency()
            self.calculateFrequency()

            # print("FMstation2", self.FMstation)

            # print("Before tuning", self.getTuned())
            # tune into station that has strong signal only
            if self.levelADCoutput > 4:
                f.writelines(str(self.FMstation) + "FM (Strong " + str(self.stereoFlag) + " signal:" + str(self.levelADCoutput) + ")\n")
                print("Station found:", self.FMstation, "FM (Strong", self.stereoFlag, "signal:", self.levelADCoutput, ")")
            # else:
                # f.writelines(str(self.FMstation) + "FM (Weak " + str(self.stereoFlag) + " signal:" + str(self.levelADCoutput) + ")\n")

                # print("Station skipped:", self.FMstation, "FM (Weak", self.stereoFlag, "signal:", self.levelADCoutput, ")")

            # i = self.readyFlag

        f.close()
        # self.readyFlag = self.getTuned()
        # print("After tuning:", self.readyFlag)

    def off(self):
        print("Radio off")
        self.standby = 1
        self.writeBytes()
        self.display()
        return ("radio off")

    def search(self, dir):
        self.readyFlag = 0
        self.mute = 1
        self.searchMode = 1
        self.SUD = dir #1 or 0
        print("Station search " + dir)
        print(str(self.FMstation) + " MHz")
        self.writeBytes()

        while not self.readyFlag:
            sleep(0.5)
            self.readBytes()

            print("New: " + str(self.FMstation) + " MHz")
            if self.FMstation < 87.5 or self.FMstation > 107.9:
                self.searchMode = 0
                self.writeBytes()
                sleep(0.1)
                print("End of bandwith.")
                return False

        self.searchMode = 0
        self.mute = 0
        self.writeBytes()

        self.display()
        return ("Station search")

    def on(self):
        print("Radio on")
        self.standby = 0
        self.mute = 0
        self.writeBytes()
        self.display()
        return ("radio on")

    def mute(self):
        self.mute = not self.mute
        self.writeBytes()
        self.display()
        return ("radio muted")

    def display(self):
        """print out all of the information that we are able to collect from the device for debugging"""
        print("")
        print("               StandBy = " + str(self.standby))
        print("                  Mute = " + str(self.mute))
        print("            Ready Flag = " + str(self.readyFlag))
        print("       Band Limit Flag = " + str(self.bandLimitFlag))
        print("  Upper Frequency Byte = " + hex(self.upperFrequencyByte))
        print("  Lower Frequency Byte = " + hex(self.lowerFrequencyByte))
        print("           Stereo Flag = " + str(self.stereoFlag))
        print("     IF Counter Result = " + str(self.IFcounter))
        print("      Level ADC Output = " + str(self.levelADCoutput))
        print("               Chip ID = " + str(self.chipID))
        print("            FM Station = " + str(self.FMstation) + " MHz")

    def start(self):

        self.calculateByteFrequency()
        self.mute = 0
        self.standby = 0
        self.bandLimits = 0
        self.HCC = 1
        self.SNC = 1
        self.FMstation = 95.5
        self.writeBytes()

        # allow us to wait until the device is ready to get the correct information
        self.readyFlag = 0
        while (self.readyFlag == 0 and self.standby == 0):
            self.readBytes()
            sleep(0.25)

        # display the updated device information
        self.display()
        return ""


if __name__ == '__main__':
    radio = tea5767()

    print(sys.argv[1])

    if sys.argv[1] == 'off':
        radio.off()
    elif sys.argv[1] == 'on':
        radio.on()
    elif sys.argv[1] == 'scan':
        radio.scan(1)
    elif sys.argv[1] == 'search':
        radio.search(sys.argv[2])
    else:
        radio.start()
