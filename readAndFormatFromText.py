

# Serial read test for P1 Port
import crcmod.predefined
import re
from tabulate import tabulate

PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

DEBUG = True

obisCodes = {
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


def checkCRC(p1Object):
    # return True
    crcIndex = -1

    try:
        crcIndex = p1Object.index(b'!')
        objectCRC = hex(
            int(p1Object[crcIndex + 1:].decode('ascii').strip(), 16))
    except ValueError as e:
        print("Cannot convert found CRC to Hex: {0}\n".format(e))

    if objectCRC == -1:
        return False

    # Calculate CRC
    p1Object = p1Object[:crcIndex + 1]

    print(p1Object)

    # print("OBJ", p1Object)
    crc16 = hex(crcmod.predefined.mkPredefinedCrcFun(
        'crc16')(p1Object))

    print("Calculated CRC:", crc16)
    print("Object CRC:", objectCRC)

    if crc16 == objectCRC:
        return True

    return False


def extractObisData(telegramLine):
    unit = ""
    timestamp = ""

    if DEBUG:
        print(f"Parsing: {telegramLine}")

    # Obis code and value are seperated by (
    obis = telegramLine.split("(")[0]

    # Check known obis codes
    if obis in obisCodes:
        values = re.findall(r'\(.*?\)', telegramLine)
        value = values[0][1:-1]

        if len(value) > 0:

            # Timestamp needs last character removed
            if obis == "0-0:1.0.0" or len(values) > 1:
                value = value[:-1]

            # Connected gasmeter
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
                    f"Description: {obisCodes[obis]}, value:{value}, unit:{unit}\n")

            return (obisCodes[obis], value, unit)
    else:
        return ()


def main():
    with open('obisExample.txt') as f:
        # lines
        # ser = serial.Serial(PORT, BAUD_RATE, xonxoff=1)
        p1Telegram = bytearray()

        for line in f:
            try:
                try:
                    p1Line = line

                    asciiLine = p1Line

                    if '/' in asciiLine:
                        p1Telegram = bytearray()

                        if DEBUG:
                            print("Beginning of telegram\n")

                    p1Telegram.extend(asciiLine.encode('ascii'))

                    if '!' in asciiLine:
                        if DEBUG:
                            print('*' * 40)
                            print(p1Telegram.decode('ascii').strip())
                            print('*' * 40)
                            print("\nEND!\n")

                        if checkCRC(p1Telegram):
                            print("Checksum Matches, extracting data...\n\n")
                            output = []
                            for line in p1Telegram.split(b'\n'):
                                r = extractObisData(line.decode('ascii'))
                                if r:
                                    output.append(r)
                                    if DEBUG:
                                        print(
                                            f"Desc: {r[0]}, val:{r[1]}, u:{r[2]}")
                            print(tabulate(output, headers=['Description', 'Value', 'Unit'],
                                           tablefmt='pretty'))
                        else:
                            if DEBUG:
                                print("CHECKSUM DOESN'T MATCH")

                except Exception as e:
                    print("EXCEPTION:", e)
            except KeyboardInterrupt:
                print("CLOSING PROGRAM")


if __name__ == "__main__":
    main()
