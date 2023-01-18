# Serial read test for P1 Port
import serial
import crcmod.predefined
import re
from tabulate import tabulate

# usb0 is used for connection with meter
PORT = "/dev/ttyUSB0"

# Meter baud rate is 115200 (bit/s)
BAUD_RATE = 115200

# Debug mode
DEBUG = True

# All OBIS codes with description
OBIS_CODES = {
    "0-0:96.1.4":   "ID",
    "0-0:96.1.1":   "Serial number of electricity meter (in ASCII hex)",
    "0-0:1.0.0":    "Timestamp of the telegram",
    "1-0:1.8.1":    "Rate 1 (day) - total consumption",
    "1-0:1.8.2":    "Rate 2 (night) - total consumption",
    "1-0:2.8.1":    "Rate 1 (day) - total production",
    "1-0:2.8.2":    "Rate 2 (night) - total production",
    "0-0:96.14.0":  "Current rate (1=day,2=night)",
    "1-0:1.7.0":    "All phases consumption",
    "1-0:2.7.0":    "All phases production",
    "1-0:21.7.0":   "L1 consumption",
    "1-0:41.7.0":   "L2 consumption",
    "1-0:61.7.0":   "L3 consumption",
    "1-0:22.7.0":   "L1 production",
    "1-0:42.7.0":   "L2 production",
    "1-0:62.7.0":   "L3 production",
    "1-0:32.7.0":   "L1 voltage",
    "1-0:52.7.0":   "L2 voltage",
    "1-0:72.7.0":   "L3 voltage",
    "1-0:31.7.0":   "L1 current",
    "1-0:51.7.0":   "L2 current",
    "1-0:71.7.0":   "L3 current",
    "0-0:96.3.10":  "Switch position electricity",
    "0-0:17.0.0":   "Max. allowed power/phase",
    "1-0:31.4.0":   "Max. allowed current/plase",
    "0-0:96.13.0":  "Message",
    "0-1:24.1.0":   "Other devices on bus",
    "0-1:96.1.1":   "Serial number of natural gas meter (in ASCII hex)",
    "0-1:24.4.0":   "Switch position natural gas",
    "0-1:24.2.3":   "Reading from natural gas meter (timestamp) (value)",
}

# Compare given CRC to calculated CRC


def checkCRC(p1Object):
    objectCRC = -1

    # Try to find the '!' character, CRC is right after '!'
    try:
        # Set index for use in calculation later
        crcIndex = p1Object.index(b'!')
        objectCRC = hex(
            int(p1Object[crcIndex + 1:].decode('ascii').strip(), 16))

    except ValueError as e:
        print("Cannot convert found CRC to Hex: {0}\n".format(e))

    # Couldn't find CRC
    if objectCRC == -1:
        raise IndexError('CRC not found in data.')

    # Calculate CRC manually

    # CRC is calculated from '/' char to '!' char
    crc16 = hex(crcmod.predefined.mkPredefinedCrcFun(
        'crc16')(p1Object[:crcIndex + 1]))

    if DEBUG:
        print("Calculated CRC:", crc16)
        print("Object CRC:", objectCRC)

    # CRC is valid
    if crc16 == objectCRC:
        return True

    # Invalid CRC
    return False

# Extract OBIS line from data


def extractObisData(telegramLine):
    unit = ""
    timestamp = ""

    if DEBUG:
        print(f"Parsing: {telegramLine}")

    # OBIS code and value is seperated by '(' character
    obis = telegramLine.split("(")[0]

    # Check our dict of OBIS codes
    if obis in OBIS_CODES:
        # Value is right after '(' char
        values = re.findall(r'\(.*?\)', telegramLine)
        value = values[0][1:-1]

        # Some values might be empty, skip those
        if len(value) > 0:

            #  Timestamps need the last char removed
            if obis == "0-0:1.0.0" or len(values) > 1:
                value = value[:-1]

            # Gas meter has more than one value, first one is timestamp
            if len(values) > 1:
                timestamp = value
                value = values[1][1:-1]

            # Parsing for serial number
            if "96.1.1" in obis:
                value = bytearray.fromhex(value).decode()
            else:
                lvalue = value.split("*")
                value = float(lvalue[0])

                if len(lvalue) > 1:
                    unit = lvalue[1]

            if DEBUG:
                print(
                    f"Description: {OBIS_CODES[obis]}, value:{value}, unit:{unit}\n")

            return (OBIS_CODES[obis], value, unit)
    else:
        return ()


def mainLoop():
    # Setup serial port, with specified BAUD_RATE
    ser = serial.Serial(PORT, BAUD_RATE, xonxoff=1)

    # Create bytearray for storing all values
    p1Telegram = bytearray()

    while True:
        try:
            try:
                # Read next line from serial input
                p1Line = ser.readline()

                # Decode line to ascii charset
                asciiLine = p1Line.decode('ascii')

                # Start of telegram is always a '/' character
                if '/' in asciiLine:
                    # Clear telegram for current transmission
                    p1Telegram = bytearray()

                    if DEBUG:
                        print("Beginning of telegram\n")

                # Add current line to our byte array, encoded as ascii
                p1Telegram.extend(asciiLine)

                # Telegram always end with '!' character followed by a CRC
                if '!' in asciiLine:
                    if DEBUG:
                        print('*' * 40)
                        print(p1Telegram.strip())
                        print('*' * 40)
                        print("\nEND!\n")

                    # Calculate CRC and compare with given
                    if checkCRC(p1Telegram):
                        print("CRC Matches, extracting data...\n\n")

                        # List for constructing our output
                        output = []

                        # Split over new line, every line contains different data
                        for lineResponse in p1Telegram.split(b'\n'):

                            # Extract our OBIS data
                            lineResponse = extractObisData(p1Telegram)

                            # Append data to our list if not empty
                            if lineResponse:
                                output.append(lineResponse)
                                if DEBUG:
                                    print(
                                        f"Desc: {lineResponse[0]}, val: {lineResponse[1]}, u:{lineResponse[2]}")

                        # Print nice table overview of our data
                        print(tabulate(output, headers=['Description', 'Value', 'Unit'],
                                       tablefmt='pretty'))
                    else:
                        if DEBUG:
                            print("CRC DOESN'T MATCH")

            except Exception as e:
                print("EXCEPTION:", e)
        except KeyboardInterrupt:
            # Close serial port for future use
            ser.close()
            print("CLOSING PROGRAM")


if __name__ == "__main__":
    mainLoop()
