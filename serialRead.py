# Serial read testfor P1 Port
import serial

PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

if __name__ == "__main__":
    ser = serial.Serial(PORT, BAUD_RATE, xonxoff=1)

    while True:
        try:
            try:
                p1Line = ser.readline()

                if '/' in p1Line.decode('ascii'):
                    print("Beginning of telegram\n")
                elif '!' in p1Line.decode('ascii'):
                    print("\nEND!\n\n")
                else:
                    print(p1Line.decode('ascii'))

            except Exception as e:
                print("EXCEPTION:", e)
        except KeyboardInterrupt:
            ser.close()
            print("CLOSING PROGRAM")
