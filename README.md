# Sensirion SPS30

## Introduction

Python-based driver for [Sensirion SPS30](https://www.sensirion.com/en/environmental-sensors/particulate-matter-sensors-pm25/) particulate matter sensor. Tested on Raspberry Pi Zero/Zero W/3B+/4B.

### Wiring

#### Sensor

```none
                                 Pin 1   Pin 5
                                   |       |
                                   V       V
.------------------------------------------------.
|                                .-----------.   |
|                                | x x x x x |   |
|                                '-----------'   |
|     []          []          []          []     |
'------------------------------------------------'
```

| Pin | Description                                       | UART | I2C |
| :-: | :------------------------------------------------ | ---- | --- |
|  1  | Supply voltage 5V                                 | VDD  | VDD |
|  2  | UART receiving pin/ I2C serial data input/ output | RX   | SDA |
|  3  | UART transmitting pin/ I2C serial clock input     | TX   | SCL |
|  4  | Interface select (UART: floating (NC) /I2C: GND)  | NC   | GND |
|  5  | Ground                                            | GND  | GND |

#### I2C Interface

```none
  Sensor Pins                                 Raspberry Pi Pins
.-------.-----.                             .----------.---------.
| Pin 1 | VDD |-----------------------------|    5V    | Pin 2/4 |
| Pin 2 | SDA |-----------------------------| I2C1 SDA |  Pin 3  |
| Pin 3 | SCL |-----------------------------| I2C1 SCL |  Pin 5  |
| Pin 4 | GND |-----.                       |          |         |
| Pin 5 | GND |-----'-----------------------|   GND    | Pin 6/9 |
'-------'-----'                             '----------'---------'
```

### Example

Default parameters of `SPS30` class

| Parameter | Value | Description             |
| --------- | ----- | ----------------------- |
| bus       | 1     | I2C bus of Raspberry Pi |
| address   | 0x69  | Default I2C address     |

```python
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
```

### Output data format

```json
{
  "sensor_data": {
    "mass_density": {
      "pm1.0": 1.883,
      "pm2.5": 3.889,
      "pm4.0": 6.232,
      "pm10": 6.7
    },
    "particle_count": {
      "pm0.5": 1.302,
      "pm1.0": 4.595,
      "pm2.5": 7.326,
      "pm4.0": 7.864,
      "pm10": 7.967
    },
    "particle_size": 1.63,
    "mass_density_unit": "ug/m3",
    "particle_count_unit": "#/cm3",
    "particle_size_unit": "um"
  },
  "timestamp": 1630217804
}
```

### Dependencies

None
