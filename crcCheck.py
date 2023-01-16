import crcmod.predefined


def checkCRC():
    crc16 = crcmod.predefined.mkCrcFun('crc-16')
    calcCrc = hex(crc16(('test').encode('utf-8')))
    print(calcCrc)


checkCRC()
