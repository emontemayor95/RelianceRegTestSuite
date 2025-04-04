# Not supported:
# 0x59 (Set RAM flags)
# 0x67 (Get Comm Timeout)
# 0x63 (Set Friendly Name)
# 0x64 (Get Friendly Name)
# 0x73 (Configure RTC) (handled in QrTimeStampTest.py)
# 0x56 (Get Flash Alignment)
# 0x79 (Flash Request)
# 0x55 (Flash Update)
# 0x80 (Logo Bank)
# 0x84 (Command Log)
# 0x85 (Bezel Configuration)
# 0x86 (Calibration)
# 0x87 (Erase External Flash)
# 0x90 (Telemetry)
# 0x92 (Print Blank Ticket)
# 0x93 (Get Paper Moved)


from printStatus import parse_printer_status

COMMANDS = {
    "PING"                    : ([0x02, 0x75], False),  

    "SET_SERIAL"              : ([0x0A, 0x41, 0x00, 0x4B, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00], False),
    "GET_SERIAL"              : ([0x02, 0x40], False),

    "GET_PRINT_QUALITY"       : ([0x02, 0x42], False),
    "SET_PRINT_QUALITY_NORMAL": ([0x03, 0x43, 0x00], False),
    "SET_PRINT_QUALITY_HIGH_QUALITY": ([0x03, 0x43, 0x01] , False),  
    "SET_PRINT_QUALITY_HIGH_SPEED"  : ([0x03, 0x43, 0x00], False),    

    "GET_RETRACT_ENABLE"      : ([0x02, 0x44], False),
    "SET_RETRACT_ENABLE"      : ([0x03, 0x62], True),

    "GET_EJECTOR_MODE"       : ([0x02, 0x46], False),
    "SET_EJECTOR_MODE_PRES"  : ([0x03, 0x47, 0x00], False),
    "SET_EJECTOR_MODE_CONT"  : ([0x03, 0x47, 0x01], False),

    "GET_PRESENTER_LENGTH"    : ([0x02, 0x48], False),
    "SET_PRESENTER_LENGTH"    : ([0x03, 0x49], True),


    "GET_CR_CFG"              : ([0x02, 0x4A], False),
    "SET_CR_CFG"              : ([0x03, 0x4B], True),

    # (0x00) Do nothing. Leave ticket presented
    # (0x01) Eject the ticket
    # (0x02) Retract the ticket (Only when retract feature  is enabled)
    "SET_TIMEOUT_ACTION"       : ([0x03, 0x4D], True),
    "GET_TIMEOUT_ACTION"       : ([0x02, 0x4C], False),

    # (0x00) Invalid Option
    # (0x01) Eject Ticket
    # (0x02) Retract Ticket (Only when retract feature is enabled)
    # (0x03) Queue Ticket (Only for USB printer class)
    "SET_NEW_TICKET_ACTION"    : ([0x03, 0x4F], True),
    "GET_NEW_TICKET_ACTION"    : ([0x02, 0x4E], False),
    
    #Takes 9 bytes of data
    "SET_SERIAL_NUMBER"        : ([0x03, 0x51], True),
    "GET_SERIAL_NUMBER"        : ([0x02, 0x50], False),

    "SAVE_CONFIG"              : ([0x02, 0x52], False),

    #Takes one byte value (0 - 200)
    #100 = 100% density, default value
    "SET_PRINT_DENSITY"             : ([0x03, 0x54], True),
    "GET_PRINT_DENSITY"             : ([0x02, 0x53], False),

    #Length value is 1 byte (1 - 255 seconds)
    "Set_TIMEOUT_PERIOD"       : ([0x03, 0x61], True),
    "GET_TIMEOUT_PERIOD"       : ([0x02, 0x60], False),

    "GET_AES_PROGRAMMED"       : ([0x02, 0x13], False),

    "GET_REVLEV"               : ([0x02, 0x15], False),

    "GET_PRINTER_TYPE"         : ([0x02, 0x16], False),

    "RESET_DEVICE"             : ([0x02, 0x25], False),

    "GET_UNIQUE_ID"            : ([0x02, 0x66], False),

    "GET_BOOT_ID"              : ([0x03, 0x57, 0x10], False),

    #Reference: https://docs.google.com/document/d/1NEIAjJgeixbisGXM3_TADLGlynWKKxfObY68pIGHccg/edit?tab=t.0#bookmark=kix.idk8vzblx7gf
    "GET_PRINTER_STATUS"       : ([0x02, 0x67], False),

    "PRINT_FONT_PAGE"          : ([0x02, 0x81], False),

    # 4 bytes set font settings
    # 1byte set CPI mode
        # 0 = A 11cpi, B 15cpi
        # 1 = A 15cpi, B 20cpi
        # 2 = A 20cpi, B 15cpi\
    # 1byte Set the default font.  ‘A’ or ’B’. Value is a 1 byte ASCII char
    # 2byte Set default codepage
    "SET_FONT_SETTINGS"        : ([0x07, 0x82, 0x01], True),
    # 0 - Classic (short)
    # 1 - Modern (tall)
    "SET_SCALAR"               : ([0x04, 0x82, 0x06], True),
    "GET_FONT_SETTINGS"        : ([0x03, 0x82, 0x00], False),
    # 6 to -3
    # 7 = 0
    "SET_CUSTOM_CPI"           : ([0x04, 0x82, 0x0B], True),
    "GET_CUSTOM_CPI"           : ([0x03, 0x82, 0x0C], False),
    
    # 58mm, 60mm, OR 80mm
    "SET_PAPER_SIZE"           : ([0x04, 0x83, 0x01], True),
    "GET_PAPER_SIZE"           : ([0x03, 0x83, 0x00], False),

    # 0 = OFF, 1 = ON
    "SET_AUTOCUT_EN"              : ([0x04, 0x88, 0x00], True),
    "GET_AUTOCUT_EN"              : ([0x03, 0x88, 0x01], False),
    # 1 byte value (0 - 255 seconds)
    "SET_AUTOCUT_TIMEOUT"      : ([0x04, 0x88, 0x02], True),

    "PRINT_CONFIG_TICKET"      : ([0x03, 0x89, 0x02], False),

    # 0 = OFF, 1 = ON
    "SET_PAPER_SLACK_COMPENSATION" : ([0x04, 0x91, 0x02], True),
    "GET_PAPER_SLACK_COMPENSATION" : ([0x03, 0x91, 0x03], False),
    
    # 0 = OFF, 1 = ON
    "SET_STARTUP_TICKET_ENABLE" : ([0x04, 0x91, 0x0C], True),
    "GET_STARTUP_TICKET_ENABLE" : ([0x03, 0x91, 0x0D], False),

    "SET_TRUNCATE_WS"           : ([0x04, 0x91, 0x010], True),
    "GET_TRUNCATE_WS"           : ([0x03, 0x91, 0x011], False),
    
    # 24 bytes formatted as follows:
    # MODE, KEY, CASE, SKIP, LINE
    # MODE - This is 1 bytes representing the current Sentry mode that the printer is in. The valid modes are as follows:
    # 00 - DISABLED (Requires printer to be repaired to enable sentry)
    # 01 - Default
    # 02 - Keyword Parse
    # 03 - Line Parse
    # 04 - Skip Parse
    # 
    # KEY - This is 20 bytes representing the custom keyword string stored in sentry. Will be null if not in keyword or skip parse mode. 
    # CASE -  This is 1 byte that controls whether case sensitive mode is enabled/disabled (1/0) for keyword parse mode.
    # SKIP - This is 1 byte representing how many occurrences of the keyword to skip in Skip parse mode. 
    # LINE - This is 1 byte representing the line to search for value data on in Line parse mode. 
    "SET_SENTRY_CONFIG"        : ([0x1A, 0x95,], True),
    "GET_SENTRY_CONFIG"        : ([0x02, 0x94], False),
    
    # 20 byte duplicate key, must pad with 0x00 if word is less than 20 bytes
    "SET_DUPLICATE_KEYWORD"     : ([0x16, 0x98], True),
    "GET_DUPLICATE_KEYWORD"     : ([0x03, 0x96], False),

    # 20 byte duplicate key, must pad with 0x00 if word is less than 20 bytes
    "SET_PRE_SENTRY_KEY"        : ([0x16, 0x99], True),
    "GET_PRE_SENTRY_KEY"        : ([0x03, 0x97], False),

    # 0 = OFF, 1 = ON
    "SET_PULL_TAB_MODE"         : ([0x04, 0xA0, 0x00], True),
    "GET_PULL_TAB_MODE"         : ([0x03, 0xA0, 0x01], False),

    # 0 = OFF, 1 = ON
    "SET_LF_CFG"      : ([0x03, 0xA2], True),
    "GET_LF_CFG"      : ([0x02, 0xA1], False),

    "SET_LOCK_CPI"             : ([0x03, 0xA4], True),
    "GET_LOCK_CPI"             : ([0x02, 0xA3], False),

    # (0 - 2) Duplicate keyword index
    "GET_MULTI_DUPKEY"         : ([0x04, 0xA5, 0x00], True),
    # (0 - 2) Duplicate keyword index
    # 20 byte duplicate key, must pad with 0x00 if word is less than 20 bytes
    "SET_MULTI_DUPKEY"         : ([0x18, 0xA5, 0x01], True),

    "SEN_QR_TS_CFG"             : ([0x03, 0xAD], True),

    "SET_RTC"                : ([0x0A, 0x73, 0x00], True),
}   

ENABLE = 0x01
DISABLE = 0x00

#Customizable commands
def get_command(command_name, value = None):
    if command_name not in COMMANDS:
        raise ValueError(f"Command '{command_name}' not found in COMMANDS")
    
    command_bytes, requires_value = COMMANDS[command_name]

    if requires_value and value is None:
        raise ValueError(f"Command '{command_name}' requires a value but none was provided")
    
    if not requires_value and value is not None:
        raise ValueError(f"Command '{command_name}' does not require a value but one was provided")
    
    return command_bytes + (value if isinstance(value, list) else [value] if value is not None else [])

# Write command to the device and read the response
# If simple command, return ACK or NAK
# If complex command, return the entire response
def write_command(device, command, *value):
    TX_ID = 1 # Transmit ID
    command_bytes = get_command(command, *value)  # Get the command bytes from the command name
    hid_length_byte = [len(command_bytes) + 1] 
    checksum = [calculate_checksum(command_bytes)] 
    payload = hid_length_byte + command_bytes + checksum
    device.write([TX_ID] + payload)
    response = device.read(128)
    if not response:
        print("No response received")
        return "NAK"

    if response[3] != 0xAA:
        print("NAK")
        print("Response:", response) 
        return "NAK"
    else:
        return "ACK", response[4:]  # Return the response data after the ACK byte


def getPrinterStatus(device):
    response = write_command(device, "GET_PRINTER_STATUS")
    if response == "NAK":
        print("Failed to get printer status")
        return "NAK"
    
    status = parse_printer_status(response)
    return status


def calculate_checksum(data: bytes) -> int:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum