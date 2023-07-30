#!/usr/bin/env python3
"""Iridium Modem Interface"""

##########################################################################
#
#   Iridium modem interface
#
#   2023-07-10  Todd Valenitc
#               Updated for transport3 / python3
#
##########################################################################

# See these sites for ideas/details:
#
# https://github.com/johngrantuk/iridiumPy/blob/master/Iridium.py
# http://transport.sri.com/projects/vbc-1/browser/software/trunk/libraries/IridiumSBD_TAV/IridiumSBD_TAV.cpp
# http://tabs2.gerg.tamu.edu/~norman/659/Iridium/9306/Iridium%20Short%20Burst%20Data%20Service%20Developers%20Guide%20v3_0.pdf
# http://tabs2.gerg.tamu.edu/~norman/659/9602DevelopersGuide_RevisionBEAM.pdf
# http://rock7.com/downloads/RockBLOCK-Developer-Guide.pdf
# https://github.com/MakerSnake/pyRockBlock/blob/master/rockBlock.py#L80

import datetime
import logging
import signal
import time

import serial
from lockfile import LockFile


class FatalError(Exception):
    """Fatal error exception"""


class Timeout(Exception):
    """Timeout exception"""


class LockBusy(Exception):
    """Lock file busy"""


class Abort(Exception):
    """Abort"""


def locked(fn):
    """Decorator to require lockfile"""

    def get_lock(lock, retries=30):
        while retries:
            if lock.acquire():
                return True
            time.sleep(1)
            retries -= 1

        raise LockBusy

    def wrapper(self, *args, **kw):
        get_lock(self.lockfile)
        try:
            result = fn(self, *args, **kw)
        finally:
            self.lockfile.release()
        return result

    return wrapper


class Modem:
    """Iridium Modem"""

    def __init__(self, name, log=logging, is_alive=None):
        self.log = log

        self.is_alive = is_alive or self.default_is_alive

        serial_device = f"/dev/{name}"
        lock_filename = f"/tmp/LCK..{name}"

        self.lockfile = LockFile(lock_filename, log)
        self.serialport = serial.Serial(
            serial_device,
            baudrate=19200,
            stopbits=1,
            rtscts=False,
            timeout=10,
            writeTimeout=10,
        )

        self.serialport.flushInput()
        self.serialport.flushOutput()

        self.remaining_messages = 0

    def default_is_alive(self):
        """Placeholder is_alive() function"""
        return True

    def compute_end_time(self, timeout):
        """Compute the end time for timeout where timeout is either an
        integer number of seconds or a timedelta object"""

        if isinstance(timeout, int):
            timeout = datetime.timedelta(seconds=timeout)

        return datetime.datetime.now() + timeout

    def wait(self, delay):
        """Wait but exit early is stop running"""

        end_time = self.compute_end_time(delay)
        while datetime.datetime.now() < end_time and self.is_alive():
            time.sleep(1)

    def read_until(self, expect="OK", error="ERROR", reject="NO CARRIER", timeout=30, **kw):
        """Read until expected string is received"""

        # Ensure responses are bytes

        if isinstance(expect, str):
            expect = expect.encode('ascii')

        if isinstance(error, str):
            error = error.encode('ascii')

        if isinstance(reject, str):
            reject = reject.encode('ascii')

        self.log.debug(f"Waiting for '{expect}'")

        response = b""

        end_time = self.compute_end_time(timeout)

        while self.is_alive():
            if datetime.datetime.now() > end_time:
                raise Timeout

            if not self.serialport.inWaiting():
                self.wait(1)
                continue

            response += self.serialport.read(1)

            self.log.debug("Response: %s", response)

            if response.endswith(expect):
                self.log.debug("  - found expect")
                return response

            if reject and response.endswith(reject):
                self.log.debug("  - found reject")
                raise ValueError("Reject found")

            if error and response.endswith(error):
                self.log.debug("  - found error")
                raise ValueError("Error found")

        self.log.debug("  - abort")
        raise Abort

    @locked
    def toggle_dtr(self, delay=10):
        """Toggle DTR line"""

        self.serialport.setDTR(0)
        self.wait(delay)
        self.serialport.setDTR(1)
        return True

    @locked
    def send(self, msg, *args, **kw):
        """Write msg to modem"""

        if isinstance(msg, str):
            msg = msg.encode('ascii')

        self.serialport.write(msg + b"\r")
        return self.read_until(*args, **kw)

    def split_result(self, prefix, result):
        """Return line starting with prefix"""

        if isinstance(prefix, str):
            prefix = prefix.encode('ascii')

        for line in result.split(b"\r\n"):
            line = line.strip()
            if line.startswith(prefix):
                return line.split(b":")[1]

        raise ValueError("Prefix not found")

    @locked
    def get_result(self, msg, *args, **kw):
        """Send msg, check for expected result"""
        if isinstance(msg, str):
            msg = msg.encode('ascii')
        result = self.send(msg, *args, **kw)
        prefix = kw.get("prefix", msg.replace(b"AT", b""))
        return self.split_result(prefix, result)

    @locked
    def ready(self):
        """Ping modem"""
        self.send(b"AT")
        return True

    @locked
    def get_signal_level(self):
        """Get signal level (0-5 bars)"""

        return int(self.get_result(b"AT+CSQ"))

    @locked
    def get_signal_level_fast(self):
        """Get cached signal level"""

        return int(self.get_result("AT+CSQF"))

    def wait_for_signal(self, min_signal=2, timeout=30):
        """Wait until signal level is high enough to transmit"""

        end_time = self.compute_end_time(timeout)

        while datetime.datetime.now() < end_time and self.is_alive():
            signal_level = self.get_signal_level()

            if signal_level >= min_signal:
                return signal_level

            self.log.info("    level=%s", signal_level)
            self.wait(1)

        raise Timeout

    def compute_checksum(self, msg):
        """Compute checksum"""

        checksum = sum(c for c in msg)
        result = chr((checksum & 0xFF00) >> 8) + chr((checksum & 0x00FF))

        return result.encode('ascii')

    @locked
    def send_sbdixa(self, *args, **kw):
        """Initiate SBD session"""

        result = self.get_result("AT+SBDIXA", prefix="+SBDIX", *args, **kw)
        return [int(x) for x in result.split(b",")]

    @locked
    def status_sbd(self, *args, **kw):
        """Query SBD status"""

        result = self.get_result("AT+SBDSX", *args, **kw)
        result = [int(x) for x in result.split(",")]
        return {
            "moFlag": result[0],
            "mo_msn": result[1],
            "mtFlag": result[2],
            "mt_msn": result[3],
            "raFlag": result[4],
            "msgWaiting": result[5],
        }

    @locked
    def status_ring(self):
        """Ring indication status"""

        result = self.get_result("AT+CRIS")
        return [int(x) for x in result.split(",")]

    @locked
    def write_message(self, msg):
        """Write msg to modem buffer"""

        checksum = self.compute_checksum(msg)

        self.log.debug(f"write_message: '{msg}', checksum={checksum}")

        # NOTE: The 9503 SBD modems appear to work different.
        # We expect a READY response before sending the message
        # body to the modem, but for 9603's, the READY doesn't
        # appear to be sent until after the message is sent.
        # The original code is below. Instead, we just wait a
        # second and then write the message, ignoring the READY
        #
        # self.send('AT+SBDWB=%d' % len(msg),expect='READY')

        #self.serialport.write(f"AT+SBDWB={len(msg)}\r".encode('utf=8'))
        #time.sleep(1)
        self.send(f"AT+SBDWB={len(msg)}", expect="READY")
        self.log.debug("Sending message and checksum")
        self.serialport.write(msg + checksum)
        self.read_until("OK")

        return True

    @locked
    def read_message(self):
        """Read text message from modem"""

        msg = self.send("AT+SBDRT")

        msg = msg.strip().strip("OK")
        msg = msg.split("+SBDRT:\r")[1]

        return msg

    @locked
    def exchange_sbd(self, timeout=300):
        """Send message"""

        end_time = self.compute_end_time(timeout)

        mt_msglist = []
        mo_ok = False
        mt_ok = False
        mt_queued = 0
        attempt = 0

        while not (mo_ok and mt_ok and mt_queued <= 0) and self.is_alive():
            attempt += 1

            self.log.info("SBD exchange: attempt %d", attempt)

            if datetime.datetime.now() > end_time:
                if mo_ok:
                    return mt_msglist
                raise Timeout

            try:
                sqf = self.wait_for_signal()
                self.log.info(f"  - good signal: {sqf}")
            except: # pylint: disable=bare-except
                self.log.info("  - no signal")
                continue

            self.log.info("  - sending")

            try:
                mo_status, mo_msn, mt_status, mt_msn, mt_len, mt_queued = self.send_sbdixa()
            except Abort:
                continue
            except: # pylint: disable=bare-except
                self.log.exception("   - failed to run sbdix")
                raise
                self.log.info("   - failed to run sbdix")
                self.wait(5)
                continue

            self.log.info("  - mo_status=%s", mo_status)
            self.log.info("  - mt_status=%s", mt_status)
            self.log.info("  - mt_queued=%s", mt_queued)

            if mo_status in [0, 1, 2, 3, 4]:
                self.log.info("  - MO send OK")
                self.send("AT+SBDD0")
                self.log.info("  - send buffer cleared")
                mo_ok = True
            elif mo_status in [12, 14, 16]:
                # Mark at true so we don't get stuck trying to resend
                self.log.error("  - invalid message")
                self.send("AT+SBDD0")
                mo_ok = True
            else:
                self.log.info("    - failed to connect to gateway")
                self.wait(15)

            if mt_status == 0:
                # No messages pending
                mt_ok = True
            elif mt_status == 1:
                self.log.info("  - pending message")
                mt_msg = self.read_message()
                if mt_msg:
                    mt_msglist.append(mt_msg)
                mt_ok = True
            else:
                mt_ok = False

            self.log.info("  - done")

        return mt_msglist


def test():
    """Test routine"""

    is_running = True

    class ServiceExit(Exception):
        """Stop service"""

    def shutdown(_signum, _frame):
        is_running = False
        raise ServiceExit

    def running():
        return is_running

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)

    try:
        modem = Modem('iridium',log=logging,is_alive=running)
        print(f"Modem ready: {modem.ready()}")
        print(f"Signal: {modem.get_signal_level()}")
        print("Waiting for good signal...")
        print(f"Signal: {modem.wait_for_signal()}")
        print("Queue message")
        modem.write_message(b"hello")
        print("SBD exchange")
        msgs = modem.exchange_sbd()
        print("Queued messages:", msgs)

        while False:
            print("Waiting for RING")
            while True:
                status = modem.status_sbd()
                print(status)
                if status["raFlag"]:
                    print("RA detected!")
                    break

            print("SBD exchange")
            msgs = modem.exchange_sbd()
            print("Queued messages:", msgs)

    except ServiceExit:
        print("Exiting ...")


if __name__ == "__main__":
    test()
