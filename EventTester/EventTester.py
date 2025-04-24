import socket
import time
import struct

MY_IP = "10.68.65.1"
REMOTE_IP = "10.68.65.81"
MY_PORT = 21347
MY_EVENT_PORT = 21349

EVENT_CTRL_PORT = 21603
EVENT_ACK_PORT = 21601
EVENT_NACK_PORT = 21614

class EventServer:
    def __init__(self):
        self.cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cs.bind( (MY_IP, MY_PORT ) )
        self.es = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.es.bind( (MY_IP, MY_EVENT_PORT ) )

        self.turfcs = ( REMOTE_IP, EVENT_CTRL_PORT )
        self.turfack = ( REMOTE_IP, EVENT_ACK_PORT )
        self.turfnack = ( REMOTE_IP, EVENT_NACK_PORT )

#        id = self.ctrlmsg(b'ID')
#        print(f'ID response: {id.hex()}')
#        pr = self.ctrlmsg(b'PR')
#        print(f'PR response: {pr.hex()}')

    def ctrlmsg(self, cmd, data=b''):
        msg = cmd + bytes(data)
        msg = msg.rjust(8, b'\x00')[::-1]
        self.cs.sendto( msg, self.turfcs )
        rmsg = self.cs.recv(1024)
        return rmsg
        
