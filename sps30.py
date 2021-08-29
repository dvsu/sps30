import sys
import threading
import logging
from time import sleep
from queue import Queue
from i2c.i2c import I2C


class SPS30:

    def __init__(self,  bus: int = 1, address: int = 0x69, sampling_period: int = 1, logger: str = None):
        self.logger = None
        if logger:
            self.logger = logging.getLogger(logger)

        self.sampling_period = sampling_period
        self.i2c = I2C(bus, address)
        self.__data = Queue(maxsize=20)
        self.__valid = {
            "mass_density": False,
            "particle_count": False,
            "particle_size": False
        }

    def crc_calc(self, data: list) -> int:
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

    def read_auto_cleaning_interval(self) -> int:
        self.i2c.write([0x80, 0x04])
        data = self.i2c.read(6)

        interval = []
        for i in range(0, 6, 3):
            if self.crc_calc(data[i:i+2]) != data[i+2]:
                return "CRC mismatched"

            interval.extend(data[i:i+2])

        return (interval[0] << 24 | interval[1] << 16 | interval[2] << 8 | interval[3])

    def read_status_register(self) -> dict:
        self.i2c.write([0xD2, 0x06])
        data = self.i2c.read(6)

        status = []
        for i in range(0, 6, 3):
            if self.crc_calc(data[i:i+2]) != data[i+2]:
                return "CRC mismatched"

            status.extend(data[i:i+2])

        binary = '{:032b}'.format(
            status[0] << 24 | status[1] << 16 | status[2] << 8 | status[3])
        speed_status = "too high/ too low" if int(binary[10]) == 1 else "ok"
        laser_status = "out of range" if int(binary[26]) == 1 else "ok"
        fan_status = "0 rpm" if int(binary[27]) == 1 else "ok"

        return {
            "speed_status": speed_status,
            "laser_status": laser_status,
            "fan_status": fan_status
        }

    def clear_status_register(self) -> None:
        self.i2c.write([0xD2, 0x10])

    def read_data_ready_flag(self) -> bool:
        self.i2c.write([0x02, 0x02])
        data = self.i2c.read(3)

        if self.crc_calc(data[:2]) != data[2]:
            if self.logger:
                self.logger.warning(
                    "'read_data_ready_flag' CRC mismatched!" +
                    f"  Data: {data[:2]}" +
                    f"  Calculated CRC: {self.crc_calc(data[:2])}" +
                    f"  Expected: {data[2]}")
            else:
                print(
                    "'read_data_ready_flag' CRC mismatched!" +
                    f"  Data: {data[:2]}" +
                    f"  Calculated CRC: {self.crc_calc(data[:2])}" +
                    f"  Expected: {data[2]}")

            return False

        return True if data[1] == 1 else False

    def wakeup(self) -> None:
        self.i2c.write([0x11, 0x03])

    def reset(self) -> None:
        self.i2c.write([0xD3, 0x04])

    def __ieee754_number_conversion(self, data: int) -> float:
        binary = "{:032b}".format(data)

        sign = int(binary[0:1])
        exp = int(binary[1:9], 2) - 127
        exp = 0 if exp < 0 else exp
        mantissa = binary[9:]

        real = int(('1' + mantissa[:exp]), 2)
        decimal = mantissa[exp:]

        dec = 0.0
        for i in range(len(decimal)):
            dec += int(decimal[i]) / (2**(i+1))

        return round((((-1)**(sign) * real) + dec), 3)

    def __mass_density_measurement(self, data: list) -> dict:
        category = ["pm1.0", "pm2.5", "pm4.0", "pm10"]

        density = {
            "pm1.0": 0.0,
            "pm2.5": 0.0,
            "pm4.0": 0.0,
            "pm10": 0.0
        }

        for block, (pm) in enumerate(category):
            pm_data = []
            for i in range(0, 6, 3):
                offset = (block*6)+i
                if self.crc_calc(data[offset:offset+2]) != data[offset+2]:
                    if self.logger:
                        self.logger.warning(
                            "'__mass_density_measurement' CRC mismatched!" +
                            f"  Data: {data[offset:offset+2]}" +
                            f"  Calculated CRC: {self.crc_calc(data[offset:offset+2])}" +
                            f"  Expected: {data[offset+2]}")
                    else:
                        print(
                            "'__mass_density_measurement' CRC mismatched!" +
                            f"  Data: {data[offset:offset+2]}" +
                            f"  Calculated CRC: {self.crc_calc(data[offset:offset+2])}" +
                            f"  Expected: {data[offset+2]}")
                    self.__valid["mass_density"] = False
                    return {}

                pm_data.extend(data[offset:offset+2])

            density[pm] = self.__ieee754_number_conversion(
                pm_data[0] << 24 | pm_data[1] << 16 | pm_data[2] << 8 | pm_data[3])

        self.__valid["mass_density"] = True

        return density

    def __particle_count_measurement(self, data: list) -> dict:
        category = ["pm0.5", "pm1.0", "pm2.5", "pm4.0", "pm10"]

        count = {
            "pm0.5": 0.0,
            "pm1.0": 0.0,
            "pm2.5": 0.0,
            "pm4.0": 0.0,
            "pm10": 0.0
        }

        for block, (pm) in enumerate(category):
            pm_data = []
            for i in range(0, 6, 3):
                offset = (block*6)+i
                if self.crc_calc(data[offset:offset+2]) != data[offset+2]:
                    if self.logger:
                        self.logger.warning(
                            "'__particle_count_measurement' CRC mismatched!" +
                            f"  Data: {data[offset:offset+2]}" +
                            f"  Calculated CRC: {self.crc_calc(data[offset:offset+2])}" +
                            f"  Expected: {data[offset+2]}")
                    else:
                        print(
                            "'__particle_count_measurement' CRC mismatched!" +
                            f"  Data: {data[offset:offset+2]}" +
                            f"  Calculated CRC: {self.crc_calc(data[offset:offset+2])}" +
                            f"  Expected: {data[offset+2]}")

                    self.__valid["particle_count"] = False
                    return {}

                pm_data.extend(data[offset:offset+2])

            count[pm] = self.__ieee754_number_conversion(
                pm_data[0] << 24 | pm_data[1] << 16 | pm_data[2] << 8 | pm_data[3])

        self.__valid["particle_count"] = True

        return count

    def __particle_size_measurement(self, data: list) -> float:
        size = []
        for i in range(0, 6, 3):
            if self.crc_calc(data[i:i+2]) != data[i+2]:
                if self.logger:
                    self.logger.warning(
                        "'__particle_size_measurement' CRC mismatched!" +
                        f"  Data: {data[i:i+2]}" +
                        f"  Calculated CRC: {self.crc_calc(data[i:i+2])}" +
                        f"  Expected: {data[i+2]}")
                else:
                    print(
                        "'__particle_size_measurement' CRC mismatched!" +
                        f"  Data: {data[i:i+2]}" +
                        f"  Calculated CRC: {self.crc_calc(data[i:i+2])}" +
                        f"  Expected: {data[i+2]}")

                self.__valid["particle_size"] = False
                return 0.0

            size.extend(data[i:i+2])

        self.__valid["particle_size"] = True

        return self.__ieee754_number_conversion(size[0] << 24 | size[1] << 16 | size[2] << 8 | size[3])

    def __read_sensor_data(self) -> None:
        while True:
            try:
                if not self.read_data_ready_flag():
                    continue

                self.i2c.write([0x03, 0x00])
                data = self.i2c.read(60)

                if self.__data.full():
                    self.__data.get()

                result = {
                    "mass_density": self.__mass_density_measurement(data[:24]),
                    "particle_count": self.__particle_count_measurement(data[24:54]),
                    "particle_size": self.__particle_size_measurement(data[54:]),
                    "mass_density_unit": "ug/m3",
                    "particle_count_unit": "#/cm3",
                    "particle_size_unit": "um"
                }

                self.__data.put(result if all(self.__valid.values()) else {})

            except KeyboardInterrupt:
                if self.logger:
                    self.logger.warning("Stopping measurement...")
                else:
                    print("Stopping measurement...")

                self.stop_measurement()
                sys.exit()

            except Exception as e:
                if self.logger:
                    self.logger.warning(f"{type(e).__name__}: {e}")
                else:
                    print(f"{type(e).__name__}: {e}")

            finally:
                sleep(self.sampling_period)

    def start_measurement(self) -> None:
        data_format = {
            "IEEE754_float": 0x03,
            "unsigned_16_bit_integer": 0x05
        }

        data = [0x00, 0x10]
        data.extend([data_format["IEEE754_float"], 0x00])
        data.append(self.crc_calc(data[2:4]))
        self.i2c.write(data)
        sleep(0.05)
        self.__run()

    def get_measurement(self) -> dict:
        if self.__data.empty():
            return {}

        return self.__data.get()

    def stop_measurement(self) -> None:
        self.i2c.write([0x01, 0x04])
        self.i2c.close()

    def __run(self) -> None:
        threading.Thread(target=self.__read_sensor_data, daemon=True).start()
