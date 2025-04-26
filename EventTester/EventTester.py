import socket
import time
import struct
import sys
import ipaddress

# these are constants
EVENT_CTRL_PORT = 21603
EVENT_ACK_PORT = 21601
EVENT_NACK_PORT = 21614

#polyfill for python < 3.8
def tohex(b, s=' '):
    if  sys.version_info < (3,8,0):
        h = b.hex()
        return s.join(h[i:i+2] for i in range(0,len(h),2))
    else: 
        return b.hex(sep=s)
    
class EventServer:
    def __init__(self,
                 local_ip="10.68.65.1",
                 local_port=21347,
                 local_event_port=21349,
                 remote_ip="10.68.65.81"
                 ):
        self.local_ip = ipaddress.ip_address(local_ip)
        self.local_port = local_port
        self.local_event_port = local_event_port
        
        self.remote_ip = ipaddress.ip_address(remote_ip)
        
        self.cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cs.bind( (str(self.local_ip), self.local_port ) )        
        self.es = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.es.bind( (str(self.local_ip), self.local_event_port ) )        

        self.turfcs = ( str(self.remote_ip), EVENT_CTRL_PORT )
        self.turfack = ( str(self.remote_ip), EVENT_ACK_PORT )
        self.turfnack = ( str(self.remote_ip), EVENT_NACK_PORT )

        # check if we're working
        self.mac = tohex(self.ctrlmsg(b'ID')[::-1][2:],s=':')
        print(f'Connected to: {self.mac}')
        cap = self.ctrlmsg(b'PR')

        self.max_mask = int.from_bytes(cap[0:2], 'little')
        self.max_addr = int.from_bytes(cap[2:4], 'little')
        self.max_fragment = int.from_bytes(cap[4:6], 'little')
        print(f'Fragment source mask bits allowable: {hex(self.max_mask)}')
        print(f'Maximum address: {self.max_addr}')
        print(f'Maximum fragment size: {self.max_fragment}')
        # reset the ack/nack tags to zero
        self.acktag = 0
        self.nacktag = 0

    def open(self, max_allow=1):
        # the 8 bytes here correspond to (in this order)
        # 7:0, 15:8, 23:16, 31:24, 39:32, 47:40, 55:48, 63:56
        # port is stored little-endian in TURF in 15:0
        # top 2 bytes are the command, dumbass
        data = self.local_event_port.to_bytes(2, 'little') + int(self.local_ip).to_bytes(4, 'little')
        self.ctrlmsg(b'OP', data=data)
        # now we have to build the acks
        # acks are (addr << 20) from 0 to max_addr (32 bits)
        # + 8 bit tag (incrementing)
        # + 2 8-bit zeros
        # + 0x80 (for allow increment) or 0x00
        for i in range(self.max_addr+1):
            self.ackmsg(i, i < max_allow, verbose=True)

    def close(self):
        self.ctrlmsg(b'CL')
            
    def ackmsg(self, addr, allow, verbose=True):
        addr = addr & 0xFFF
        msg = (addr<<20).to_bytes(4, 'little')
        msg += self.acktag.to_bytes(1, 'little')
        msg += b'\x00\x00'
        msg += b'\x80' if allow else b'\x00'
        self.cs.sendto( msg, self.turfack )
        # should have a timeout check here!!!!!
        rmsg = self.cs.recv(1024)
        ctlbyte = rmsg[7]
        respaddr = (int.from_bytes(rmsg[0:4], 'little'))>>20
        resptag = rmsg[4]
        if verbose:
            print(f'ack response: tag {resptag} addr {respaddr} ctl {hex(ctlbyte)}')
            print(f'ack response: {rmsg.hex(sep=" ")}')
            
        # shoud do an ack check here but whatevs
        self.acktag = (self.acktag + 1) & 0xFF
        return (respaddr, resptag, ctlbyte)
            
    def ctrlmsg(self, cmd, data=b''):
        # ok ok ok: the way this works is that our command has to come
        # first, no matter what.
        msg = cmd[::-1] + data[::-1]
        # and pad up to 8
        msg = msg.ljust(8, b'\x00')
        self.cs.sendto( msg, self.turfcs )
        rmsg = self.cs.recv(1024)
        return rmsg
        
