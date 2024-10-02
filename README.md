# Camera XBee Pro

This project is designed to receive and process image data from remote devices using XBee modules. The received data is saved as images on the local filesystem.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Device Setup](#device-setup)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)

## Features

- Easy setup and configuration
- Basic communication examples

## Requirements

- XBee Pro module
- XBee USB adapter or equivalent
- Python 3.x
- `PySerial` library
- XBee Python library software
- [XCTU](http://www.digi.com/xctu)

## Device Setup

1. **Ensure API Firmware**: For old Zigbee devices (S2 and S2B), ensure they are using API firmware. This can be verified in the Function label of the device in the Radio Modules view.
    - One device must be a coordinator - Function: Zigbee Coordinator API.
    - It is recommended that the other device is a router - Function: Zigbee Router API.

    > **Note**: If these conditions are not met, update the firmware of the device by clicking the Update firmware button in the Radio Configuration toolbar.

2. **Load Default Firmware Settings**: Click the Load default firmware settings button in the Radio Configuration toolbar to load the default values for the device firmware.

3. **Configure Device Parameters**:
    - Set the AP parameter to 1 (API mode without escapes) or 2 (API mode with escapes).
    - Set the CE parameter to Enabled for the coordinator.

4. **Set PAN ID**: Configure the ID (PAN ID) setting to `C001BEE`.

5. **Set Scan Channels**: Configure the SC (Scan Channels) setting to `FFF`.

6. **Write Radio Settings**: Click the Write radio settings button in the Radio Configuration toolbar to apply the new values to the module.

7. **Verify Connectivity**: Once both modules are configured, ensure they can see each other by clicking Discover radio modules in the same network, the second button in the device panel of the Radio Modules view. The other device should be listed in the Discovering remote devices dialog.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/ysasiwat/simple-xbee-pro.git
    cd simple-xbee-pro
    ```

2. Install the required Python libraries:
    ```sh
    pip install PySerial
    pip install -r requirements.txt
    ```

## Usage

1. Connect your XBee Pro module to your computer using the USB adapter.
2. Open a terminal and run the `rx.py` script to start receiving data:
    ```sh
    python rx.py
    ```
3. Open a new terminal if you are using the same machine for both sending and receiving data.
4. Run the `tx.py` script in the new terminal to start sending data:
    ```sh
    python tx.py
    ```

## Documentation

For more detailed information, please refer to the [XBee Python library documentation](https://xbplib.readthedocs.io/en/latest/index.html).