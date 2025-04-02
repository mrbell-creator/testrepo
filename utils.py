"""
Utility functions for parsing Mopeka sensor data.
These functions handle the conversion of Bluetooth hex strings to meaningful sensor data.
"""

def hex_to_bytearray(hex_string):
    """Converts a hex string (which may include spaces) into a bytearray."""
    hex_string = hex_string.replace(" ", "")
    try:
        return bytearray.fromhex(hex_string)
    except ValueError:
        return None

def parse_payload(hex_payload):
    """
    Parses a Mopeka sensor payload from its hex representation.

    After stripping the first two header bytes, the manufacturer data is expected to be:  
      - Bytes 0-1: Manufacturer header (should be 0D00)  
      - Byte 2: Accelerometer data (a single byte; lower nibble gives X and upper nibble gives Y via a lookup table)  
      - Byte 3: Hardware ID (determines sensor family and version)  
      - Byte 4: Battery value; battery voltage = (value/256)*2.0 + 1.5.  
      - Byte 5: Temperature and flags.  
          * Lower 6 bits: raw temperature (if 0 then -40°C, else (raw - 25)*1.776964)  
          * Bit 6 (0x40): Slow update rate flag.  
          * Bit 7 (0x80): Sync pressed flag.  
      - Bytes 6 onward: Advertisement (peak) data, encoded in 10-bit groups.  

    Returns a dict with key fields and a list "advertisement_peaks" where each peak is a dict with:  
      - "a": amplitude (adjusted as: (raw_amp - 1)*4 + 6)  
      - "i": time offset (this_time * 2)  
    """
    data = hex_to_bytearray(hex_payload)
    if not data or len(data) < 8:
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

        battery_raw = mfrData[4]
        battery_voltage = (battery_raw / 256.0) * 2.0 + 1.5

        temp_byte = mfrData[5]
        raw_temp = temp_byte & 0x3F
        temperature = -40.0 if raw_temp == 0 else (raw_temp - 25) * 1.776964
        slow_update = (temp_byte & 0x40) != 0
        sync_pressed = (temp_byte & 0x80) != 0

        adv = []
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
    except (IndexError, ValueError):
        return None

def adjust_amplitude(a_val, time_val, vref):
    """Mimics the amplitude adjustment function from the legacy JS code."""
    c_val = 0.5 * vref
    d_val = (255 - time_val) / 256.0
    if a_val <= c_val:
        return 0
    return (a_val - c_val) * d_val

def compute_pulse_echo_time2(peak_data, vref=1.2421875):
    """Approximate replication of the legacy GetPulseEchoTime2 algorithm."""
    if not peak_data:
        return 0
    c = peak_data
    e = len(c)

    k = [0]
    for b in range(1, e):
        prev_time = c[b-1]['i'] / 2.0
        curr_time = c[b]['i'] / 2.0
        if abs((prev_time + 1) - curr_time) > 1e-6:
            k.append(b)

    g_list = []
    p = 0
    num_segments = len(k)
    for b in range(num_segments):
        m_val = 0
        n_val = 0
        q = e if b == num_segments - 1 else k[b+1]
        for f in range(p, q):
            if c[f]['a'] > m_val:
                m_val = c[f]['a']
                n_val = f
        g_list.append(n_val)
        p = q

    n_arr = [0.0] * 100
    m_arr = [0.0] * 100

    for b in range(e):
        time_val = c[b]['i'] / 2.0
        p_val = c[b]['a']
        p_adj = adjust_amplitude(p_val, time_val, vref)
        idx = int(round(time_val))
        if idx < 100:
            n_arr[idx] += 0.5 * p_adj
        for f in range(b+1, e):
            q_val = c[f]['i'] / 2.0
            t_val = q_val - time_val
            r_val = c[f]['a']
            r_adj = adjust_amplitude(r_val, q_val, vref)
            if p_adj < r_adj:
                r_adj = p_adj
            t_idx = int(round(t_val))
            if t_idx < 100:
                n_arr[t_idx] += r_adj

    for b in range(len(g_list)):
        time_val = c[g_list[b]]['i'] / 2.0
        p_val = c[g_list[b]]['a']
        m_adj = adjust_amplitude(p_val, time_val, vref)
        idx = int(round(time_val))
        if idx < 100:
            m_arr[idx] += m_adj
        for f in range(b+1, len(g_list)):
            q_val = c[g_list[f]]['i'] / 2.0
            t_val = q_val - time_val
            r_val = c[g_list[f]]['a']
            r_adj = adjust_amplitude(r_val, q_val, vref)
            r_combined = (r_adj + m_adj) / 2.0
            t_idx = int(round(t_val))
            if t_idx < 100:
                m_arr[t_idx] += r_combined

    score_filt = [0.0] * 100
    score_filt[0] = 0.25 * n_arr[1] + 0.5 * n_arr[0] + 0.5 * m_arr[1] + 0.5 * m_arr[0]
    for b in range(1, 99):
        score_filt[b] = (0.25 * (n_arr[b-1] + n_arr[b+1]) +
                         0.5 * n_arr[b] +
                         0.5 * (m_arr[b-1] + m_arr[b+1]) +
                         0.5 * m_arr[b])
    score_filt[99] = 0.25 * n_arr[98] + 0.5 * n_arr[99] + 0.5 * m_arr[98] + 0.5 * m_arr[99]

    max_score = 0.005
    n_index = 0
    for b in range(2, 100):
        if score_filt[b] > max_score:
            max_score = score_filt[b]
            n_index = b

    g_max = max(peak['a'] for peak in c) if c else 0
    if g_max <= 0.63453125:
        return 0
    return 2e-5 * n_index

def legacy_level_inches(tof):
    return 13700 * tof + 0.5

def legacy_level_cm(tof):
    return legacy_level_inches(tof) * 2.54

def legacy_level_percentage(tof, tank_height=0.254):
    if tank_height <= 0.0381:
        return 100
    level_meters = legacy_level_cm(tof) / 100.0
    percentage = 98 * (level_meters - 0.0381) / (tank_height - 0.0381) + 2
    if percentage < 2:
        percentage = 2
    if percentage > 100:
        percentage = 100
    return round(percentage)

def process_hex_string(hex_string, tank_height=0.254):
    if not hex_string:
        return None
    parsed = parse_payload(hex_string)
    if not parsed:
        return None

    peaks = parsed.get("advertisement_peaks", [])
    tof = compute_pulse_echo_time2(peaks)
    level_in_inches = legacy_level_inches(tof)
    level_cm = legacy_level_cm(tof)
    is_empty = tof == 0

    result = parsed.copy()
    result["tof"] = tof
    result["level_inches"] = level_in_inches
    result["level_cm"] = level_cm
    result["is_empty"] = is_empty

    if not is_empty:
        result["percentage"] = legacy_level_percentage(tof, tank_height)
    else:
        result["percentage"] = 0

    return result

def get_example_hex_strings():
    """Returns a list of example hex strings that can be used for testing."""
    return [
        "1AFF0D000002B765924F310302157CA080030D74E08107EA287B270302A0AD",
        "1AFF0D000002B867F34E3183051C04B08001000080810275287B270302A0AD",
        "1AFF0D000002B567D3CE3147041C088041041C28E041007E287B270302A0AD",
        "1AFF0D000002AC67153CE04100000C30C000036C9080074D287B270302A0AD",
    ]
