# this contains both HskSerial and HskEthernet
# YES I KNOW THE NAME OF THE MODULE IS STUPID
from serial import Serial
from cobs import cobs
import sys
import socket
import os
import struct


# dev.send(HskPacket(0x80, 0x00)) as well as fully-filling it
# from a response.
# data can be
# - bytearray
# - bytes
# - string
# - list of integers under 256
# - anything else castable to bytes via bytes()
class HskPacket:
    cmds = {
        "ePingPong" : 0x00,
        "eStatistics" : 0x0F,
        "eTemps" : 0x10,
        "eVolts" : 0x11,
        "eIdentify" : 0x12,
        "eCurrents" : 0x13,
        "eStartState" : 0x20,
        "eSleep" : 0x21,
        "eFwParams" : 0x80,
        "eFwNext" : 0x81,
        "ePROMStartup" : 0x82,
        "ePROMBitLoadOrder" : 0x83,
        "ePROMSoftLoadOrder" : 0x84,
        "ePROMOrientation" : 0x85,
        "eLoadSoft" : 0x86,
        "eSoftNext" : 0x87,
        "eSoftNextReboot" : 0x88,
        "eJournal" : 0xBD,
        "eDownloadMode" : 0xBE,
        "eRestart" : 0xBF,
        "eEnable" : 0xC8,
        "ePMBus" : 0xC9,
        "eReloadFirmware" : 0xCA,
        "eError" : 0xFF
        }

    #  cmd, src range
    prettifiers = {
            ('eTemps', 'TURF') : lambda d, a : {
                'T_APU_TURF' : getT(d[0],d[1],'TURF'),
                'T_RPU_TURF' : getT(d[2],d[3],'TURF')
                },
            ('eTemps', 'SURF') : lambda d, a : {
                'T_APU_SURF_' + str(surfNum(a)) : getT(d[0], d[1],'SURF'),
                'T_RPU_SURF_' + str(surfNum(a)) : getT(d[2], d[3],'SURF')
                },
            ('eTemps', 'TURFIO') : lambda d, a : {
                'T_TURFIO_'  + str(turfioNum(a)) : getT(d[0], d[1], 'TURFIO'),
                'T_SURF1HS_' + str(turfioNum(a)) : getT(d[2], d[3], 'SURFSWAP'),
                'T_SURF2HS_' + str(turfioNum(a)) : getT(d[4], d[5], 'SURFSWAP'),
                'T_SURF3HS_' + str(turfioNum(a)) : getT(d[6], d[7], 'SURFSWAP'),
                'T_SURF4HS_' + str(turfioNum(a)) : getT(d[8], d[9], 'SURFSWAP'),
                'T_SURF5HS_' + str(turfioNum(a)) : getT(d[10],d[11],'SURFSWAP'),
                'T_SURF6HS_' + str(turfioNum(a)) : getT(d[12],d[13],'SURFSWAP'),
                'T_SURF7HS_' + str(turfioNum(a)) : getT(d[14],d[15],'SURFSWAP')
                }
    }




    strings = dict(zip(cmds.values(),cmds.keys()))

    def __init__(self,
                 dest,
                 cmd,
                 data=None,
                 src=0xFE):
        if data is None:
            self.data = b''
        elif isinstance(data, str):
            self.data = data.encode()
        else:
            self.data = bytes(data)
        self.dest = dest
        self.src = src
        if isinstance(cmd, str):
            if cmd in self.cmds:
                self.cmd = self.cmds[cmd]
            else:
                raise ValueError("%s not in cmds table" % cmd)
        else:
            self.cmd = cmd

    def __str__(self):
        return "HskPacket."+self.pretty()
        
    def pretty(self, asString=False):
        if self.cmd in self.strings:
            cstr = self.strings[self.cmd]
        else:
            cstr = "UNKNOWN(%2.2x)" % self.cmd
        myStr = cstr + " from " + "%2.2x" % self.src + " to " + "%2.2x" % self.dest
        if len(self.data):

            pretty_dict = self.prettyDict()
            if pretty_dict is not None:
                myStr += ": " + str(pretty_dict)
            elif asString:
                myStr += ": " + self.data.decode()
            else:
                myStr += ": " + tohex(self.data)
        return myStr


    def prettyDict(self):
            pretty_tuple =(self.strings[self.cmd], deviceType(self.src))
            if pretty_tuple in self.prettifiers:
                return self.prettifiers[pretty_tuple](self.data, self.src)
        
    def encode(self):
        pkt = bytearray(4)
        pkt[0] = self.src
        pkt[1] = self.dest
        pkt[2] = self.cmd
        pkt[3] = len(self.data)
        pkt += self.data
        pkt.append((256-(sum(pkt[4:]))) & 0xFF)
        return cobs.encode(pkt)

class HskBase:
    def __init__(self, srcId):
        self.src = srcId
        self._writeImpl = lambda x : None
        self._readImpl = lambda : none

    def repeat_receive(self, daddr, cmd):
        """ Retrieves output (called inside HskBase.journal) """
        res = ''
        pkt = self.receive()
        res += pkt.data.decode()
        while len(pkt.data) == 255:
            self.send(HskPacket(daddr, cmd))
            pkt = self.receive()
            res += pkt.data.decode()
        return res
    
    def journal(self, daddr, line='-u pueo-squashfs -o cat -n 10'):
        """ Fetches the output of a journalctl command. Options passed in line. """
        self.send(HskPacket(daddr, 'eJournal', data=line.encode()))
        return self.repeat_receive(daddr, 'eJournal')
        
    def send(self, pkt, override=False):
        """ Send a housekeeping packet. Uses HskSerial.src as source unless override is true or no source was provided """
        if not isinstance(pkt, HskPacket):
            raise TypeError("pkt must be of type HskPacket")
        if not override:
            pkt.src = self.src
        self._writeImpl(pkt.encode()+b'\x00')

    def receive(self):
        """ Receive a housekeeping packet. No timeout right now. """
        crx = self._readImpl().strip(b'\x00')
        rx = cobs.decode(crx)
        # checky checky
        if len(rx) < 5:
            raise IOError("received data only %d bytes" % len(rx))
        if sum(rx[4:]) & 0xFF:
            raise IOError("checksum failure: " + tohex(rx))
        return HskPacket(rx[1],
                         rx[2],
                         data=rx[4:-1],
                         src=rx[0])

        
class HskEthernet(HskBase):
    TH_PORT = 21608
    def __init__(self,
                 srcId=0xFE,
                 localIp="10.68.65.1",
                 remoteIp="10.68.65.81",
                 localPort=21352):
        HskBase.__init__(self, srcId)
        self.localIpPort = ( localIp, localPort)
        self.remoteIpPort = ( remoteIp, self.TH_PORT )

        self.hs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hs.bind(self.localIpPort)
        self._writeImpl = lambda x : self.hs.sendto(x, self.remoteIpPort)
        self._readImpl = lambda : self.hs.recv(1024)


    def upload(self, fn, destfn=None):
        """ 
        WIP DO NOT USE
        Uploads a file via the secret hskSpiBridge uploader methods.
        """
        # This is magic: we need to make sure that our payload size + 1 byte
        # is a multiple of 32, because we read out in chunks of 32 and can't
        # determine anything other than that.
        PAYLOAD_SIZE = 1023
        def fwupdHeader(fn, size):
            hdr = bytearray(b'PYFW')
            flen = size
            hdr += struct.pack(">I", flen)
            hdr += fn.encode()
            hdr += b'\x00'
            hdr += (256 - sum(hdr) % 256).to_bytes(1, 'big')
            return (hdr, flen)
        if not destfn:
            destfn = '/home/root/' + os.path.basename(fn)
        if not os.path.isfile(fn):
            raise ValueError(f'{fn} is not a regular file')
        hdr, flen = fwupdHeader(destfn, os.path.getsize(fn))
        toRead = PAYLOAD_SIZE - len(hdr)
        toRead = flen if flen < toRead else toRead
        print(f'Uploading {fn} to {destfn}')
        # secret reset
        self._writeImpl(b'\x00'*32)
        # ack        
        r = self._readImpl()
        if r[0] == 0:
            print('Reset was acknowledged.')
        d = hdr
        written = 0
#        if pb2:
#            uploadbar = make_bar(flen, uwidgets).start()
#            update = lambda v, n : uploadbar.update()
#            finish = uploadbar.finish
#        else:
#            update = lambda v, n : print(f'{v}/{n}')
#            finish = lambda : None
        with open(fn, "rb") as f:
            while written < flen:
                d += f.read(toRead)
                nb = len(d)
                padBytes = PAYLOAD_SIZE - nb if nb < PAYLOAD_SIZE else 0
                d += padBytes*b'\x00'
                self._writeImpl(b'\x00'+d)
                r = self._readImpl()
                print(f'ack: {r[0]}')
                written += toRead
                remain = flen - written
                toRead = remain if remain < PAYLOAD_SIZE else PAYLOAD_SIZE
                d = b''
    
# build up and send the command given the destination, type,
# and the data to deliver if any.
# Data defaults to none b/c it allows us to do like
# sendHskCmd(dev, 0x80, 0x00) straight out.
# the smart user may create dicts or something to lookup
# IDs and command types with enums that can cast to ints or some'n
# src defaults to zero
# ...
# i am not smart
class HskSerial(Serial, HskBase):
    def __init__(self, path, baudrate=500000, srcId=None):
        """ Create a housekeeping parser from a tty-like object. If srcId is provided, packets always come from that ID. """
        Serial.__init__(self, path, baudrate=baudrate, timeout=5)
        HskBase.__init__(self, srcId)
        self._writeImpl = self.write
        self._readImpl = lambda : self.read_until(b'\x00')
        

#polyfill for python < 3.8
def tohex(b, s=' '):
    if  sys.version_info < (3,8,0):
        h = b.hex()
        return s.join(h[i:i+2] for i in range(0,len(h),2))
    else: 
        return b.hex(sep=s)
    

def getT(msb, lsb, kind = 'SURF'):

    adc = msb * 256 + lsb; 

    if kind == 'SURF' or kind == 'TURF':
        return adc * 509.3140064 / (2**16) - 280.2308787
    elif kind == 'TURFIO':
        return adc * 503.975 / (2**12) - 273.15
    elif kind == 'SURFSWAP':
        return (adc * 10  - 31880) / 42
    else: 
        return None

def deviceType(addr):
    if addr == 0x60:
        return 'TURF'
    elif addr in (0x40,0x48,0x50,0x58):
        return 'TURFIO'
    elif addr >= 0x80:
        return 'SURF'


def surfNum(addr):
    return addr - 128

def turfioNum(addr):
    return (addr-64) >> 3


