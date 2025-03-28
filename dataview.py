class DataView:
    def __init__(self, data):
        self.data = data

    def getUint8(self, offset):
        return self.data[offset]

    def getUint16(self, offset, endian=False):
        b1 = self.data[offset]
        b2 = self.data[offset + 1]
        if endian:
            return (b2 << 8) | b1   # little-endian
        else:
            return (b1 << 8) | b2   # big-endian

    def getUint32(self, offset, endian=False):
        b1 = self.data[offset]
        b2 = self.data[offset + 1]
        b3 = self.data[offset + 2]
        b4 = self.data[offset + 3]
        if endian:
            return ((b4 << 8) | b3) | ((b2 << 8) | b1)   # little-endian
        else:
            return (b1 << 24) | (b2 << 16) | (b3 << 8) | b4   # big-endian
