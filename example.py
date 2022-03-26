import sys
import json
from time import sleep
from sps30 import SPS30


if __name__ == "__main__":
    pm_sensor = SPS30()
    print(f"Firmware version: {pm_sensor.firmware_version()}")
    print(f"Product type: {pm_sensor.product_type()}")
    print(f"Serial number: {pm_sensor.serial_number()}")
    print(f"Status register: {pm_sensor.read_status_register()}")
    print(
        f"Auto cleaning interval: {pm_sensor.read_auto_cleaning_interval()}s")
    print(f"Set auto cleaning interval: {pm_sensor.write_auto_cleaning_interval_days(2)}s")
    pm_sensor.start_measurement()

    while True:
        try:
            print(json.dumps(pm_sensor.get_measurement(), indent=2))
            sleep(2)

        except KeyboardInterrupt:
            print("Stopping measurement...")
            pm_sensor.stop_measurement()
            sys.exit()
