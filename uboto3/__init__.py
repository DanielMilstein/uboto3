import urequests
import uhashlib
import ubinascii
import utime
import ntptime


class S3Client:
    def __init__(self, provider: str, access_key: str, secret_key, region):
        self.provider = provider
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

    # --- HMAC-SHA256 Implementation ---
    def _hmac_sha256(self, key_bytes, msg_bytes):
        block_size = 64

        if len(key_bytes) > block_size:
            key_bytes = uhashlib.sha256(key_bytes).digest()

        if len(key_bytes) < block_size:
            key_bytes = key_bytes + b"\x00" * (block_size - len(key_bytes))

        o_key_pad = bytes(b ^ 0x5C for b in key_bytes)
        i_key_pad = bytes(b ^ 0x36 for b in key_bytes)

        inner_hash = uhashlib.sha256(i_key_pad + msg_bytes).digest()
        outer_hash = uhashlib.sha256(o_key_pad + inner_hash).digest()

        return outer_hash

    def _get_timestamp(self) -> tuple[str, str]:
        now = utime.gmtime()
        amz_date = "{:04d}{:02d}{:02d}T{:02d}{:02d}{:02d}Z".format(
            now[0], now[1], now[2], now[3], now[4], now[5]
        )
        datestamp = "{:04d}{:02d}{:02d}".format(now[0], now[1], now[2])
        return amz_date, datestamp

    def _get_signature_key(self, date_stamp_string, service_name_string="s3"):
        k_secret_bytes = ("AWS4" + self.secret_key).encode("utf-8")
        k_date_bytes = self._hmac_sha256(
            k_secret_bytes, date_stamp_string.encode("utf-8")
        )
        k_region_bytes = self._hmac_sha256(k_date_bytes, self.region.encode("utf-8"))
        k_service_bytes = self._hmac_sha256(
            k_region_bytes, service_name_string.encode("utf-8")
        )
        k_signing_bytes = self._hmac_sha256(k_service_bytes, b"aws4_request")
        return k_signing_bytes

    def sync_time():
        print("Synchronizing time with NTP server...")
        try:
            ntptime.settime()  # This sets the ESP32's RTC to UTC
            print("Time synchronized successfully.")
            now_utc = utime.gmtime()
            print(
                "Current UTC from ESP32: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                    now_utc[0],
                    now_utc[1],
                    now_utc[2],
                    now_utc[3],
                    now_utc[4],
                    now_utc[5],
                )
            )
        except Exception as e:
            print(f"Error synchronizing time: {e}")

    def upload_to_s3(
        self,
        local_file_path: str,
        bucket: str,
        s3_object_name: str,
        content_type="application/octet-stream",
    ):
        try:
            with open(local_file_path, "rb") as f:
                data = f.read()
            print(f"Successfully read {len(data)} bytes from {local_file_path}")
        except OSError as e:
            print(f"Error opening or reading file '{local_file_path}': {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred reading file '{local_file_path}': {e}")
            return False

        host = f"{bucket}.s3.{self.region}.{self.provider}"
        amz_date, datestamp = self._get_timestamp()

        # ---- Task 1: Create Canonical Request ----
        method = "PUT"
        canonical_uri = f"/{s3_object_name}"
        canonical_querystring = ""

        payload_hash_bytes = uhashlib.sha256(data).digest()
        payload_hash_hex = ubinascii.hexlify(payload_hash_bytes).decode()

        # Note: Headers must be in alphabetical order by header name (lowercase)
        # and values should be stripped of leading/trailing whitespace.
        canonical_headers_list = [
            ("host", host),
            ("x-amz-content-sha256", payload_hash_hex),
            ("x-amz-date", amz_date),
            # If you add Content-Type here, ensure it's also in SignedHeaders and the actual request
            # ('content-type', content_type)
        ]
        canonical_headers_list.sort(key=lambda item: item[0])

        canonical_headers_str = ""
        signed_headers_list = []
        for key, value in canonical_headers_list:
            canonical_headers_str += f"{key}:{value.strip()}\n"
            signed_headers_list.append(key)
        signed_headers_str = ";".join(signed_headers_list)

        canonical_request = (
            f"{method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers_str}\n"  # Already has a trailing newline
            f"{signed_headers_str}\n"
            f"{payload_hash_hex}"
        )
        # print(f"Canonical Request:\n{canonical_request}\n") # For debugging

        # ---- Task 2: Create String to Sign ----
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{datestamp}/{self.region}/s3/aws4_request"

        hashed_canonical_request_bytes = uhashlib.sha256(
            canonical_request.encode("utf-8")
        ).digest()
        hashed_canonical_request_hex = ubinascii.hexlify(
            hashed_canonical_request_bytes
        ).decode()

        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request_hex}"
        )
        # print(f"String to Sign:\n{string_to_sign}\n") # For debugging

        # ---- Task 3: Calculate Signature ----
        signing_key_bytes = self._get_signature_key(
            date_stamp_string=datestamp, service_name_string="s3"
        )

        signature_bytes = self._hmac_sha256(
            signing_key_bytes, string_to_sign.encode("utf-8")
        )
        signature_hex = ubinascii.hexlify(signature_bytes).decode()
        # print(f"Signature: {signature_hex}\n") # For debugging

        # ---- Task 4: Add Signing Information to the Request ----
        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, "
            f"Signature={signature_hex}"
        )

        headers = {
            "Host": host,
            "X-Amz-Date": amz_date,
            "X-Amz-Content-Sha256": payload_hash_hex,
            "Authorization": authorization_header,
            "Content-Type": content_type,  # Ensure this is sent
            "Content-Length": str(len(data)),
        }
        # ---- Make the PUT request ----
        url = f"https://{host}{canonical_uri}"  # Use HTTPS
        print(f"Uploading to: {url}")
        # print(f"Request Headers: {headers}") # For debugging

        try:
            response = urequests.put(url, headers=headers, data=data)
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            response.close()
            return response.status_code == 200
        except Exception as e:
            print(f"Error during S3 PUT request: {e}")
            return False
