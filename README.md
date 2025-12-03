# uboto3

`uboto3` is a MicroPython library designed to facilitate uploading files directly from a MicroPython-enabled device (like an ESP32 or ESP8266) to Amazon Web Services (AWS) S3 or to a S3-compatible provider. It implements the necessary AWS Signature Version 4 for an S3 PUT Object request. This allows you to store data, sensor readings, images, or any other files from your microcontroller projects in the cloud.

## Features

* **Direct S3 Upload:** Upload files directly to an S3 bucket without needing an intermediary server.
* **AWS Signature V4:** Implements the required request signing process.
* **HMAC-SHA256:** Includes a MicroPython-compatible HMAC-SHA256 implementation for signing.
* **Time Synchronization:** Includes a helper function to synchronize the device's time using NTP, which is crucial for AWS request signing.
* **Minimal Dependencies:** Built with standard MicroPython libraries like `urequests`, `uhashlib`, `ubinascii`, `utime`, and `network`.

## Requirements

* MicroPython firmware flashed on your device.
* Network connectivity (WiFi) configured on the device.
* The following MicroPython libraries:
    * `urequests`
    * `uhashlib`
    * `ubinascii`
    * `utime`
    * `network`
    * `ntptime` (for time synchronization)

## Setup

1.  **Copy `uboto3.py`:** Create a `uboto3` directory file into the the `/lib` directory of your MicroPython device and copy the `__init__.py` file into it.
2.  **AWS Credentials & Configuration:**
    Import the `S3Client` class from `uboto3` and set your AWS credentials and S3 bucket details in your script:
    ```python
    from uboto3 import S3Client
    # --- AWS Configuration ---
    PROVIDER = "amazonaws.com" # or "backblazeb2.com" or other S3 compatible provider
    AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY_ID"  
    AWS_SECRET_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
    AWS_REGION = "your-s3-bucket-region" 

    client = S3Client(
        provider=PROVIDER,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        region=AWS_REGION,
    )
    ```
    **Important Security Note:** Hardcoding credentials directly into the script is generally not recommended for production environments. Consider alternative methods for managing secrets on your device if security is a major concern.

3.  **IAM Permissions:**
    Ensure the AWS IAM user associated with the `AWS_ACCESS_KEY` and `AWS_SECRET_KEY` has the necessary permissions to put objects into the specified S3 bucket. A minimal policy would look like this:

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                    "arn:aws:s3:::your-s3-bucket-name/*"
                ]
            }
        ]
    }
    ```
    Replace `"your-s3-bucket-name"` with your actual bucket name.

## Usage Example

Here's how to use `uboto3` to upload a local file from your MicroPython device to S3:

```python
import network
import time
from uboto3 import S3Client
# --- Network Configuration (Example for ESP32/ESP8266) ---
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("Connecting to WiFi...")
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASSWORD)
        while not sta_if.isconnected():
            time.sleep(1)
    print("Network Config:", sta_if.ifconfig())

PROVIDER = "amazonaws.com" # or "backblazeb2.com" or other S3 compatible provider
AWS_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY_ID"  
AWS_SECRET_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
AWS_REGION = "your-s3-bucket-region" 

client = S3Client(
    provider=PROVIDER,
    access_key=AWS_ACCESS_KEY,
    secret_key=AWS_SECRET_KEY,
    region=AWS_REGION,
)

# --- Main Application ---
def main():
    # 1. Connect to WiFi
    connect_wifi()

    # 2. Synchronize time (critical for AWS authentication)
    client.sync_time() #

    # 3. Create a dummy file to upload (or use an existing file)
    local_file_to_upload = "data.txt"
    bucket_name = "my_bucket" # Ensure this bucket exists in S3
    s3_object_name = "my_device_data/data.txt" # Desired path and name in S3
    content_type = "bucket_nametext/plain"

    try:
        with open(local_file_to_upload, "w") as f:
            f.write("Hello from MicroPython!\n")
            f.write(f"Timestamp: {time.time()}\n")
        print(f"Created dummy file: {local_file_to_upload}")
    except OSError as e:
        print(f"Error creating file: {e}")
        return

    # 4. Upload the file
    print(f"Attempting to upload '{local_file_to_upload}' to S3 bucket '{bucket_name}' as '{s3_object_name}'...")
    if client.upload_to_s3(local_file_to_upload, bucket_name, s3_object_name, content_type):
        print("Upload successful!")
    else:
        print("Upload failed.")

if __name__ == "__main__":
    main()
```

## Contributing
Feel free to fork this repository, submit issues, and create pull requests if you have improvements or bug fixes.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
