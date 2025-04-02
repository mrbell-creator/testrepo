import logging

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)

def hex_to_bytearray(hex_string):
    """Converts a hex string (which may include spaces) into a bytearray."""
    hex_string = hex_string.replace(" ", "")
    try:
        return bytearray.fromhex(hex_string)
    except ValueError:
        logging.error("Invalid hex string: %s", hex_string)
        return None

def parse_payload(hex_payload):
    logging.debug("[parse_payload] Starting parse for: %s", hex_payload)
    data = hex_to_bytearray(hex_payload)
    if not data or len(data) < 8:
        logging.warning("[parse_payload] Payload too short or invalid: %s", data)
        return None

    try:
        header = data[:2]
        mfrData = data[2:]
        mfr_header = mfrData[0:2]

        accelo_byte = mfrData[2]
        accelo_map = [-7, 1, 2, 3, 4, 5, 6, 0, -6, -5, -8, 7, -4, -3, -2, -1]
        accelo_x = accelo_map[accelo_byte & 0x0F]
        accelo_y = accelo_map[(accelo_byte >> 4) & 0x0F]

        hwid = mfrData[3]
        hw_family = "xl" if (hwid & 1) == 1 else "gen2"
        hw_version = hwid & 0xCF
        logging.debug("[parse_payload] Detected %s sensor.", hw_family.upper())

        battery_raw = mfrData[4]
        battery_voltage = (battery_raw / 256.0) * 2.0 + 1.5

        temp_byte = mfrData[5]
        raw_temp = temp_byte & 0x3F
        temperature = -40.0 if raw_temp == 0 else (raw_temp - 25) * 1.776964
        slow_update = (temp_byte & 0x40) != 0
        sync_pressed = (temp_byte & 0x80) != 0

        adv = []
        if hw_family == "xl":
            last_time = 0
            w = 6
            data_length = len(mfrData)
            for q in range(12):
                bitpos = q * 10
                bytepos = bitpos // 8
                off = bitpos % 8
                if w + bytepos + 1 >= data_length:
                    break
                v = mfrData[w + bytepos] + (mfrData[w + bytepos + 1] << 8)
                v = v >> off
                dt = (v & 0x1F) + 1
                v = v >> 5
                amp = v & 0x1F
                this_time = last_time + dt
                last_time = this_time
                if this_time > 255:
                    break
                if amp == 0:
                    continue
                amp = (amp - 1) * 4 + 6
                adv.append({"a": amp, "i": this_time * 2})
        else:
            i = 6
            while i + 1 < len(mfrData):
                amp = mfrData[i]
                offset = mfrData[i + 1]
                if amp == 0 and offset == 0:
                    break
                adv.append({"a": amp, "i": offset})
                i += 2

        logging.debug("[parse_payload] Parsed peaks: %s", adv)

        return {
            "header": header.hex(),
            "manufacturer_header": mfr_header.hex(),
            "accelerometer": {"raw": accelo_byte, "x": accelo_x, "y": accelo_y},
            "hardware_id": hwid,
            "hardware_family": hw_family,
            "hardware_version": hw_version,
            "battery_raw": battery_raw,
            "battery_voltage": round(battery_voltage, 2),
            "temperature_raw": raw_temp,
            "temperature_c": round(temperature, 2),
            "slow_update": slow_update,
            "sync_pressed": sync_pressed,
            "advertisement_peaks": adv
        }
    except (IndexError, ValueError) as e:
        logging.exception("[parse_payload] Error while parsing: %s", e)
        return None

def get_example_hex_strings():
    return [
        "1AFF0D000002B765924F310302157CA080030D74E08107EA287B270302A0AD",
        "1AFF0D000002B867F34E3183051C04B08001000080810275287B270302A0AD",
        "1AFF0D000002B567D3CE3147041C088041041C28E041007E287B270302A0AD",
        "1AFF0D000002AC67153CE04100000C30C000036C9080074D287B270302A0AD",
    ]
