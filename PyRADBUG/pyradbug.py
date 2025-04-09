
from serial import Serial
import time
import argparse
import sys

# default configuration
sideMap = { 'L' : 'A',
            'R' : 'B' }
slotBitmapL = { '1' : 0x81,
                   '2' : 0x82,
                   '3' : 0x84,
                   '4' : 0x88, 
                   '5' : 0x90,
                   '6' : 0xA0,
                   '7' : 0xC0, 
                 }
slotBitmapR = {'1' : 0xC0, 
                    '2' : 0xA0, 
                    '3' : 0x90, 
                    '4' : 0x88,
                    '5' : 0x84,
                    '6' : 0x82,
                    '7' : 0x81}
parser = argparse.ArgumentParser( prog = 'pyradbug',
                                  description = 'configure RADBUG')
parser.add_argument('slot', help='slot of crate to configure to (L|R)(1-7)')
parser.add_argument('--port', help='RADBUG port (search if not specified)')
parser.add_argument('--pueo', help='path to pueo-python directory')

args = parser.parse_args()
slot = args.slot
if not slot[0] in sideMap.keys():
    print("slot must begin with one of", sideMap.keys())
    sys.exit(1)
side = sideMap[slot[0]]
if not slot[1] in slotBitmapL.keys():
    print("slot must end with one of", slotBitmapL.keys())
    sys.exit(1)
if slot[0] == 'L': 
    bitmap = slotBitmapL[slot[1]]
else: 
    bitmap = slotBitmapR[slot[1]]

if not args.port:
    if args.pueo:
        sys.path.append(args.pueo)
    from pueo.common.serialcobsdevice import SerialCOBSDevice    
    print("Available ports:", SerialCOBSDevice.find_serial_devices(name='RB'))
    sys.exit(0)

print("Using", port)
dev = Serial(port, baudrate=9600)
time.sleep(2)
dev.write(b'\n\r')
ln = dev.read_until(b'CMD >> ')
print(ln.decode())
if side == 'A':
    offCmd = b'b '
    onCmd = b'a '
    ctrlCmd = b'ctrla 0x'
else:
    offCmd = b'a '
    onCmd = b'b '
    ctrlCmd = b'ctrlb 0x'

dev.write(offCmd + b'0\r')
ln = dev.read_until(b'CMD >> ')
print(ln.decode())
dev.write(onCmd + b'1\r')
ln = dev.read_until(b'CMD >> ')
print(ln.decode())
dev.write(ctrlCmd+bitmap.to_bytes(1,'big').hex().encode()+b'\r')
ln = dev.read_until(b'CMD >> ')
print(ln.decode())
dev.write(b'status\r')
ln = dev.read_until(b'CMD >> ')
print(ln.decode())

