# Serial read test for P1 Port
from tabulate import tabulate
from datetime import datetime
import crcmod.predefined
import traceback
import requests
import serial
import json
import uuid
import re
import os

# usb0 is used for connection with meter
PORT = "/dev/ttyUSB0"

# Meter baud rate is 115200 (bit/s)
BAUD_RATE = 115200

# Debug mode
DEBUG = True
PI_KEY = ""

SEND_URL = 'https://meterapiproject4.azurewebsites.net/api/MeterData'
GET_USER_METERS = 'https://meterapiproject4.azurewebsites.net/api/UserMeter'
GET_SEND_METERS = 'https://meterapiproject4.azurewebsites.net/api/Meter'
SEND_DATA = True
METER_ID = -1
METER_ID_DB = -1


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

OBIS_FOR_SEND = ["0-0:1.0.0", "1-0:1.8.1",
                 "1-0:1.8.2", "1-0:1.7.0", "0-1:24.2.3"]

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
    global METER_ID
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

                if "0-0:96.1.1" in obis:
                    METER_ID = value

                    if DEBUG:
                        print("\nSerial Number:", value)
                        print("")

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

# Send json object to Database


def sendData(obisOutput):
    global METER_ID, METER_ID_DB, SEND_URL

    if METER_ID_DB == -1:
        getDBMeterID()

    # Add required data to list
    sendObject = []

    for code in OBIS_FOR_SEND:
        # Find required obis codes
        found = list(
            filter(lambda x: x[0] == OBIS_CODES[code], obisOutput))
        sendObject.append(found)

    # Format Datetime
    dateString = str(int(sendObject[0][0][1]))
    formatDate = datetime.strptime(
        dateString, '%y%m%d%H%M%S')

    meterDataDTO = {
        "date":                     str(formatDate),
        "meterId":                  int(METER_ID_DB),
        "totalConsumptionDay":      float(sendObject[1][0][1]),
        "totalConsumptionNight":    float(sendObject[2][0][1]),
        "allPhaseConsumption":      float(sendObject[3][0][1]),
        "gasConsumption":           float(sendObject[4][0][1]),
    }

    if DEBUG:
        print(meterDataDTO)

    headers = {'Content-Type': 'application/json'}
    response = requests.post(
        SEND_URL, headers=headers, json=meterDataDTO, verify=True)

    if DEBUG:
        print(response.content)
        print(response.status_code)

    if response.status_code == 201:
        print("Data successfully submitted\n")
    elif response.status_code == 400:
        print("Error while trying to submit data\n")


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
                p1Telegram.extend(asciiLine.encode('ascii'))

                # Telegram always end with '!' character followed by a CRC
                if '!' in asciiLine:
                    if DEBUG:
                        print('*' * 40)
                        print(p1Telegram.decode('ascii').strip())
                        print('*' * 40)
                        print("\nEND!\n")

                    # Calculate CRC and compare with given
                    if checkCRC(p1Telegram):

                        if DEBUG:
                            print("CRC Matches, extracting data...\n\n")

                        # List for constructing our output
                        output = []

                        # Split over new line, every line contains different data
                        for line in p1Telegram.split(b'\n'):

                            # Extract our OBIS data
                            r = extractObisData(
                                line.decode('ascii'))

                            # Append data to our list if not empty
                            if r:
                                output.append(r)
                                if DEBUG:
                                    print(
                                        f"Desc: {r[0]}, val: {r[1]}, u:{r[2]}")

                        # Print nice table overview of our data
                        if DEBUG:
                            print(tabulate(output, headers=['Description', 'Value', 'Unit'],
                                           tablefmt='pretty'))

                        if SEND_DATA:
                            sendData(output)

                    else:
                        if DEBUG:
                            print("CRC DOESN'T MATCH")

            except Exception as e:
                print("EXCEPTION:", e)

                if DEBUG:
                    traceback.print_exc()

        except KeyboardInterrupt:
            # Close serial port for future use
            ser.close()
            print("CLOSING PROGRAM")

# Try to get meter id from database


def getDBMeterID():
    global METER_ID, GET_USER_METERS, PI_KEY, METER_ID_DB

    print("Trying to get METER ID...\n")

    if METER_ID != -1:
        response = requests.get(GET_USER_METERS)

        jsonObject = json.loads(response.content)

        # Find correct meter with METER_ID and PI_ID

        foundUserMeter = list(filter(lambda meter: meter['meterDeviceId'] == METER_ID and meter['rpId'] == PI_KEY, list(
            jsonObject)))

        if foundUserMeter != []:
            METER_ID_DB = foundUserMeter[0].get('meterId')

            if DEBUG:
                print("Meter ID in DB:", METER_ID_DB)
        else:
            # Meter not found, check if meter exists in DB
            resp = requests.get(GET_SEND_METERS)

            jsonObj = json.loads(resp.content)

            # Check for meter
            foundMeteter = list(
                filter(lambda meter: meter['meterDeviceId'] == METER_ID and meter['rpId'] == PI_KEY, list(jsonObj)))

            if foundMeteter != []:
                if DEBUG:
                    print("METER FOUND")
            else:
                if DEBUG:
                    print("NO METER YET")

                headers = {'Content-Type': 'application/json'}

                meterDTO = {
                    "rpId":             PI_KEY,
                    "meterDeviceId":    METER_ID
                }

                meterResp = requests.post(
                    GET_SEND_METERS, headers=headers, json=meterDTO)

                if meterResp.status_code == 201:
                    METER_ID_DB = json.loads(meterResp.content)['id']

                    if DEBUG:
                        print("SET METER ID DB", METER_ID_DB)

                if DEBUG:
                    print(meterResp.content)
                    print(meterResp.status_code)

# Try to find already defined uuid, if none were found create a new one


def createUUID():
    global PI_KEY

    mode = 'r+' if os.path.exists("./uuid.key") else 'w+'
    with open("uuid.key", mode) as keyFile:
        line = keyFile.readline()

        if len(line) > 0:
            PI_KEY = line
            print("Key found.\n\n")
        else:
            print("Creating key...\n\n")
            uid = str(uuid.uuid1())
            keyFile.writelines(uid)
            PI_KEY = uid


if __name__ == "__main__":
    # Setup
    createUUID()

    # Run main loop
    mainLoop()
