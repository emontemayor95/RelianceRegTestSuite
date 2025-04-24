from commands import write_command
import time
from dataclasses import dataclass
from typing import Callable, Any, List
from emu_sentry import Sentry
import datetime
from emu_sentry import Sentry, get_timestamp_bytes, get_random_timestamp
import sys
import os


@dataclass 
class TestEntry:
    name: str
    success: bool
    func: Callable[..., bool]
    args: List[Any] = None

    def run(self):
        """Run the test and update the 'success' attribute based on the result."""
        try: 
            if self.args:
                self.success = self.func(*self.args, self)  # Pass self (the TestEntry instance) as the last argument
            else:
                self.success = self.func(self)  # Pass self directly if no arguments
        except Exception as e:
            print(f"Error running test {self.name}: {e}")
            self.success = False



## Generic commands / globals ##
PRNT_CMD = b'\x0C'
EN = 0x01
DIS = 0x00
CR_CMD = b'\x0D'
LF_CMD = b'\x0A'

def datetime_to_bytes(dt: datetime.datetime) -> bytes:
    # Extract date and time components
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute

    # Pack the components into bytes
    year_bytes = year.to_bytes(2, 'little')  
    month_byte = month.to_bytes(1, 'little')  
    day_byte = day.to_bytes(1, 'little')     
    hour_byte = hour.to_bytes(1, 'little')   
    minute_byte = minute.to_bytes(1, 'little')

    return year_bytes + month_byte + day_byte + hour_byte + minute_byte

def checkSuccess(testName, test_entry: TestEntry):
    """Updates the success attribute of the TestEntry instance."""
    while True:
        status = input(f"Pass? (y/n): ").strip().lower()
        if status in ['y', 'n']:
            break
        print("Invalid input. Please enter 'y' or 'n'.")
    
    if status == 'n':
        print(f"{testName} - Test failed")
        test_entry.success = False  # Update the test entry as failed
        return False
    else:
        print(f"{testName} - Test passed")
        test_entry.success = True  # Update the test entry as passed
        return True

def test_printQuality(ser, device, quantity, test_entry: TestEntry):
    
    input("Tickets will print with three different qualities that affect print speed." \
    "\nHigh speed: faster prints" \
    "\nHigh quality: slower prints" \
    "\nNormal: balanced between speed and quality" \
    "\nPASS CONDITIONS:" \
    "\n - No jamming occurs" \
    "\n - Each option has a noticeable difference in print speed" \
    "\nPress Enter to begin...")

    response = write_command(device, "SET_PRINT_QUALITY_NORMAL")
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    print("Print quality set to NORMAL")
    for i in range(quantity):
        for j in range(10):
            ser.write(b'PRINT QUALITY NORMAL\n')
        ser.write(PRNT_CMD)
        time.sleep(2)  

    response = write_command(device, "SET_PRINT_QUALITY_HIGH_QUALITY")
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    print("Print quality set to HIGH QUALITY")
    for i in range(quantity):
        for j in range(10):
            ser.write(b'PRINT QUALITY HIGH QUALITY\n')
        ser.write(PRNT_CMD)
        time.sleep(2)  
    
    time.sleep(3)
    response = write_command(device, "SET_PRINT_QUALITY_HIGH_SPEED")
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    print("Print quality set to HIGH SPEED")
    for i in range(quantity):
        for j in range(10):
            ser.write(b'PRINT QUALITY HIGH SPEED\n')
        ser.write(PRNT_CMD)
        time.sleep(2)  

    response = write_command(device, "SET_PRINT_QUALITY_NORMAL")
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    return checkSuccess("PRINT_QUALITY", test_entry)
    

def test_jamTestingRetractionMode(ser, device, quantity, mm, test_entry: TestEntry):
    print(f"Load {mm}mm paper into printer")
    input("Tickets will print and then retract into the\ndisposal on the bottom of the printer\nwhen a new ticket is sent" \
    "\nSet printer on the edge of your desk to allow space for disposal." \
    "\nPASS CONDITIONS:" \
    "\n - No jamming occurs" \
    "\n - Tickets are correctly retracted" \
    "\nPress Enter to begin...")

    #Set paper size to mm
    if mm == 80:
        size = 0x50
    elif mm == 58:
        size = 0x3A
    
    # Set paper size to 80mm or 58mm
    response = write_command(device, "SET_PAPER_SIZE", size)
    if response == "NAK":
        print("Failed to set paper size")
        return

    response = write_command(device, "SET_RETRACT_ENABLE", EN)
    if response == "NAK":
        print("Failed to set retraction mode")
        return
    
    # Set new ticket action to retract
    response = write_command(device, "SET_NEW_TICKET_ACTION", 0x02)
    if response == "NAK":
        print("Failed to set retraction mode")
        return
    
    response = write_command(device, "SET_PRINT_QUALITY_NORMAL")
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    for i in range(quantity):
        for j in range(10):
            ser.write(b'\nRETRACT TESTING\n')
        ser.write(PRNT_CMD)
        time.sleep(2)  

    ## Return to default settings ##
    time.sleep(3)
    response = write_command(device, "SET_RETRACT_ENABLE", DIS)
    if response == "NAK":
        print("Failed to set retraction mode")
        return
    
    response = write_command(device, "SET_NEW_TICKET_ACTION", 0x01)
    if response == "NAK":
        print("Failed to set retraction mode")
        return
    
    response = write_command(device, "SET_PRINT_QUALITY_NORMAL")
    if response == "NAK":
        print("Failed to set print quality")
        return

    return checkSuccess(f"JAM_RETRACTION_{mm}MM", test_entry)

def test_jamTestingContinuousMode(ser, device, quantity, mm, test_entry: TestEntry):
    print(f"Load {mm}mm paper into printer")
    input("Tickets will print and then eject\nwhen a new ticket is sent" \
    "\nBe prepared to catch them" \
    "\nPASS CONDITIONS:" \
    "\n - No jamming occurs" \
    "\n - Tickets are correctly ejected in succession" \
    "\nPress Enter to begin...")

    #Set paper size to mm
    if mm == 80:
        size = 0x50
    elif mm == 58:
        size = 0x3A
    
    # Set paper size to 80mm or 58mm
    response = write_command(device, "SET_PAPER_SIZE", size)
    if response == "NAK":
        print("Failed to set paper size")
        return
    
    #Print density set to 160%
    response = write_command(device, "SET_PRINT_DENSITY", 0xA0)
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    for i in range(quantity):
        for j in range(10):
            ser.write(b'PRINT DENSITY 160% \nCONTINUOUS TESTING\n')
        ser.write(PRNT_CMD)
        time.sleep(2)  

    #Print density set to 100%
    response = write_command(device, "SET_PRINT_DENSITY", 0x64)
    if response == "NAK":
        print("Failed to set print quality")
        return
    
    for i in range(quantity):
        for j in range(10):
            ser.write(b'PRINT DENSITY 100% \nCONTINUOUS TESTING\n')
        ser.write(PRNT_CMD)
        time.sleep(2)
    
    if mm == 80:
        print("You can keep the 80mm paper in the printer\nfor the rest of the tests!")

    return checkSuccess(f"JAM_CONTINUOUS_{mm}MM", test_entry)

def test_presentLength(ser, device, test_entry: TestEntry):
    input("Two tickets will print. First with present length set to 200\nand then with present length set to 10\n" \
    "\nObserve how much the ticket sticks out and note the difference between the two." \
    "\nPASS CONDITIONS:" \
    "\n - First ticket sticks out more than the second" \
    "\n - Both tickets are obtainable" \
    "\nPress Enter to begin...")

    response = write_command(device, "SET_PRESENTER_LENGTH", 0xC8)
    if response == "NAK":
        print("Failed to set presenter length")
        return
    
    ser.write(b'OBSERVE PRESENT LENGTH: 200\n')
    ser.write(PRNT_CMD)

    input("Observe present length. \nPress Enter to continue...\n")

    response = write_command(device, "SET_PRESENTER_LENGTH", 0x0A)
    if response == "NAK":
        print("Failed to set presenter length")
        return
    
    ser.write(b'OBSERVE PRESENT LENGTH: 10\n')
    ser.write(PRNT_CMD)

    input(f"Observe present length. \nPress Enter to continue...\n")

    response = write_command(device, "SET_PRESENTER_LENGTH", 0xC8)
    if response == "NAK":
        print("Failed to set presenter length")
        return

    return checkSuccess(f"PRESENT_LENGTH", test_entry)

def test_CRLF(ser, device, test_entry: TestEntry):
    input("The Carriage Return (CR) and Line Feed (LF) configurables \nwill be tested. \nwhen a new ticket is sent" \
    "\nBoth of these serve the same function: to start a new line" \
    "\nPASS CONDITIONS:" \
    "\n - If enabled there will be space between the printed lines. These are LF or CR commands." \
    "\n - If disabled there will be no space between the lines" \
    "\nPress Enter to begin...")

    print("Testing carriage return (0x0D)\n")
    response = write_command(device, "SET_CR_CFG", EN)
    if response == "NAK":
        print("Failed to set carriage return")
        return
    time.sleep(1)
    ser.write(b'CARRIAGE RETURN ENABLE\n')
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(b'THIS LINE SHOULD BE\n 5 BELOW FIRST LINE\n')
    ser.write(PRNT_CMD)

    input("Observe ticket. Press Enter to continue...\n")

    response = write_command(device, "SET_CR_CFG", DIS)
    if response == "NAK":
        print("Failed to set carriage return")
        return
    time.sleep(1)
    ser.write(b'CARRIAGE RETURN DISABLED\n')
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(CR_CMD)
    ser.write(b'THIS LINE SHOULD BE ONE LINE\n BELOW FIRST\n')    
    ser.write(PRNT_CMD) 

    input("Observe ticket. \nPress Enter to continue...\n")

    print("Testing line feed (0x0A)\n")
    response = write_command(device, "SET_LF_CFG", EN)
    if response == "NAK":
        print("Failed to set line feed")
        return
    
    #fun fact: \n and 0x0A over ser     are the same thing, but we are 
    #keeping this format for consistency with the CR_CMD :)

    ser.write(b'LINEFEED ENABLED\n')
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(b'THIS LINE SHOULD BE FIVE LINES\n BELOW FIRST\n')        
    ser.write(PRNT_CMD) 

    input("Observe ticket!\n Press Enter to continue...\n")

    response = write_command(device, "SET_LF_CFG", DIS)
    if response == "NAK":
        print("Failed to set line feed")
        return
    
    ser.write(b'LINEFEED DISABLED  \n')
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(LF_CMD)
    ser.write(b'THIS LINE SHOULD BE ON THE SAME AS THE FIRST')
    ser.write(PRNT_CMD) 

    response = write_command(device, "SET_LF_CFG", EN)
    if response == "NAK":
        print("Failed to set line feed")
        return

    return checkSuccess(f"PRESENT_LENGTH", test_entry)

def test_autocut(ser, device, test_entry: TestEntry):
    input("Tickets will print without an explicit cut command and the \nautocut feature will cut and present them. \nThe timeout feature is also tested, \nwhere autocut will wait for the timer to run out before presenting." \
    "\nSet printer on the edge of your desk to allow space for disposal." \
    "\nPASS CONDITIONS:" \
    "\n - No jamming occurs" \
    "\n - Tickets are correctly cut and presented when autocut is enabled" \
    "\nPress Enter to begin...")
    response = write_command(device, "SET_AUTOCUT_EN", EN)
    if response == "NAK":
        print("Failed to set autocut")
        return
    for i in range(10):
        ser.write(b'AUTOCUT ENABLED\n')
    

    input("Auto cut enabled!\nPress Enter to continue...\n")

    response = write_command(device, "SET_AUTOCUT_TIMEOUT", 0x0A)
    if response == "NAK":
        print("Failed to set autocut")
        return
    for i in range(10):
        ser.write(b'AUTOCUT DISABLED\n')   

    print("Autocut timeout set to 10 seconds. Wait for print!")
    input("Press Enter to continue...\n")

    response = write_command(device, "SET_AUTOCUT_TIMEOUT", 0x03)
    if response == "NAK":
        print("Failed to set autocut")
        return
    for i in range(10):
        ser.write(b'AUTOCUT DISABLED\n')   

    print("Autocut timeout set to 3 seconds. Wait for print!")
    input("Press Enter to continue...\n")

    response = write_command(device, "SET_AUTOCUT_EN", DIS)
    if response == "NAK":
        print("Failed to set autocut")
        return
    for i in range(10):
        ser.write(b'AUTOCUT DISABLED\n')
    input("Autocut disabled!\nTicket should be inside printer.\nPress enter to continue/eject ticket\n")
    ser.write(PRNT_CMD)

    response = write_command(device, "SET_AUTOCUT_EN", EN)
    if response == "NAK":
        print("Failed to set autocut")
        return    

    return checkSuccess(f"AUTOCUT", test_entry)

def test_truncateWS(ser, device, test_entry: TestEntry):
    response = write_command(device, "SET_TRUNCATE_WS", EN)
    if response == "NAK":
        print("Failed to set truncate whitespace")
        return
    
    response = write_command(device, "SET_LF_CFG", EN)
    if response == "NAK":
        print("Failed to set line feed")
        return
    
    for i in range(10):
        ser.write(b'TRUNCATE WHITE SPACE ENABLED\n')
    ser.write(b'This ticket should not have\nextra space at the end')
    for i in range(10):
        ser.write(LF_CMD)

    ser.write(PRNT_CMD)
    
    time.sleep(2)

    response = write_command(device, "SET_TRUNCATE_WS", DIS)
    if response == "NAK":
        print("Failed to set truncate whitespace")
        return
    
    for i in range(10):
        ser.write(b'TRUNCATE WHITE SPACE DISABLED\n')
    ser.write(b'This ticket SHOULD have\nwhite space at the end\n')
    for i in range(10):
        ser.write(LF_CMD)
    ser.write(PRNT_CMD)

    input("Compare the two tickets to confirm truncate WS works\nPress Enter to continue...\n")
    
    return checkSuccess(f"TRUNCATE_WS", test_entry)

def test_pullTabMode(ser, device, test_entry: TestEntry):
    response = write_command(device, "SET_PULL_TAB_MODE", EN)
    if response == "NAK":
        print("Failed to set pull tab mode")
        return
    
    ser.write(b'PULL TAB ENABLED\n')
    ser.write(b'This is a test of the pull tab mode.\n')
    ser.write(PRNT_CMD)

    input("Observe ticket!\nPress Enter to continue...\n")

    response = write_command(device, "SET_PULL_TAB_MODE", DIS)
    if response == "NAK":
        print("Failed to set pull tab mode")
        return
    
    ser.write(b'PULL TAB DISABLED\n')
    ser.write(b'This is a test of the pull tab mode.\n')
    ser.write(PRNT_CMD)

    input("Observe ticket!\nPress Enter to continue...\n")

    return checkSuccess(f"PULL_TAB", test_entry)

def convert_to_percentage(value):
    percentage_map = {
        6: "10%",
        5: "20%",
        4: "30%",
        3: "40%",
        2: "50%",
        1: "60%",
        0: "70%",
        -1: "80%",
        -2: "90%",
        -3: "100%"
    }
    return percentage_map.get(value, "Disabled")  # Default case


def test_fonts(ser, device, test_entry: TestEntry):

    input("Font features will be tested.\nincluding custom characters per inch (CPI) and the CPI lock." \
    "\nPASS CONDITIONS:" \
    "\n - CPI changes accordingly" \
    "\n - Custom CPI shows the different spacing between each setting" \
    "\n - Lock CPI prevents the font from changing" \
    "\nPress Enter to begin...")
    #time.sleep(1)
    #response = write_command(device, "PRINT_FONT_PAGE")
    #if response == "NAK":
    #    print("Failed to set font")
    #    return

    input("Go onto Reliance Tools and select the font page.\nThen hit APPLY AND TEST PRINT \nEnsure all code pages and CPIs are displayed.\nPress enter to continue...")

    print("Testing custom CPI options")
    for i in range(-3, 7):
        if i == 0:
            response = write_command(device, "SET_CUSTOM_CPI", int(format(7 & 0xFF, '02X'), 16))
        else:    
            response = write_command(device, "SET_CUSTOM_CPI", int(format(i & 0xFF, '02X'), 16))
        if response == "NAK":
            print("Failed to set font")
            return    
        ser.write(f"CUSTOM CPI AT {convert_to_percentage(i)}".encode('utf-8'))
        ser.write(LF_CMD)
        time.sleep(.1)
    ser.write(PRNT_CMD)
    input("Observe ticket!\nPress Enter to continue...\n")#


    response = write_command(device, "SET_CUSTOM_CPI", DIS)
    if response == "NAK":
        print("Failed to disable custom CPI")
        return
    
    print("Testing Lock CPI")
    response = write_command(device, "SET_LOCK_CPI", DIS)
    if response == "NAK":
        print("Failed to set font")
        return
    
    time.sleep(1)
    ser.write([0x1B, 0xC1, 0x00])
    ser.write(b'LOCK CPI DISABLED\n')
    time.sleep(.2)
    ser.write([0x1B, 0xC1, 0x01])   
    ser.write(b'LOCK CPI DISABLED\n')
    time.sleep(.2)
    ser.write([0x1B, 0xC1, 0x02])
    ser.write(b'LOCK CPI DISABLED\n')
    ser.write(b'\nThe above should all\n be different widths')
    ser.write(PRNT_CMD)
    time.sleep(.2)

    response = write_command(device, "SET_LOCK_CPI", EN)
    if response == "NAK":
        print("Failed to set font")
        return
    
    time.sleep(1)
    ser.write([0x1B, 0xC1, 0x00])
    ser.write(b'LOCK CPI ENABLED\n')
    time.sleep(.2)
    ser.write([0x1B, 0xC1, 0x01])
    ser.write(b'LOCK CPI ENABLED\n')
    time.sleep(.2)
    ser.write([0x1B, 0xC1, 0x02])
    ser.write(b'LOCK CPI ENABLED\n')
    ser.write(b'\nThe above should all\n be the same width')
    ser.write(PRNT_CMD)
    time.sleep(1)

    response = write_command(device, "SET_LOCK_CPI", DIS)
    if response == "NAK":
        print("Failed to set font")
        return

    return checkSuccess(f"FONTS", test_entry)

def test_SENTRY_duplicateKeywords(ser, device, test_entry: TestEntry):
    input("This is a SENTRY test. \n>>PAIR PRINTER BEFORE CONTINUING<<" \
          "\nDUPLICATE keywords are meant to suppress the QR code.\n We will test setting a single dup keyword and multiple dup keywords."\
          "\nPASS CONDITIONS:" \
          "\n - DUPLICATE keyword suppresses the QR code correctly." \
          "\n - Tickets without the keyword display the QR code AND Value error" \
          "\nPress Enter to continue...\n")

    response = write_command(device, "SET_DUPLICATE_KEYWORD", [0x4D, 0x41, 0x49, 0x4E, 0x54, 0x45, 0x4E, 0x41, 0x4E, 0x43, 0x45] + [0x00] * 9)
    if response == "NAK":
        print("Failed to set duplicate keywords")
        return
    
    ser.write(b'DUP KEYWORD TESTING\n')
    ser.write(b'KEYWORD: MAINTENANCE\n')
    ser.write(b'\nThere should be no QR code\n on this ticket!\n')
    ser.write(PRNT_CMD)

    time.sleep(2)

    ser.write(b'DUP KEYWORD TESTING\n')
    ser.write(b'This one should have a QR code!\n')
    ser.write(PRNT_CMD)
    
    input("Observe ticket!\nPress Enter to continue...\n")

    response = write_command(device, "SET_MULTI_DUPKEY", [0x00, 0x55, 0x4C, 0x54, 0x52, 0x41, 0x4C, 0x49, 0x47, 0x48, 0x54, 0x42, 0x45, 0x41, 0x4D] + [0x00] * 6)
    if response == "NAK":
        print("Failed to set duplicate keywords")
        return

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'KEYWORD: ULTRALIGHTBEAM\n\n')
    ser.write(b'\nThere should be no QR code\n on this ticket!\n')
    ser.write(PRNT_CMD)

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'This one SHOULD have a QR code!\n')
    ser.write(PRNT_CMD)
    
    time.sleep(2)
    
    response = write_command(device, "SET_MULTI_DUPKEY", [0x01, 0x4E, 0x45, 0x56, 0x45, 0x52, 0x45, 0x4E, 0x44, 0x45, 0x52] + [0x00] * 10)
    if response == "NAK":
        print("Failed to set duplicate keywords")
        return

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'KEYWORD: NEVERENDER\n\n')
    ser.write(b'\nThere should be no QR code\n on this ticket!\n')
    ser.write(PRNT_CMD)

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'This one SHOULD have a QR code!\n')
    ser.write(PRNT_CMD)
    
    time.sleep(2)

    response = write_command(device, "SET_MULTI_DUPKEY", [0x02, 0x4C, 0x55, 0x43, 0x4B, 0x59, 0x43, 0x41, 0x54] + [0x00] * 12)
    if response == "NAK":
        print("Failed to set duplicate keywords")
        return

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'KEYWORD: LUCKYCAT\n\n')
    ser.write(b'\nThere should be no QR code\n on this ticket!\n')
    ser.write(PRNT_CMD)

    ser.write(b'MULTI-DUP KEYWORD TESTING\n')
    ser.write(b'This one SHOULD have a QR code!\n')
    ser.write(PRNT_CMD)
    
    return checkSuccess(f"DUPLICATE_KEY", test_entry)

def test_SENTRY_config(ser, device, test_entry: TestEntry):
    sentry = Sentry()
    print("80mm paper required.\n")
    input ("This is a SENTRY test. \n>>PAIR PRINTER<<\n>>CONNECT A USB QR SCANNER<<\n" \
           "\nSENTRY config will be tested, including:"\
           "\nSENTRY keywords, case sensitivity, line parse, skip parse."\
           "\nPASS CONDITIONS:" \
           "\n - SENTRY keywords are parsed correctly and shows valid tickets" \
           "\n - SENTRY case sensitivity raises a value error for incorrect case" \
           "\n - SENTRY line parses the correct line" \
           "\n - SENTRY skip parse skips the correct number of instances of the keyword" \
           "\nPress Enter to continue...\n")
    response = write_command(device, "SET_PAPER_SIZE", 80)
    if response == "NAK":
        print("Failed to set paper size")
        return
     
    while(1):
        try:
            pairing_code = input("Pairing Code: ")
            sentry.pair(pairing_code)
            break
        except Exception as e:
            print(f"Error pairing with SENTRY: {e}")
    
    print("\nSENTRY Keyword Test\n------------\n")
    # Set SENTRY config to:
    # Keyword parse, keyword: "WINNER"
    # case, skip, parse disabled
    print("Keyword: WINNER")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x02, 0x57, 0x49, 0x4E, 0x4E, 0x45, 0x52] + [0x00] * 14 +[0x00, 0x00, 0x00])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    ser.write(b'SENTRY CONFIG TESTING\n')
    ser.write(b'WINNER $32.00\n')
    ser.write(PRNT_CMD)

    redemption = input("Scan ticket to redeem: ")
    is_valid, is_duplicate, timestamp_redemption = sentry.validate_ticket(redemption)
    if is_valid:
        print(f"VALID")
    else:
        print("INVALID TICKET")
    
    # Set SENTRY config to:
    # Keyword parse, keyword: "antiestablishmentism"
    # case, skip, parse disabled
    print("\nKeyword: antiestablishmentism")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x02, 0x61, 0x6E, 0x74, 0x69, 0x65, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x6D, 0x65, 0x6E, 0x74, 0x69, 0x73, 0x6D] +[0x00, 0x00, 0x00])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    ser.write(b'SENTRY CONFIG TESTING\n')
    ser.write(b'antiestablishmentism $21.00\n')
    ser.write(PRNT_CMD)

    redemption = input("Scan ticket to redeem: ")
    is_valid, is_duplicate, timestamp_redemption = sentry.validate_ticket(redemption)
    if is_valid:
        print(f"VALID")
    else:
        print("INVALID TICKET")

    print("\nCase sensitive test")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x02, 0x61, 0x6E, 0x74, 0x69, 0x65, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x6D, 0x65, 0x6E, 0x74, 0x69, 0x73, 0x6D] +[0x01, 0x00, 0x00])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    ser.write(b'SENTRY CONFIG TESTING\n')
    ser.write(b'antiestaBlishMentism $21.00\n')
    ser.write(b'This ticket should have a value error\n')
    ser.write(PRNT_CMD)

    input("Ticket should dispaly error message\nPress Enter to continue...\n")

    print("Line parse test\nSet to parse 3rd line")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x03, 0x61, 0x6E, 0x74, 0x69, 0x65, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x6D, 0x65, 0x6E, 0x74, 0x69, 0x73, 0x6D] +[0x00, 0x00, 0x03])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    ser.write(b'SENTRY CONFIG TESTING\n')
    ser.write(b'antiestablishmentism $3.00\n')
    ser.write(b'antiestablishmentism $1.00\n')
    ser.write(b'antiestablishmentism $5.00\n')
    ser.write(b'antiestablishmentism $9.00\n')
    ser.write(PRNT_CMD)

    redemption = input("Scan ticket to redeem: ")
    is_valid, is_duplicate, timestamp_redemption = sentry.validate_ticket(redemption)
    if is_valid:
        print(f"VALID")
    else:
        print("INVALID TICKET")
    parsed_redemption = sentry.parse(redemption)
    payout = parsed_redemption.split(",")[0].split(" ")[1]  
    if payout == "$1.00":
        print(f"Payout is correct: {payout}\n")
    else:
        print(f"Payout is incorrect: {payout}")

    print("\nSkip parse test\nSet to skip 3 occurances")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x04, 0x61, 0x6E, 0x74, 0x69, 0x65, 0x73, 0x74, 0x61, 0x62, 0x6C, 0x69, 0x73, 0x68, 0x6D, 0x65, 0x6E, 0x74, 0x69, 0x73, 0x6D] +[0x00, 0x03, 0x00])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    ser.write(b'SENTRY CONFIG TESTING\n')
    ser.write(b'antiestablishmentism $3.00\n')
    ser.write(b'antiestablishmentism $1.00\n')
    ser.write(b'antiestablishmentism $5.00\n')
    ser.write(b'antiestablishmentism $9.00\n')
    ser.write(PRNT_CMD)

    redemption = input("Scan ticket to redeem: ")
    is_valid, is_duplicate, timestamp_redemption = sentry.validate_ticket(redemption)
    if is_valid:
        print(f"VALID")
    else:
        print("INVALID TICKET")
    parsed_redemption = sentry.parse(redemption)
    payout = parsed_redemption.split(",")[0].split(" ")[1]  
    if payout == "$9.00":
        print(f"Payout is correct: {payout}\n")
    else:
        print(f"Payout is incorrect: {payout}")

    return checkSuccess(f"SENTRY_CONFIG", test_entry)

def test_SENTRY_qrTimeStamp (ser, device, test_entry: TestEntry):
    sentry = Sentry()
    input ("This is a SENTRY test. \n>>PAIR PRINTER<<\n>>CONNECT A USB QR SCANNER<<\n" \
           "\nSENTRY QR Time stamp will be tested."\
           "\nEach QR will be assigned a random time stamp."\
           "\nPASS CONDITIONS:" \
           "\n - Time stamp set and read from the QR code match" \
           "\n - All tickets are valid" \
           "\nPress Enter to continue...\n")
    
    
    qty = input("Enter number of tickets to print: ")

    while(1):
        try:
            pairing_code = input("Pairing Code: ")
            sentry.pair(pairing_code)
            break
        except Exception as e:
            print(f"Error pairing with SENTRY: {e}")


    response = write_command(device, "SEN_QR_TS_CFG", EN)
    if response == "NAK":
        print("Failed to enable QR timestamp")
        return

    # Set SENTRY config to:
    # Keyword parse, keyword: "WINNER"
    # case, skip, parse disabled
    print("Keyword: WINNER")
    response = write_command(device, "SET_SENTRY_CONFIG", [0x02, 0x57, 0x49, 0x4E, 0x4E, 0x45, 0x52] + [0x00] * 14 +[0x00, 0x00, 0x00])  
    if response == "NAK":
        print("Failed to set SENTRY config")
        return
    for i in range(int(qty)):
        timestamp = get_random_timestamp()
        timestamp = timestamp.replace(second=0, microsecond=0)  # Create a new datetime object with seconds set to 0
        timestamp_bytes = datetime_to_bytes(timestamp)

        # Convert timestamp_bytes to a list
        timestamp_bytes_list = list(timestamp_bytes)  

        # timestamp + 0x00 (for the seconds byte)
        response = write_command(device, "SET_RTC", timestamp_bytes_list + [0x00])
        if response == "NAK":
            print("Failed to set RTC")
            return

        # Print ticket
        ser.write(b'WINNER $23.00\n')
        ser.write(b'\x0C')


        redemption = input("Redemption TKT: ")
        is_valid, is_duplicate, timestamp_redemption = sentry.validate_ticket(redemption)
        if is_valid:
            print(f"VALID")
            if timestamp == timestamp_redemption:
                print(f"TS MATCH: {timestamp}\n")
            else:
                print("Timestamp does not match!")
                print(f"Generated TS: {timestamp}")
                print(f"Redemption TS: {timestamp_redemption}")
    
    return checkSuccess(f"SENTRY_QR_TIMESTAMP", test_entry)

def test_ESCPOS(ser, device, test_entry: TestEntry):
    
    if getattr(sys, 'frozen', False):
    # Running in a bundle (e.g., PyInstaller)
        base_path = sys._MEIPASS
    else:
    # Running in a normal Python environment
        base_path = os.path.dirname(__file__)

    file_path = os.path.join(base_path, "main.bin")

    time.sleep(1)
    print("Attempting to unpair. If already unpaired, you will see a NAK response")
    response = write_command(device, "GET_SENTRY_CONFIG")
    if response[1][0] == 0x01:  
        # Unpair printer to reset SENTRY
        print("Unpairing printer...")
        response = write_command(device, "SET_SENTRY_CONFIG", [0x00] + [0x00] * 20 +[0x00, 0x00, 0x00])  
        if response == "NAK":
            print("Failed to set SENTRY config")
            return
    input("\n\nAbout to test all ESC/POS commands\nTons of tickets will print!\nPress Enter to continue...\n")
    
    while True:
        try:
            # Open the binary file in read-binary mode
            with open(file_path, "rb") as binary_file:
                # Read the file in chunks and write to the serial port
                while chunk := binary_file.read(1024):  # Read in 1KB chunks
                    ser.write(chunk)
                    time.sleep(0.1)  # Optional: Add a small delay to ensure data is sent properly
                break
        except Exception as e:
            print(f"Could not find file. Please enter the path to main.bin\n (should be in the same folder as this exe): {e}")
            try:
                # Prompt user for the path to the binary file
                file_path = input("Enter the full path to main.bin: ").strip()
                with open(file_path, "rb") as binary_file:
                    # Read the file in chunks and write to the serial port
                    while chunk := binary_file.read(1024):  # Read in 1KB chunks
                        ser.write(chunk)
                        time.sleep(0.1)  # Optional: Add a small delay to ensure data is sent properly
                    break
            except Exception as e:
                print(f"Error reading the provided file path: {e}")
                continue
    return checkSuccess(f"ESC_POS", test_entry)

def test_pageESCPOS(ser, device, test_entry: TestEntry):
    
    if getattr(sys, 'frozen', False):
    # Running in a bundle (e.g., PyInstaller)
        base_path = sys._MEIPASS
    else:
    # Running in a normal Python environment
        base_path = os.path.dirname(__file__)

    file_path = os.path.join(base_path, "page_main.bin")

    time.sleep(1)
    print("Attempting to unpair. If already unpaired, you will see a NAK response")
    response = write_command(device, "GET_SENTRY_CONFIG")
    if response[1][0] == 0x01:  
        # Unpair printer to reset SENTRY
        print("Unpairing printer...")
        response = write_command(device, "SET_SENTRY_CONFIG", [0x00] + [0x00] * 20 +[0x00, 0x00, 0x00])  
        if response == "NAK":
            print("Failed to set SENTRY config")
            return
    input("\n\nAbout to test all ESC/POS commands\nTons of tickets will print!\nPress Enter to continue...\n")

    
    while True:
        try:
            # Open the binary file in read-binary mode
            with open(file_path, "rb") as binary_file:
                # Read the file in chunks and write to the serial port
                while chunk := binary_file.read(1024):  # Read in 1KB chunks
                    ser.write(chunk)
                    time.sleep(0.1)  # Optional: Add a small delay to ensure data is sent properly
                break
        except Exception as e:
            print(f"Could not find file. Please enter the path to main.bin\n (should be in the same folder as this exe): {e}")
            try:
                # Prompt user for the path to the binary file
                file_path = input("Enter the full path to main.bin: ").strip()
                with open(file_path, "rb") as binary_file:
                    # Read the file in chunks and write to the serial port
                    while chunk := binary_file.read(1024):  # Read in 1KB chunks
                        ser.write(chunk)
                        time.sleep(0.1)  # Optional: Add a small delay to ensure data is sent properly
                    break
            except Exception as e:
                print(f"Error reading the provided file path: {e}")
                continue
    return checkSuccess(f"ESC_POS", test_entry)