from time import sleep
from i2c.i2c import I2C


class SPS30:

    def __init__(self,  bus:int = 1, address:int = 0x69):
        
        self.i2c = I2C(bus, address)
        self.pm_data = {
            "mass_density": {
                "pm1.0": 0.0,
                "pm2.5": 0.0,
                "pm4.0": 0.0,
                "pm10": 0.0
            },
            "particle_count": {

            }
        }

    def crc_calc(self, data: list):
        crc = 0xFF
        for i in range(2):
            crc ^= data[i]
            for _ in range(8, 0, -1):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        
        # The checksum only contains 8-bit, 
        # so the calculated value has to be masked with 0xFF
        return (crc & 0x0000FF)

    def firmware_version(self) -> str:
        self.i2c.write([0xD1, 0x00])
        data = self.i2c.read(3)

        if self.crc_calc(data[:2]) != data[2]:
            return "CRC mismatched"

        return ".".join(map(str, data[:2]))
    
    def product_type(self) -> str:
        self.i2c.write([0xD0, 0x02])
        data = self.i2c.read(12)
        result = ""

        for i in range(0, 12, 3):
            if self.crc_calc(data[i:i+2]) != data[i+2]:
                return "CRC mismatched"
            
            result += "".join(map(chr, data[i:i+2]))

        return result
    
    def serial_number(self) -> str:
        self.i2c.write([0xD0, 0x33])
        data = self.i2c.read(48)
        result = ""

        for i in range(0, 48, 3):
            if self.crc_calc(data[i:i+2]) != data[i+2]:
                return "CRC mismatched"
            
            result += "".join(map(chr, data[i:i+2]))

        return result

    def stop(self):
        self.i2c.close()
