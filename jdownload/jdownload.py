#!/usr/bin/env python3

# you need pysct for this
# https://github.com/raczben/pysct
# you also need progressbar2 because I said so

from pysct.core import Xsct
import progressbar2
import socket
import sys
import argparse
import os
from tempfile import NamedTemporaryFile
from math import ceil

JDLD_VERSION = b'V 1.0'
JDLD_OK = b'K'
JDLD_CHUNK_SIZE = 1024*1024
JDLD_MAILBOX = "0x70000000"
endfile = b'\x04'

# stupid utility crap
def startStopUart( xsct, en ):
    if en:
        cmd = 'jtagterminal -socket'
    else:
        cmd = 'jtagterminal -stop'
    resp = xsct.do('target -set -filter { name =~ "Cortex-A53 #0" }')
    resp = xsct.do(cmd)
    if en:
        termPort = int(resp)
    else:
        termPort = None
    resp = xsct.do('target -set -filter { name =~ "PSU" }')
    return termPort

def getLine( sock ):
    msg = b''
    while True:
        try:
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' %
                      (prog, len(data), len(msg)))
            if msg[-1:] == b'\n':
                break
        except socket.timeout:
            print("%s: never received a line before timeout??" % prog)
            print("{!r}".format(msg))
            # send EOT to be safe
            sock.sendall(endfile)
            return None
    return msg

def getExpected( sock, expect):
    msg = b''
    while True:
        try:
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' %
                      (prog, len(data), len(msg)))
            if msg == expect:
                break
        except socket.timeout:
            print("%s: never received echo before timeout??" % prog)
            print("{!r}".format(expect))
            print("{!r}".format(msg))
            # send EOT to be safe
            sock.sendall(endfile)
            return False
    return True
    

prog = "jdownload"
bridge = b'jb'
finish = b'\x04'

# what-freaking-ever
modes = [ 'pynq', 'surf' ]
promptDict = { 'pynq' : b'xilinx@pynq:~$ ',
           'surf' : b'root@SURFv6:~# ' }
beginPromptDict = { 'pynq' : b'\x1b[?2004h',
                'surf' : b'' }
endcmdDict = { 'pynq' : b'\x1b[?2004l\r',
               'surf' : b'' }
newlineDict = { 'pynq' : b'\r\n',
            'surf' : b'\r\n' }

parser = argparse.ArgumentParser(prog=prog)
parser.add_argument("localFile", help="local filename to transfer")
parser.add_argument("remoteFile", help="remote filename")
parser.add_argument("--xsdb", help="xsdb binary",
                    default="xsdb")
parser.add_argument("--port", help="if specified, use running xsdb at this port",
                    default="")
parser.add_argument("--connect", help="string to pass after connect if spawning xsct",
                    default="")
parser.add_argument("--verbose", "-v", action="count", default=0,
                    help="Increase verbosity")
parser.add_argument("--mode", help="either pynq or surf (default)",
                    default="surf")
parser.add_argument("--safeStart",action='store_true',
                    help="Try to read out all characters possible before starting (takes 5+ seconds)")

args = parser.parse_args()
v = args.verbose
mode = args.mode

# do a bunch of stuff that'll except out if user is a jerk
prompt = promptDict[mode]
beginPrompt = promptDict[mode]
newline = newlineDict[mode]
endcmd = endcmdDict[mode]

if v > 1:
    print("%s: running in %s mode - expect prompt %s" % (prog, mode, prompt))

remoteFileBytes = bytes(args.remoteFile, encoding='utf-8')

print(args.xsdb)
host = 'localhost'

# check if this $#!+ exists
if not os.path.exists(args.localFile):
    print("%s: can't find %s to send" % (prog, args.localFile))

# get its file size
lfilesz = os.path.getsize(args.localFile)    
lfile = os.open(args.localFile, os.O_RDONLY)

# connect to the xsct/xsdb server
if args.port:
    xsct = Xsct(host, int(args.port))
else:
    print("%s: launching xsdb/xsct is still a work in progress" % prog)
    exit(1)

# get a tempfile
tf = NamedTemporaryFile()

# spawn the terminal (this also bounces us back to PSU as a target)
termPort = startStopUart(xsct, True)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (host, termPort)
if v > 0:
    print('%s: connecting to %s port %d' % (prog, host, termPort))
sock.connect(server_address)

try:
    if v > 0:
        print('%s: fetching prompt' % prog)
    sock.sendall(b'\n')
    sock.settimeout(5)
    msg = b''
    while True:
        try:
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' % (prog, len(data), len(msg)))
            if (msg[-len(prompt):None] == prompt):
                if args.safeStart:
                    if v > 0:
                        print('%s: found prompt after %d bytes, continuing due to safeStart'
                              % (prog, len(msg)))
                else:
                    if v > 0:
                        print('%s: found prompt after %d bytes'
                              % (prog, len(msg)))
                        break            
        except socket.timeout:
            if v > 0:
                print('%s: timed out waiting for more data' % prog)
            break
    # did we get our prompt
    if v > 1:
        print("%s: got %d bytes - " % (prog, len(msg)))
        print("{!r}".format(msg))
    if msg[-len(prompt):None] == prompt:
        if v > 0:
            print("%s: found prompt, continuing" % prog)
    else:
        print("%s: did not find prompt, maybe try --safeStart?" % prog)
        print("%s: got %d bytes - " % (prog, len(msg)))
        print("{!r}".format(msg))
        print("expected {!r}".format(prompt))
        startStopUart(xsct, False)
        exit(1)

    # execute the bridge
    sock.sendall(b'jb\n')
    getExpected(sock, b'jb\r\n')
    sock.sendall(b'V\n')
    ln = getLine(sock)
    if ln[:-2] != JDLD_VERSION:
        print("%s: jdld says it is version %s??" % (prog, ln[:-2]))
        print("%s: I was expecting %s" % (prog, JDLD_VERSION))
        sock.sendall(endfile)
        startStopUart(xsct, False)
        exit(1)
    # create the remote file
    crCommand = b'C' + remoteFileBytes + b'\n'
    sock.sendall(crCommand)
    ln = getLine(sock)
    if ln[:-2] != JDLD_OK:
        print("%s: jdld did not respond OK to file create (%s)" % (prog, ln[:-2]))
        print("%s: maybe a previous transfer is borked - open terminal, run jc, then send D0" % prog)
        sock.sendall(endfile)
        sock.close()
        startStopUart(xsct, False)
        exit(1)
    # NOW IT'S FUN TIME
    chunkCount = 0
    # Up the timeout, since it takes ~13 seconds per chunk
    xsct._socket.settimeout(30)
    # PRETTY PRETTY
    widgets = widgets = [ args.remoteFile  + ":",
                          ' ', progressbar2.Percentage(),
                          ' ', progressbar2.GranularBar(),
                          ' ', progressbar2.AdaptiveETA(),
                          ' ', progressbar2.AdaptiveTransferSpeed() ]
    bar = progressbar2.ProgressBar( widgets=widgets,
                                    max_value=lfilesz,
                                    redirect_stdout=True).start()                          
    while True:
        if v > 0:
            print("starting chunk %d..." % chunkCount, end='')
        bar.update(chunkCount*JDLD_CHUNK_SIZE)
        chunk = os.read(lfile, JDLD_CHUNK_SIZE)
        chunkLen = len(chunk)
        if chunkLen > 0:
            tf.write(chunk)
            tf.flush()
            xsctCmd = 'dow -data %s %s; set done "done"' % (tf.name, JDLD_MAILBOX)
            resp = xsct.do(xsctCmd)
            if resp != 'done':
                print("%s: got response %s ????" % (prog, resp))
                sock.sendall(b'D0\n'+endfile)
                sock.close()
                startStopUart(xsct, False)
                exit(1)
        if v > 0:
            print("downloaded...", end='')
        if chunkLen != JDLD_CHUNK_SIZE:
            dCommand = b'D '+bytes(str(chunkLen), encoding='utf-8')+b'\n'
        else:
            dCommand = b'D\n'
        sock.sendall(dCommand)
        ln = getLine(sock)
        if ln[:-2] != JDLD_OK:
            print("%s: jdld did not respond OK to chunk download (%s)!" % (prog, ln[:-2]))
            sock.sendall(endfile)
            sock.close()
            startStopUart(xsct, False)
            exit(1)
        if v > 0:
            print("complete.")
        chunkCount = chunkCount + 1
        if chunkLen != JDLD_CHUNK_SIZE:
            break
        else:
            tf.seek(0)
    bar.finish()
    print("%s: Download successful after %d chunks" % (prog, chunkCount))
    sock.sendall(endfile)
    # clear out the prompt
    ln = getExpected(sock, b'jc: exiting\r\n'+prompt)
    sock.close()
    startStopUart(xsct, False)
finally:
    print("%s : exiting." % prog)
    
