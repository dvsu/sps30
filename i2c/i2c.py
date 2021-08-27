import io
from fcntl import ioctl


class I2C:

    I2C_SLAVE = 0x0703

    def __init__(self, bus: int, address: int):

        self.fr = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.fw = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

        # set device address
        ioctl(self.fr, self.I2C_SLAVE, address)
        ioctl(self.fw, self.I2C_SLAVE, address)

    def write(self, data: list):
        self.fw.write(bytearray(data))

    def read(self, nbytes: int) -> list:
        return list(self.fr.read(nbytes))

    def close(self):
        self.fw.close()
        self.fr.close()
