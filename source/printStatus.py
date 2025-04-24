import struct

def parse_printer_status(response: bytes):
    """
    Parses the Get Printer Status response.

    :param response: A bytes object containing the printer status data.
    :return: A dictionary with parsed values.
    """
    if len(response) < 16:  # Ensure minimum valid length
        raise ValueError("Response is too short to be valid")

    # Extract fields from the response
    head_voltage = response[:5].decode('ascii')  # 5-byte ASCII string
    head_temp = response[5]  # 1 byte integer
    sensor_status = response[6]  # 1 byte bit field
    presenter_sensor_raw = struct.unpack_from('<H', response, 7)[0]  # uint16_t
    path_sensor_raw = struct.unpack_from('<H', response, 9)[0]
    paper_sensor_raw = struct.unpack_from('<H', response, 11)[0]
    notch_sensor_raw = struct.unpack_from('<H', response, 13)[0]
    arm_sensor_raw = struct.unpack_from('<H', response, 15)[0]
    ticket_status = response[17]  # 1 byte
    error_status = response[18]  # 1 byte bit field

    # Decode bit fields
    sensor_flags = {
        "Platen": bool(sensor_status & 0b00000001),
        "Cutter Home": bool(sensor_status & 0b00000010),
        "Tach Status": bool(sensor_status & 0b00000100),
        "Presenter Paper": bool(sensor_status & 0b00001000),
        "Path Paper": bool(sensor_status & 0b00010000),
        "Paper Sensor": bool(sensor_status & 0b00100000),
        "Notch Sensor": bool(sensor_status & 0b01000000),
        "Arm Sensor": bool(sensor_status & 0b10000000),
    }

    error_flags = {
        "Jammed": bool(error_status & 0b00000001),
        "Overheated": bool(error_status & 0b00000010),
        "Cutter Error": bool(error_status & 0b00000100),
        "Voltage High": bool(error_status & 0b00001000),
        "Voltage Low": bool(error_status & 0b00010000),
        "Platen Open": bool(error_status & 0b00100000),
        "Reserved": bool(error_status & 0b01000000),
        "Unknown Error": bool(error_status & 0b10000000),
    }

    ticket_status_meaning = {
        0: "Idle",
        1: "Printing",
        2: "Unpresented",
        3: "Presented",
    }

    return {
        "Head Voltage": head_voltage,
        "Head Temp (°C)": head_temp,
        "Sensor Status": sensor_flags,
        "Presenter Sensor Raw": presenter_sensor_raw,
        "Path Sensor Raw": path_sensor_raw,
        "Paper Sensor Raw": paper_sensor_raw,
        "Notch Sensor Raw": notch_sensor_raw,
        "Arm Sensor Raw": arm_sensor_raw,
        "Ticket Status": ticket_status_meaning.get(ticket_status, "Unknown"),
        "Error Status": error_flags,
    }
