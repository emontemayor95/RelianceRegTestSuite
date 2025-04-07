#Tests
#################################
#Print Config tests

#Print quality
#Print density
#paper slack
#Ticket retraction
#Ejector mode
#Ticket timeout
#Timeout action
#New ticket action
#Present length
#Carriage return
#Line feed enable
#Autocut
#Auto cut timeout
#Start up ticket
#ESC/POS Line Spacing
#Pull tab mode
#Lock CPI

################################
#Sentry tests
#Default font spacing
#Duplicate keywords
#Custom keyword
#   Case sensitive, skip, pre-parsing keyword
#Exact line 

################################
#Font config tests
#Advanced font spacing
#Modern (tall) vs Classic (short)


import hid
import serial
from commands import * 
from testManager import *

### HID Comms Parameters ##
VENDOR_ID = 0x0425
PRODUCT_ID = 0x8147
TX_ID = 1 
RX_ID = 2  

## Serial Port Parameters ##
SERIAL_PORT = 'COM3'  
baudrate = 19200 

if __name__ == "__main__":
    while True:
        com_num = input("Enter COM port NUMBER for serial connection (e.g., 3): ")
        if not com_num.isdigit():
            print("Invalid input. Please enter a numeric value.")
            continue
        SERIAL_PORT = 'COM' + com_num
        try: 
            # Open serial port
            ser = serial.Serial(SERIAL_PORT, baudrate, timeout=1) 
        except Exception as e:
            print(f"Error opening serial port {SERIAL_PORT}: {e}")
            continue  
        try: 
            # Open USB HID device
            device = hid.device()
            device.open(VENDOR_ID, PRODUCT_ID)
            device.set_nonblocking(0)  # 0 means blocking mode
            break
        except Exception as e:
            print(f"Error opening USB HID device: {e}")
            ser.close()
            device.close()
            continue

    print ("\n========================")
    # Ping to check if the device is connected
    response = write_command(device, "PING")
    if response == "NAK":
        print("Device not responding")
        exit(1)
    else:
        print("Device connected")
    # Set serial config 
    # 19200 baud, 8N1, no handshaking
    response = write_command(device, "SET_SERIAL")
    if response == "NAK":
        print("Failed to set serial configuration")
        exit(1)
    else:
        print("Serial configuration set\n")
    
    print ("CONNECTION SUCCESSFUL")
    print ("BEGINNING TESTS")
    print ("========================\n")
    
    TESTS = {
        "JAM_RETRACTION_58MM": TestEntry(
            "JAM_TST_RETRACTION_56MM", 
            False, 
            test_jamTestingRetractionMode, 
            [ser, device, 6, 58]),  #args: ser,device, quantity, mm
        "JAM_CONTINUOUS_58MM": TestEntry(
            "JAM_CONTINUOUS_56MM", 
            False, 
            test_jamTestingContinuousMode, 
            [ser, device, 6, 58]),  #args: ser,device, quantity, mm
        "JAM_RETRACTION_80MM": TestEntry(
            "JAM_RETRACTION_80MM", 
            False, 
            test_jamTestingRetractionMode, 
            [ser, device, 6, 80]),  #args: ser,device, quantity, mm
        "JAM_CONTINUOUS_80MM": TestEntry(
            "JAM_CONTINUOUS_80MM", 
            False, 
            test_jamTestingContinuousMode, 
            [ser, device, 6, 80]),  #args: ser,device, quantity, mm
        "PRINT_QUALITY": TestEntry(
            "PRINT_QUALITY",
            False, 
            test_printQuality, 
            [ser, device, 6]),  #args: ser,device, quantity
        "PRESENT_LENGTH": TestEntry(
            "PRESENT_LENGTH", 
            False, 
            test_presentLength, 
            [ser, device]),  #args: ser,device
        "CRLF": TestEntry(
            "CRLF", 
            False, 
            test_CRLF, 
            [ser, device]),  #args: ser,device, quantity
        "AUTOCUT": TestEntry(
            "AUTOCUT", 
            False, 
            test_autocut, 
            [ser, device]),  #args: ser,device, quantity       
        "TRUNCATE_WS": TestEntry(
            "TRUNCATE_WS", 
            False, 
            test_truncateWS, 
            [ser, device]),  #args: ser,device, quantity
        #"PULL_TAB": TestEntry(     #Only useful for pull tab paper, disabled for now
        #    "PULL_TAB", 
        #    False, 
        #    test_pullTabMode, 
        #    [ser, device]),  #args: ser,device, quantity
        "FONTS": TestEntry(
            "FONTS", 
            False, 
            test_fonts, 
            [ser, device]),  #args: ser,device, quantity
        "DUPLICATE_KEY": TestEntry(
            "DUPLICATE_KEY", 
            False, 
            test_SENTRY_duplicateKeywords, 
            [ser, device]),  #args: ser,device, quantity
        "SENTRY_CONFIG": TestEntry(  
            "SENTRY_CONFIG", 
            False, 
            test_SENTRY_config, 
            [ser, device]),  #args: ser,device, quantity       
        "SENTRY_QRTS": TestEntry(  
            "SENTRY_QRTS", 
            False, 
            test_SENTRY_qrTimeStamp, 
            [ser, device]),  #args: ser,device, quantity  
        "ESC_POS": TestEntry(  
            "ESC_POS", 
            False, 
            test_ESCPOS, 
            [ser, device]),  #args: ser,device, quantity    
    }

print ("Welcome to the Reliance Test Suite!\n")
while True:
    selection = input("Run all tests (r)\nSelect specific tests (s)\nEnter: ").strip().lower()
    if selection != "r" and selection != "s":
        print("Invalid input. Please enter 'r' or 's'.")
        continue
    break

tests_todo = []
tests_completed = []
if selection == "s":
    print("Available tests:")
    for test_name in TESTS.keys():
        print(f"- {test_name}")
    while True:
        selected_tests = input("Enter the names of the tests you want to run (comma-separated): ").strip().split(",")
        selected_tests = [test.strip() for test in selected_tests if test.strip() in TESTS]
        if not selected_tests:
            print("No valid tests selected. Please try again.")
            continue
        break

    tests_todo = [TESTS[test_name] for test_name in selected_tests] 
elif selection == "r": 
    for test_name, test_entry in TESTS.items():  
        tests_todo.append(test_entry)  

try:        
    while tests_todo:
        # Iterate through all tests and run them
        for test_entry in tests_todo[:]:  
            print(f"\nRunning {test_entry.name}...")  
            test_entry.run()  #
            print("--------------------------------------")

        # Print results of all tests
        for test_entry in tests_todo[:]:  
            print("*************************************")
            if test_entry.success:
                tests_todo.remove(test_entry)  # Remove passed tests
                if test_entry in tests_completed:
                    tests_completed.remove(test_entry)  
                tests_completed.append(test_entry) 
                print(f"{test_entry.name} ... PASSED")
            else:
                if test_entry in tests_completed:
                    tests_completed.remove(test_entry)                  
                tests_completed.append(test_entry)
                print(f"{test_entry.name} ... >>>>>> FAILED <<<<<")
            print("*************************************")
        
        if not tests_todo:
            print("\nAll tests passed!")
            break
        else:
            while True:
                status = input(f"Repeat failed tests? (y/n): ").strip().lower()
                if status in ['y', 'n']:
                    break
                print("Invalid input. Please enter 'y' or 'n'.")

            if status == 'n':
                break
            else:
                print("Repeating failed tests...\n")
    
    with open("test_results.txt", "w") as results_file:
        results_file.write(f"    RELIANCE FIRMWARE\n      TEST RESULTS\n*************************")
        for test_entry in tests_completed:
            status = "PASSED" if test_entry.success else ">FAILED<"
            results_file.write(f"\n{test_entry.name}: {status}\n*************************")
    print ("\nTest results saved to test_results.txt")
    
finally:
    if ser.is_open:
        ser.close()
        print("\nSerial connection closed.")
    try:
        device.close()
        print("USB HID device closed.\n")
    except Exception:
        pass


