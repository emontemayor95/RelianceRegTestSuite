# -*- coding: utf-8 -*-
"""
@file sentry_test
@author cory
@created 7/16/2020
@brief Sentry POC
"""
# standard library
import array
import base64
import collections
import datetime
import hashlib
import io
import logging
import math
import os
import shutil
import struct
import sys

# vendor library
try:
    # PIL can be a pain to install so make it optional
    import qrcode

    QR_ENABLED = True
except ImportError:
    #print("qrcode is not installed. Cannot generate qrcodes.")
    QR_ENABLED = False

try:
    import numpy as np
    # pip install pycryptodome
    from Crypto.Cipher import AES
except:
    print("Emu Sentry missing nump and/or AES")

# local module - None

file_handler = logging.FileHandler(filename='sentry_emulator.log')
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('LOGGER_NAME')


def get_b64_len(s):
    return math.ceil(len(s) / 3) * 4


def get_random_timestamp() -> datetime:
    # generate random time since January 1, 2023
    first_date = datetime.datetime(2023, 1, 1)
    last_date = datetime.datetime.now()
    days = (last_date - first_date).days
    random_days = np.random.randint(days)
    random_date = first_date + datetime.timedelta(days=random_days)
    random_time_of_day = datetime.time(np.random.randint(24), np.random.randint(60), np.random.randint(60))
    return datetime.datetime.combine(random_date, random_time_of_day)

def get_timestamp_bytes(timestamp: datetime) -> bytes:
    # first byte is the last two digits of the year
    # next three bytes is the minute of that year
    last_two_digits_of_year = int(timestamp.year - 2000)
    time_bytes: bytes = struct.pack('B', last_two_digits_of_year)
    day_of_year: int = timestamp.timetuple().tm_yday
    minutes  = int(timestamp.minute) + int(timestamp.hour) * 60 + int(day_of_year - 1) * 24 * 60
    time_bytes += struct.pack('>I', minutes)[1:]

    return time_bytes

def decode_timestamp_bytes(time_bytes: bytes) -> datetime.datetime:
    year = 2000 + int.from_bytes(time_bytes[0:1], byteorder='big')
    minutes = int.from_bytes(time_bytes[1:4], byteorder='big')
    day = minutes // (24 * 60)
    hour = (minutes - day * 24 * 60) // 60
    minute = minutes - day * 24 * 60 - hour * 60
    return datetime.datetime(year, 1, 1) + datetime.timedelta(days=day, hours=hour, minutes=minute)


def make_hex_string(id_buff):
    """Create id string from raw id bytes"""
    sb = io.StringIO()
    for b in id_buff:
        sb.write("{:02X}".format(b))
    return sb.getvalue()


def make_buffer(id_str):
    """Convert hex string back to a buffer"""
    bb = []
    for ch in [id_str[i:i + 2] for i in range(0, len(id_str), 2)]:
        bb.append(int(ch, 16))
    return np.asarray(bb).astype(np.uint8)


def pretty_payout(payout):
    """Add currency symbols to make payout readable
            0002700 -> $27.00
        :param payout unsymbolized payout value
        :return Pretty currency string
    """
    sb = io.StringIO()

    # Iterate backwards
    for i, ch in enumerate(payout[::-1]):
        sb.write(ch)

        if i == 1:
            sb.write('.')
        elif i == 4:
            sb.write(',')
    pretty = sb.getvalue()[::-1].lstrip('0').lstrip(',').lstrip('0')
    return "${}".format(pretty
                        )


def expand_iv(iv):
    """Applies expansion rule to convert 4-byte IV to 16-byte IV"""
    if type(iv) is bytes:
        return iv * 4
    return np.tile(iv, 4)


def make_infinite_payout(provider):
    """Returns a generator that repeats the payout of this provider forever
        :param provider file type
        :return string generator
    """

    def fn():
        while True:
            for line in provider:
                yield line.strip()

            provider.seek(0)

    return fn


def make_infinite_security(provider):
    """Returns a generator that repeats the security triplets of this provider forever
        :param provider file type
        :return string generator
    """

    def fn():
        j = 0
        for _j, _ in enumerate(provider):
            j = _j
        provider.seek(0)
        lines = collections.deque(provider, maxlen=j + 1)
        for line in lines:
            # Split into parts convert into numbers
            pid, key, iv = line.split()
            pid = make_buffer(pid)
            key = make_buffer(key)
            iv = make_buffer(iv)
            yield pid, key, iv

    return fn


class PhoenixU23(object):
    """Phoenix firmware implementation modeling"""
    CTRL_PAIRING = 'X'
    CTRL_REDEEM_NON_TIMESTAMP = 'Y'
    CTRL_REDEEM_TIMESTAMP = 'Z'

    LEN_PAIRING = 46
    LEN_REDEEM = 41

    def __init__(self, sn, payout_provider=None, security_provider=None, use_timestamp=True):
        """Create a new Phoenix with the specified 9-digit serial number"""
        if sn is None or len(sn) != 9:
            raise Exception("Invalid serial number")

        self.sn = sn
        self.pid = None
        self.key = None
        self.iv = None
        self.nonce = 0
        self.last_pairing_code = None
        self.use_timestamp = use_timestamp
        self.redemption_control_code = self.CTRL_REDEEM_TIMESTAMP if use_timestamp else self.CTRL_REDEEM_NON_TIMESTAMP

        if payout_provider is None:
            def p():
                while True:
                    yield self.__random_payout()
        else:
            p = make_infinite_payout(payout_provider)
        self.payout_provider = p

        if security_provider is None:
            def r():
                while True:
                    yield self.__random_security()
        else:
            # Make an infinite loop out of this file provider
            r = make_infinite_security(security_provider)
        self.security_provider = r

    def make_pairing_string(self):
        """Generate a new set of pairing codes for this printer
            [ctrl] [sn#] [base64 payload]
                        >[printer id] [IV] [Key]
            :return pairing codes encoded as pairing string
        """
        self.pid, self.key, self.iv = self.get_next_security()
        logger.info("PHX SN#{} generated new pairing code".format(self.sn))

        to_encode = io.BytesIO()
        [to_encode.write(x) for x in self.pid]
        [to_encode.write(x) for x in self.iv]
        [to_encode.write(x) for x in self.key]

        encoded = base64.b64encode(to_encode.getvalue()).decode('utf-8')

        self.last_pairing_code = "{}{}{}".format(PhoenixU23.CTRL_PAIRING, self.sn, encoded)
        return self.last_pairing_code

    def make_redemption_string(self):
        """Generate a redemption string
            [ctrl] [payout] [base64 payload]
                           >[printer id] [encrypted]
                                        >[payout] [nonce] [padding]
            :return str formatted redemption string
        """
        if self.pid is None:
            raise Exception("Printer is not paired")

        # Pre-increment the nonce so we don't lose it
        self.nonce += 1

        payout = self.get_next_payout()
        if len(payout) != 8 or any([x for x in payout if x < '0' or x > '9']):
            raise Exception("Payout must be 8 ASCII digits")

        logger.debug("PHX SN#{} making redemption for payout: {}".format(self.sn, pretty_payout(payout)))

        # Build encrypted payload first
        v_prime = io.BytesIO()
        v_prime.write(bytes(payout, "utf-8"))
        v_prime.write(struct.pack(">I", self.nonce))
        padding_bytes: bytes = bytes("#$%&", "utf-8")
        if self.use_timestamp: padding_bytes = get_timestamp_bytes(get_random_timestamp())
        v_prime.write(padding_bytes) # THIS WILL BE REPLACED BY TIMESTAMP
        encrypted = self.__encrypt(v_prime)

        # Base 64 the id bytes + encrypted payload
        payload_bytes = io.BytesIO()
        [payload_bytes.write(x) for x in self.pid]
        payload_bytes.write(encrypted)
        encoded_enc = base64.b64encode(payload_bytes.getvalue()).decode('utf-8')
        logger.debug("b64_payload={}".format(encoded_enc))

        return "{}{}{}".format(self.redemption_control_code, payout, encoded_enc)

    def get_next_payout(self):
        """Returns next payout value"""
        return next(self.payout_provider())

    def get_next_security(self):
        """Returns next security triplet"""
        return next(self.security_provider())

    @staticmethod
    def __random_payout():
        """Generate a random payout between 0 and 1e6, exclusive"""
        # ASCII payout values $0.00 to $999,999.99
        pool = list("0123456789")
        rng_payout = np.random.choice(pool, 8)
        return "".join(rng_payout)

    @staticmethod
    def __random_security():
        """Generate random security values
            :return tuple(id, key, iv)
        """
        pid = np.random.randint(0, 255, 6, dtype=np.uint8)
        # IV is 4 bytes which we expand into 16 bytes to save RAM on the MCU
        iv = np.random.randint(0, 255, 4).astype(np.uint8)
        key = np.random.randint(0, 255, 16).astype(np.uint8)
        return pid, key, iv

    def __encrypt(self, payload):
        """Encrypts payout using current pairing state. Payload
            will be padded with random bytes to satisfy 128-bit alignment.
            :param payload to encrypt
            :return encrypted payload
        """
        # Pad to 16 bytes, randomly
        while payload.getbuffer().nbytes % 16 != 0:
            payload.write(struct.pack('B', np.random.randint(0, 255)))

        iv = expand_iv(self.iv).tobytes()

        aes = AES.new(self.key.tobytes(), AES.MODE_CBC, iv)
        block = aes.encrypt(payload.getvalue())
        return block

    def __repr__(self):
        return str(self)

    def __str__(self):
        pid = "" if self.pid is None else make_hex_string(self.pid)
        key = "" if self.key is None else make_hex_string(self.key)
        iv = "" if self.iv is None else make_hex_string(self.iv)
        return "sn:{}, id:{}, key:{}, iv:{}, nonce:{}".format(self.sn, pid, key, iv, self.nonce)

class Sentry(object):
    """Sentry SDK modeling"""

    def __init__(self):
        """Create a new Sentry SDK"""
        # Store as id:tuple(key, iv)
        self.keys = {}
        self.history = set()

    def pair(self, pairing_code):
        """Pair a Phoenix to this Sentry
            :param pairing_code pairing code string
        """
        if pairing_code is None or pairing_code[0] != PhoenixU23.CTRL_PAIRING or len(
                pairing_code) != PhoenixU23.LEN_PAIRING:
            raise Exception("Invalid pairing code: {}".format(pairing_code))

        serial_number = pairing_code[1:10]
        encoded = pairing_code[10:]

        decoded = base64.b64decode(encoded)
        printer_id = decoded[:6]
        secure_iv = decoded[6:10]
        secure_key = decoded[10:]

        id_str = make_hex_string(printer_id)
        logger.debug("SEN: paired to PHX SN#{}, ID#:{}, Key:{}, IV:{}".format(serial_number, id_str,
                                                                              make_hex_string(secure_key),
                                                                              make_hex_string(secure_iv)))

        self.keys[id_str] = (secure_key, secure_iv)

    @staticmethod
    def parse(code):
        """Reads parts of pairing or redemption code
            :param code pairing code string
            :return Parsed code string
        """
        if code is None or type(code) != str:
            return "Invalid pairing code"

        if len(code) == PhoenixU23.LEN_PAIRING:
            if code[0] != PhoenixU23.CTRL_PAIRING:
                return "Pairing is missing control code {}".format(PhoenixU23.CTRL_PAIRING)

            serial_number = code[1:10]
            encoded = code[10:]

            decoded = base64.b64decode(encoded)
            printer_id = decoded[:6]
            secure_iv = decoded[6:10]
            secure_key = decoded[10:]

            return "SN# {}, PID {}, IV={}, AES={}".format(serial_number, make_hex_string(printer_id),
                                                          make_hex_string(secure_iv), make_hex_string(secure_key))

        elif len(code) == PhoenixU23.LEN_REDEEM:
            if code[0] not in (PhoenixU23.CTRL_REDEEM_TIMESTAMP, PhoenixU23.CTRL_REDEEM_NON_TIMESTAMP):
                return "Redemption is missing control code {} or {}".format(PhoenixU23.CTRL_REDEEM_NON_TIMESTAMP, PhoenixU23.CTRL_REDEEM_TIMESTAMP)

            payout = code[1:9]
            encoded = code[9:]

            decoded = base64.b64decode(encoded)
            printer_id = decoded[:6]
            cipher_payout = decoded[6:12]
            cipher_nonce = decoded[12:16]
            cipher_padding = decoded[16:20]

            supports_timestamp = code[0] == PhoenixU23.CTRL_REDEEM_TIMESTAMP
            if supports_timestamp:
                return "Payout {}, PID {}, cipher_payout={}, cipher_nonce={}, timestamp={}, decoded_timestamp={}".format(
                    pretty_payout(payout), make_hex_string(printer_id), make_hex_string(cipher_payout),
                    make_hex_string(cipher_nonce), make_hex_string(cipher_padding), decode_timestamp_bytes(cipher_padding))
            return "Payout {}, PID {}, cipher_payout={}, cipher_nonce={}, cipher_padding={}".format(
                pretty_payout(payout), make_hex_string(printer_id), make_hex_string(cipher_payout),
                make_hex_string(cipher_nonce), make_hex_string(cipher_padding))

        return "Unknown code format"

    def validate_ticket(self, redemption_code):
        """Attempts to validate a redemption code. This code must come from a
            paired printer. The ticket has two attributes:
                valid     TRUE  - the encrypted value matches the claimed value
                          FALSE - the printer is unknown or the encrypted value does not match the claim
                duplicate TRUE  - ticket is valid but has already been redeemed
                          FALSE - ticket is valid and has not been seen by *this* Sentry
            :param redemption_code raw redemption code from QR
            :return tuple(is_valid, is_duplicate)
        """
        if redemption_code is None or redemption_code[0] not in (PhoenixU23.CTRL_REDEEM_NON_TIMESTAMP, PhoenixU23.CTRL_REDEEM_TIMESTAMP) or len(redemption_code) != PhoenixU23.LEN_REDEEM:
            raise Exception("Invalid redemption code: {}".format(redemption_code))

        payout_value = redemption_code[1:9]
        encoded = redemption_code[9:]
        decoded = base64.b64decode(encoded)

        printer_id = decoded[:6]
        id_str = make_hex_string(printer_id)
        if id_str not in self.keys:
            raise Exception("Unknown printer")

        logger.debug(
            "SEN: Validation payout value {} from PHX {}".format(pretty_payout(payout_value), id_str))

        encrypted = decoded[6:]
        secure = self.keys[id_str]

        key = secure[0]
        iv = expand_iv(secure[1])
        aes = AES.new(key, AES.MODE_CBC, iv)

        decrypted = aes.decrypt(encrypted)

        cipher_payout_value = decrypted[:8]
        cipher_nonce = decrypted[8:12]
        cipher_nonce_str = make_hex_string(cipher_nonce)
        logger.debug("SEN: nonce={}".format(cipher_nonce_str))
        cipher_timestamp = decrypted[12:16]  # Only used if timestamp is enabled
        timestamp = decode_timestamp_bytes(cipher_timestamp)  # This will throw if timestamp is invalid
        
        is_valid = payout_value == cipher_payout_value.decode('utf-8')
        is_duplicate = self.check_duplicate(redemption_code, id_str, cipher_nonce_str)

        return is_valid, is_duplicate, timestamp

    def check_duplicate(self, redemption_code, printer_id_str, nonce_str):
        """Fingerprint this redemption attempt to test for duplicates
            :param redemption_code raw redemption code
            :param printer_id_str parsed printer id string
            :param nonce_str parsed nonce counter string
            :return true if this ticket has already been redeemed
        """
        m = hashlib.sha224()
        m.update(redemption_code.encode('utf-8'))
        m.update(printer_id_str.encode('utf-8'))
        m.update(nonce_str.encode('utf-8'))
        key = make_hex_string(m.digest())

        if key in self.history:
            return True
        self.history.add(key)
        return False


def run(iterations, total_printers, payout_source, security_source, make_qrcodes, write_text_file, except_on_error):
    """Run the emulator
        :param iterations int total validations to attempt
        :param total_printers int count of printers to add to pool
        :param payout_source file provides set of payout values. If None, random payouts
               will be used.
        :param security_source file provides set of security id/key/iv triplets. If None,
               random values will be generated.
        :param make_qrcodes bool true to generate QR codes for all pairing and redemptions
        :param write_text_file bool true to write generated values to text files
        :param except_on_error bool true to raise exception if validation fails. This
               excludes emulation bugs which will always through. Only value mismatch
               and duplicate tickets will be raised.
    """

    def make_sn(c):
        return "{:09}".format(c)

    total_printers = int(total_printers)
    iterations = int(iterations)

    # If the import failed, quietly disable qrcodes
    make_qrcodes = make_qrcodes and QR_ENABLED

    data_dir = os.path.join(os.getcwd(), 'data')
    pairing_code_dir = os.path.join(data_dir, 'pairing_codes')
    redemption_code_dir = os.path.join(data_dir, 'redemption_codes')
    pairing_code_file = os.path.join(pairing_code_dir, "a_small_pairing_codes.txt")
    redemption_code_file = os.path.join(redemption_code_dir, "a_small_redemption_codes.txt")

    # Data directory setup
    if make_qrcodes or write_text_file:
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)
        if not os.path.exists(pairing_code_dir):
            os.mkdir(pairing_code_dir)
        if not os.path.exists(redemption_code_dir):
            os.mkdir(redemption_code_dir)

    sen = Sentry()

    # Generate all printers at once so each has an equal chance of selection
    phx_list = []
    for i in range(total_printers):
        phx = PhoenixU23(make_sn(i), payout_source, security_source)
        phx_list.append(phx)

        new_pairing_code = phx.make_pairing_string()

        logger.debug("Pairing code: {}".format(new_pairing_code))

        sen.pair(new_pairing_code)

        if make_qrcodes:
            qr = qrcode.make(new_pairing_code)
            f_name = os.path.join(pairing_code_dir, "p_{:09}.png".format(len(sen.keys)))
            qr.save(f_name)

        if write_text_file:
            with open(pairing_code_file, 'a') as d:
                d.write("{}\n".format(new_pairing_code))

    for counter in range(iterations):

        phx = np.random.choice(phx_list)

        logger.info("#{} Phoenix: {}".format(counter, phx))

        # Make a random new payout/redemption string
        next_redemption_code = phx.make_redemption_string()
        logger.info("Redemption Code: '{}' (len={})".format(next_redemption_code, len(next_redemption_code)))

        if make_qrcodes:
            qr = qrcode.make(next_redemption_code)
            f_name = os.path.join(redemption_code_dir, "r_{:09}.png".format(counter))
            qr.save(f_name)

        if write_text_file:
            with open(redemption_code_file, 'a') as d:
                d.write("{}\n".format(next_redemption_code))

        # Perform the actual validation
        valid, duplicate = sen.validate_ticket(next_redemption_code)

        if except_on_error and not valid:
            logger.error("Invalid redemption: {}, {}".format(phx.last_pairing_code, next_redemption_code))
            logger.error("AES: key={}, iv={}".format(phx.key, phx.iv))
            raise Exception("Test Failure : Validation Failure")

        if except_on_error and duplicate:
            logger.error("Duplicate redemption: {}, {}".format(phx.last_pairing_code, next_redemption_code))
            logger.error("AES: key={}, iv={}".format(phx.key, phx.iv))
            raise Exception("Test Failure : Duplicate Ticket")


def decode_pairing():
    raw = "X000000000MDAwMDAxAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    sen = Sentry()
    sen.pair(raw)


def raw_decryption_test():
    payload = array.array('B',
                          [0x56, 0x8D, 0xF6, 0x40, 0x15, 0x65, 0xF1, 0x99, 0x61, 0x36, 0xF5, 0x12, 0xF5, 0x14, 0x51,
                           0x81]).tobytes()
    key = array.array('B', [0xFF] * 16).tobytes()
    iv = array.array('B',
                     [0x42, 0x80, 0x42, 0x81, 0x12, 0x10, 0xB4, 0x81, 0x67, 0x00, 0x00, 0x02, 0x46, 0x81, 0x02,
                      0x81]).tobytes()

    dn = AES.new(key, AES.MODE_CBC, iv)

    decrypted = dn.decrypt(payload)
    print(make_hex_string(decrypted))

    en = AES.new(key, AES.MODE_CBC, iv)
    actual = en.encrypt("XXXXXXValueError")
    print(make_hex_string(actual))


def encryption_test():
    message = "XXXXXXValueError"
    key = array.array('B', [0xFF] * 16).tobytes()
    iv = array.array('B', [0x00] * 16).tobytes()

    en = AES.new(key, AES.MODE_CBC, iv)
    dn = AES.new(key, AES.MODE_CBC, iv)

    cipher_message = en.encrypt(message)
    print(make_hex_string(cipher_message))

    plaintext_message = dn.decrypt(cipher_message)
    print(plaintext_message)


def quick_test():
    r = "Y00002700VVVVVVVVLFxhHx0Jemyb6etjL/Nn3Q=="
    p = "X000000001VVVVVVVVISIjJBESExQVFhcYGRobHB0eHyA="

    sen = Sentry()
    sen.pair(p)

    ret = sen.validate_ticket(r)
    print(ret)


def scan_parse_loop():
    """Create an input loop for interpreting Sentry barcodes"""

    print("Q to quit")

    while True:
        raw = input("Scan barcode\n")

        raw = raw.strip()

        if raw.lower() in ["quit", "q", ]:
            break

        if len(raw) in [PhoenixU23.LEN_PAIRING, PhoenixU23.LEN_REDEEM]:
            print(Sentry.parse(raw))
        else:
            print("Unknown string format (incorrect length)")


if __name__ == "__main__":
    # run(10_000, 1_000, None, None, False, False)
    # decode_pairing()
    quick_test()