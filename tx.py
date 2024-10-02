import os
import struct
from digi.xbee.devices import XBeeDevice, XBee64BitAddress, RemoteXBeeDevice, PowerLevel
import time
import cv2

# XBee device configuration
PORT = "COM6"  # Change this to your XBee COM port
BAUD_RATE = 9600
TIMEOUT_FOR_SYNC_OPERATIONS = 5 # 5 seconds

# Initialize XBee device
dest_address = XBee64BitAddress.from_hex_string("0013A200422B127D")
device = XBeeDevice(PORT, BAUD_RATE)

"""
Radio	                                Payload Size
====================================================
802.15.4/ XBee	                        94 Bytes
XTend	                                2048 Bytes
XTC (Xtend Compatible) and SX products	2048 Bytes
900 HP 	                                256 Bytes
"""
CHUNK_SIZE = 255  # Set chunk size (in bytes)

# Timeout and retry settings
ACK_TIMEOUT = 5  # Timeout in seconds to wait for ACK
MAX_RETRIES = 3  # Max number of retries before giving up

def read_image_to_bytes(image_path):
    """
    Reads an image using OpenCV and returns its byte array.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Image at path {image_path} could not be read.")
    # Use the cvtColor() function to grayscale the image
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Downsample the image (reduce the size by half)
    downsampled_image = cv2.pyrDown(gray_image)
    _, buffer = cv2.imencode('.jpg', downsampled_image)
    return buffer.tobytes()


def split_bytes(data, chunk_size):
    """
    Splits a byte array into chunks of specified size.
    """
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

def wait_for_ack(device, expected_frame_counter):
    """
    Wait for an acknowledgment with the expected frame counter.
    """
    start_time = time.time()

    while time.time() - start_time < ACK_TIMEOUT:
        xbee_message = device.read_data(timeout=ACK_TIMEOUT)

        if xbee_message:
            ack_frame_counter, = struct.unpack('>I', xbee_message.data)
            if ack_frame_counter == expected_frame_counter:
                return True

    return False

def send_image(image_path, device):
    """
    Reads an image, splits it into chunks, and sends each chunk using XBee.
    """
    try:
        # Open device
        device.open()
        device.set_power_level(PowerLevel.LEVEL_HIGHEST)  # Set power level to lowest, [0, 4]
        device.set_sync_ops_timeout(TIMEOUT_FOR_SYNC_OPERATIONS)
        # Configure the Node ID using 'set_parameter' method.
        device.set_parameter("DO", bytearray([16]))

        remote = RemoteXBeeDevice(device, dest_address)

        # Read image file to bytes
        image_bytes = read_image_to_bytes(image_path)
        chunks = split_bytes(image_bytes, CHUNK_SIZE - 8)  # Subtract 4 bytes for frame counter

        # Send each chunk
        frame_counter = 0  # Frame counter (incremental)
        chunk_count = len(chunks)
        while frame_counter < chunk_count:
            try:

                chunk = chunks[frame_counter]
                payload = struct.pack('>I', frame_counter) + struct.pack('>I', chunk_count) + chunk
                
                # Attempt to send the chunk and wait for ACK
                for attempt in range(MAX_RETRIES):
                    print(f"Sending chunk {frame_counter + 1}/{chunk_count} with frame counter: {frame_counter}")
                    device.send_data(remote, payload)

                    # Wait for the acknowledgment
                    ack = wait_for_ack(device, frame_counter)
                    if ack:
                        # print(f"ACK received for frame {frame_counter}.")
                        break
                    else:
                        print(f"Retry {attempt + 1} for frame {frame_counter}...")
                        if attempt == MAX_RETRIES - 1:
                            raise Exception("Max retries reached.")

                    time.sleep(ACK_TIMEOUT)

                frame_counter += 1
            except KeyboardInterrupt:
                print("Transmission interrupted.")
                break
            except Exception as e:
                print(f"Error: {e}")
                break
        
        if frame_counter == chunk_count:
            print("Image sent successfully!")
        else:
            print(f"Image transmission failed. Only {frame_counter} out of {chunk_count} chunks sent.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if device.is_open():
            device.close()


if __name__ == "__main__":
    image_path = "input/flower.jpg"
    send_image(image_path, device)
