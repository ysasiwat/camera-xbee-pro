import struct
import sys
import time
from digi.xbee.devices import XBeeDevice, XBee64BitAddress, RemoteXBeeDevice, PowerLevel
import threading
import atexit
import os
import cv2
import numpy as np

# XBee device configuration
PORT = "COM5"  # Change this to your XBee COM port
BAUD_RATE = 9600
TIMEOUT_FOR_SYNC_OPERATIONS = 5  # 5 seconds
OUTPUT_IMAGE = "output"

# Initialize XBee device
src_address = XBee64BitAddress.from_hex_string("0013A200422B138D")
device = XBeeDevice(PORT, BAUD_RATE)

received_data = {}  # To store received data

def save_image(data, output_path):
    """
    Saves the received byte data as an image.
    """
    # Convert the byte data to a NumPy array
    nparr = np.frombuffer(data, np.uint8)

    grey_image = cv2.imdecode(nparr, cv2.COLOR_BGR2GRAY)

    # Upsample the image to 200% of its original size
    upsampled_image = cv2.resize(grey_image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)

    # Check if the image was loaded successfully
    if upsampled_image is not None:
        # Save the image to a file
        cv2.imwrite(output_path, upsampled_image)
        print("Image saved successfully!")
    else:
        print("Failed to decode image from byte data.")


def data_receive_callback(xbee_message):
    """
    Callback to handle incoming data and append it to the received_data.
    """
    global received_data
    payload = xbee_message.data
    remote_device = xbee_message.remote_device

    #  str(remote_device).split(" ")[0]

    # print(f"Received data from {remote_device}")

    # Unpack the frame counter (first 4 bytes of the payload)
    (frame_counter,) = struct.unpack(">I", payload[:4])
    (frame_counter_end,) = struct.unpack(">I", payload[4:8])
    chunk = payload[8:]  # The rest is the image data

    # print(f"Received chunk of size {len(xbee_message.data)}")
    # print(f"Received chunk with frame counter: {frame_counter}")
    # print(f"Received chunk with frame counter end: {frame_counter_end}")
    # print(f"Received chunk at {xbee_message.timestamp}")

    if remote_device not in received_data:
        # print("New device detected. Initializing data.")
        received_data[remote_device] = {
            "frame_counter": -1,
            "frame_counter_end": frame_counter_end - 1,
            "data": b"",
            "timestamp": -1,
        }

    if received_data[remote_device]["frame_counter"] == received_data[remote_device]["frame_counter_end"]:
        # print("All chunks received. Discarding new chunk.")
        return

    if frame_counter != received_data[remote_device]["frame_counter"] + 1:
        # print("Frame counter mismatch. Discarding chunk.")
        # print(
        #     f"Expected: {received_data[remote_device]['frame_counter'] + 1}, Received: {frame_counter}"
        # )
        del received_data[remote_device]
        return

    received_data[remote_device]["frame_counter"] = frame_counter
    received_data[remote_device]["data"] += chunk
    received_data[remote_device]["timestamp"] = xbee_message.timestamp

    send_ack(remote_device, frame_counter)

def send_ack(dst_address, frame_counter):
    """
    Sends an acknowledgment back to the sender with the frame counter.
    """
    remote_device = RemoteXBeeDevice(device, dst_address.get_64bit_addr())
    ack_payload = struct.pack('>I', frame_counter)
    # print(f"Sending ACK for frame {frame_counter}")
    device.send_data(remote_device, ack_payload)

def receive_image(device):
    """
    Waits for image data to be received and saves it once completed.
    """
    try:
        # Open the device
        device.open()
        device.set_power_level(
            PowerLevel.LEVEL_HIGHEST
        )  # Set power level to lowest, [0, 4]
        device.set_sync_ops_timeout(TIMEOUT_FOR_SYNC_OPERATIONS)
        device.set_parameter("DO", bytearray([16]))

        # remote = RemoteXBeeDevice(device, src_address)

        # Set callback to handle incoming data
        device.add_data_received_callback(data_receive_callback)
        print("Waiting for data...")

        # Wait to receive all data (adjust the timeout based on expected transmission time)
        while True:
            time.sleep(1)

        # Save the complete image
        # save_image(received_data, OUTPUT_IMAGE)
    except KeyboardInterrupt as e:
        print("KeyboardInterrupt detected.")
    finally:
        print("Exit and Closing device.")
        if device.is_open():
            device.close()


class DataCleanupService(threading.Thread):
    def __init__(self, interval, timeout):
        super().__init__()
        self.interval = interval
        self.timeout = timeout
        self.running = True

    def run(self):
        while self.running:
            current_time = time.time()
            for remote_device in list(received_data.keys()):
                if received_data[remote_device]["timestamp"] != -1 and (
                    current_time - received_data[remote_device]["timestamp"]
                    > self.timeout
                ):
                    print(f"Removing data for {remote_device} due to timeout.")
                    del received_data[remote_device]
            time.sleep(self.interval)

    def stop(self):
        self.running = False


class DataStoreService(threading.Thread):
    def __init__(self, interval, output_path):
        super().__init__()
        self.interval = interval
        self.running = True
        self.output_path = output_path

    def run(self):
        while self.running:
            for remote_device in list(received_data.keys()):
                if (
                    received_data[remote_device]["frame_counter"]
                    == received_data[remote_device]["frame_counter_end"]
                ):
                    print(f"{remote_device} All chunks received.")
                    directory_name = str(remote_device.get_64bit_addr())
                    # Create directory if it doesn't exist
                    directory_path = os.path.join(self.output_path, directory_name)
                    if not os.path.exists(directory_path):
                        os.makedirs(directory_path)

                    filename = f"{time.strftime('%Y%m%d%H%M%S')}.jpg"
                    save_image(
                        received_data[remote_device]["data"],
                        os.path.join(directory_path, filename),
                    )
                    del received_data[remote_device]
            time.sleep(self.interval)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    try:
        # Start the data cleanup service
        cleanup_service = DataCleanupService(interval=5, timeout=15)
        auto_store_service = DataStoreService(interval=5, output_path=OUTPUT_IMAGE)

        cleanup_service.start()
        auto_store_service.start()

        receive_image(device)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup_service.stop()
        auto_store_service.stop()
        cleanup_service.join()
        auto_store_service.join()
