# Serial read test for P1 Port
import serial
import crcmod.predefined
import re

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
    objectCRC = -1

    # Get CRC
    for match in re.compile(b'\r\n(?=!)').finditer(p1Object):
        p1Contents = p1Object[:match.end() + 1].decode('ascii').strip()

        objectCRC = hex(int(p1Contents, 16))

    if objectCRC == -1:
        return False

    # Calculate CRC
    crc16 = crcmod.predefined.mkCrcFun('crc-16')
    calcCrc = hex(crc16((p1Object).encode('utf-8')))
    print("Calculated CRC:", calcCrc)
    print("Object CRC:", objectCRC)

    if calcCrc == objectCRC:
        return True

    return False


def extractObisData(telegram):
    pass


def main():
    ser = serial.Serial(PORT, BAUD_RATE, xonxoff=1)
    p1Telegram = bytearray()

    while True:
        try:
            try:
                p1Line = ser.readline()

                asciiLine = p1Line.decode('ascii')

                if '/' in asciiLine:
                    p1Telegram = bytearray()

                    if DEBUG:
                        print("Beginning of telegram\n")

                elif '!' in asciiLine:
                    if DEBUG:
                        print("\nEND!\n")
                        print('*' * 40)
                        print(p1Telegram.strip())
                        print('*' * 40)

                    if checkCRC(p1Telegram):
                        print("Checksum Matches, extracting data...")
                        extractObisData(p1Telegram)
                    else:
                        if DEBUG:
                            print("CHECKSUM DOESN'T MATCH")

                else:
                    p1Telegram.extend(asciiLine)

            except Exception as e:
                print("EXCEPTION:", e)
        except KeyboardInterrupt:
            ser.close()
            print("CLOSING PROGRAM")


if __name__ == "__main__":
    main()
