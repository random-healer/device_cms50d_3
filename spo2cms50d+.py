#!/usr/bin/env python2

# Copyright (c) 2016 Tommi Airikka <tommi@airikka.net>
# License: GPLv2

import sys, struct, serial, argparse
from dateutil.parser import parse

#####################
##### Variables #####
#####################
parser = argparse.ArgumentParser(description='Download stored data from a CMS50D+ oximeter.')
parser.add_argument('device', type=str, help='path to device file')
parser.add_argument('outfile', type=str, help='output file path')
parser.add_argument('-s', '--start-time', dest='starttime', type=str, help='start time (\"YYYY-MM-DD HH:MM:SS\")')

args = parser.parse_args(['/dev/ttyUSB0', 'output.txt', '-s', '2014-01-02'])

device = args.device
outfile = args.outfile
starttime = args.starttime
ser = serial.Serial()

###################
##### Helpers #####
###################


# Pack little endian
def _ple(value):
    return struct.pack("<I", value)


def _get_real_values(val1, val2):

    oval1 = ord(val1)
    oval2 = ord(val2)
    v1 = oval1 - 0x80
    v2 = oval2 - 0x80
    if v1 == 0 or oval1 == 0xFF:
        v1 = 127
    if v2 == 0 or oval2 == 0xFF:
        v2 = 255
    return (v1, v2)


def _parse_list(toparse, parsed):
    while toparse:
        if len(toparse) > 1:
            fs = (toparse.pop(0), toparse.pop(0))
            if not fs == ('\x0f', '\x80'):
                (file, s) = _get_real_values(fs)
                if file >= 0 and s >= 0:
                    parsed.append(file)
                    parsed.append(s)
        else:
            toparse.pop(0)

#####################
##### Functions #####
#####################


def configure_serial(ser):
    ser.baudrate = 115200  # 115200
    ser.bytesize = serial.EIGHTBITS  # 8
    ser.parity = serial.PARITY_NONE  # N
    ser.stopbits = serial.STOPBITS_ONE  # 1
    ser.xonxoff = 1  # XON/XOFF flow control
    ser.timeout = 1
    ser.port = device


def get_raw_data(ser):
    sys.stdout.write("Connecting to device...")
    sys.stdout.flush()
    ser.open()
    sys.stdout.write("reading...")
    sys.stdout.flush()
    ser.write(b'\x7d\x81\xa6')
    raw = list(ser.readall())
    ser.close()
    if len(raw) <= 1:
        print("no data received. Is the device on?")
        exit(43)
    print("done!")
    return raw


def parse_raw_data(data):
    sys.stdout.write("Parsing data...",)
    sys.stdout.flush()
    parsed = []
    _parse_list(data, parsed)
    print("done!")
    return parsed


def get_len_of_parsed_data(parsed):
    return len(parsed) / 2  # 1Hz, two values (pulse and sats)


def write_to_file(parsed, total_len, file):
    sys.stdout.write("Writing to file...",)
    sys.stdout.flush()

    zeroval = _ple(0)
    file.write(_ple(856))
    file.write(_ple(1))
    for _ in range(212):
        file.write(zeroval)
    file.write(_ple(1))
    for _ in range(55):
        file.write(zeroval)
    file.write(_ple(total_len))
    for e in parsed:
        file.write(chr(e))


def change_starttime(file):
    if starttime != None:
        sys.stdout.write("changing start time...",)
        sys.stdout.flush()
        dt = parse(starttime, dayfirst=False, yearfirst=True)
        year = _ple(dt.year)
        month = _ple(dt.month)
        day = _ple(dt.day)
        hour = _ple(dt.hour)
        minute = _ple(dt.minute)
        second = _ple(dt.second)
        file.seek(0x420)
        s = year + month + day + hour + minute + second
        file.write(s)

################
##### Main #####
################


configure_serial(ser)

data = get_raw_data(ser)

parsed = parse_raw_data(data)

total_len = get_len_of_parsed_data(parsed)

file = open(outfile, 'wb')

write_to_file(parsed, total_len, file)

change_starttime(file)

file.close()

print("done!")
