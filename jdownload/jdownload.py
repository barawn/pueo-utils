#!/usr/bin/env python3

# you need pysct for this
# https://github.com/raczben/pysct
# you also need progressbar2 because I said so
# - OK you need SOME form of progressbar
#   I don't know if I'm using any progressbar2
#   -exclusive features. Deal with it.

# I'm deferring pysct's import until after argparse
# to allow for passing the path to it
#from pysct.core import Xsct

pb = None
try:
    import progressbar2 as pb
except ImportError:
    pass
if pb is None:
    try:
        import progressbar as pb
    except ImportError:
        pass

import socket
import sys
import argparse
import textwrap
import os
from pathlib import Path
from sys import platform
from tempfile import NamedTemporaryFile
from math import ceil
from string import Template

translate_path = lambda x : x
# cygwin needs the pycygwin module for cygpath
# to translate tmpfile paths.

# windows systems stupidly use double-backslashes which
# Python/pysct turns into control-characters, so eff that $#!+
# - use forward-slashes
if platform == 'cygwin':
    from cygwin import cygpath
    translate_path = lambda x : cygpath(x, mode='windows').replace("\\","/")
elif platform == 'win32' or platform == 'msys':
    translate_path = lambda x : x.replace("\\","/")
    
JDLD_VERSION = b'V 1.0'
JDLD_OK = b'K'
JDLD_CHUNK_SIZE = 1024*1024
JDLD_MAILBOX = "0x70000000"
endfile = b'\x04'

# stupid utility crap
def startStopUart( xsct, en, jtagsn = None ):
    if jtagsn:
        cortexTargetStr = 'target -set -filter { name =~ "Cortex-A53 #0" && jtag_cable_serial =~ "%s" }' % jtagsn
        psuTargetStr = 'target -set -filter { name =~ "PSU" && jtag_cable_serial =~ "%s" }' % jtagsn
    else:
        cortexTargetStr = 'target -set -filter { name =~ "Cortex-A53 #0" }'
        psuTargetStr = 'target -set -filter { name =~ "PSU" }'   

    if en:
        cmd = 'jtagterminal -socket'
    else:
        cmd = 'jtagterminal -stop'
    resp = xsct.do(cortexTargetStr)    
    resp = xsct.do(cmd)
    if en:
        termPort = int(resp)
    else:
        termPort = None
    resp = xsct.do(psuTargetStr)
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
    
def getPrompt( sock, prompt, prog, v=0, safeStart=False):
    msg = b''
    while True:
        try:
            data = sock.recv(500)
            msg += data
            if v > 1:
                print('%s: got %d bytes, up to %d' % (prog, len(data), len(msg)))
            if (msg[-len(prompt):None] == prompt):
                if safeStart:
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
    return msg

prog = "jdownload"
bridge = b'jb'
finish = b'\x04'

# what-freaking-ever
modes = [ 'pynq', 'surf', 'turf' ]
promptDict = { 'pynq' : b'xilinx@pynq:~$ ',
               'surf' : b'root@SURFv6:~# ',
               'turf' : b'root@TURFv6:~# '}
beginPromptDict = { 'pynq' : b'\x1b[?2004h',
                    'surf' : b'',
                    'turf' : b'' }
endcmdDict = { 'pynq' : b'\x1b[?2004l\r',
               'surf' : b'',
               'turf' : b'' }
newlineDict = { 'pynq' : b'\r\n',
                'surf' : b'\r\n',
                'turf' : b'\r\n' }

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
parser.add_argument("--pysct", help="path to pysct repository")
parser.add_argument("--jtagsn", help="JTAG serial number")
parser.add_argument("--postcmd",
                    help=textwrap.dedent(''' post-download command file. \
                    This file is a templated file containing commands to \
                    run after download is complete. \
                    See string.Template - available template variables \
                    are localFile, localPath, remoteFile, baseFile.'''))
parser.add_argument("--yes", action='store_true', help="don't prompt for postcmd, just do it")                    

args = parser.parse_args()
if args.pysct:
    sys.path.append(args.pysct)

splitFile = args.localFile.split('/')

postCmds = None
if args.postcmd:
    templDict = dict(localFile = args.localFile,
                     localPath = '/'.join(splitFile[:-1]),
                     remoteFile = args.remoteFile,
                     baseFile = splitFile[-1])    
    p = Path(args.postcmd)
    if not p.exists():
        print(f'cannot find {args.postcmd}')
        exit(1)
    txt = p.read_text()
    t = Template(txt)
    postCmds = t.substitute(templDict).splitlines()
    if not args.yes:
        print("After transfer, I will:")
        for l in postCmds:
            print(f'execute: {l}')
        i = input("Confirm with yep:")
        if i != 'yep':
            print("Exiting instead.")
            exit(1)
        
# now import
from pysct.core import Xsct
    
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
# open the damn thing, but DON'T USE os.open it DOESN'T WORK on Windows
lfile = open(args.localFile, "rb")

# connect to the xsct/xsdb server
if args.port:
    xsct = Xsct(host, int(args.port))
else:
    print("%s: launching xsdb/xsct is still a work in progress" % prog)
    exit(1)

# get a tempfile
# let's try deferring the tempfile because windows is an asshole
#tf = NamedTemporaryFile()

# spawn the terminal (this also bounces us back to PSU as a target)
termPort = startStopUart(xsct, True, jtagsn=args.jtagsn)

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
    # did we get our prompt
    msg = getPrompt( sock, prompt, prog, v=v, safeStart=args.safeStart)
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
        startStopUart(xsct, False, jtagsn=args.jtagsn)
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
        startStopUart(xsct, False, jtagsn=args.jtagsn)
        exit(1)
    # create the remote file
    crCommand = b'C' + remoteFileBytes + b'\n'
    sock.sendall(crCommand)
    ln = getLine(sock)
    if ln[:-2] != JDLD_OK:
        print("%s: jdld did not respond OK to file create (%s)" % (prog, ln[:-2]))
        print("%s: maybe a previous transfer is borked - open terminal, run jc, then send \"D 0\"" % prog)
        sock.sendall(endfile)
        sock.close()
        startStopUart(xsct, False, jtagsn=args.jtagsn)
        exit(1)
    # NOW IT'S FUN TIME
    chunkCount = 0
    # Up the timeout, since it takes ~13 seconds per chunk
    xsct._socket.settimeout(30)
    # PRETTY PRETTY
    if pb is not None:
        bar_widget = None
        try:
            bar_widget = pb.GranularBar()
        except:
            bar_widget = pb.Bar()
        widgets = widgets = [ args.remoteFile  + ":",
                              ' ', pb.Percentage(),
                              ' ', bar_widget,
                              ' ', pb.AdaptiveETA(),
                              ' ', pb.AdaptiveTransferSpeed() ]
        bar = pb.ProgressBar( widgets=widgets,
                              max_value=lfilesz,
                              redirect_stdout=True).start()
        updateFn = lambda x : bar.update(x)
        finishFn = lambda : bar.finish()
    else:
        updateFn = lambda x : print(x)
        finishFn = lambda : None

    while True:
        if v > 0:
            print("starting chunk %d..." % chunkCount, end='')
        updateFn(chunkCount*JDLD_CHUNK_SIZE)
        chunk = lfile.read(JDLD_CHUNK_SIZE)
        chunkLen = len(chunk)
        if chunkLen > 0:
            # try using the tempfile in a context manager
            # goddamnit screw you windows
            tf = NamedTemporaryFile(delete=False)
            tf.write(chunk)
            tf.flush()
            fn = translate_path(tf.name)
            tf.close()
            xsctCmd = 'dow -data %s %s; set done "done"' % (fn, JDLD_MAILBOX)
            resp = xsct.do(xsctCmd)
            os.unlink(tf.name)
            if resp != 'done':
                print("%s: got response %s ????" % (prog, resp))
                sock.sendall(b'D0\n'+endfile)
                sock.close()
                startStopUart(xsct, False, jtagsn=args.jtagsn)
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
            startStopUart(xsct, False, jtagsn=args.jtagsn)
            exit(1)
        if v > 0:
            print("complete.")
        chunkCount = chunkCount + 1
        if chunkLen != JDLD_CHUNK_SIZE:
            break

    finishFn()
    lfile.close()
    print("%s: Download successful after %d chunks" % (prog, chunkCount))
    sock.sendall(endfile)
    # clear out the prompt
    ln = getExpected(sock, b'jc: exiting\r\n'+prompt)
    # any post-commands?
    if postCmds:
        for cmd in postCmds:
            sock.sendall(cmd.encode()+b'\n')
            msg = getPrompt( sock, prompt, prog, v=1)
            print(msg.decode())
    sock.close()
    startStopUart(xsct, False, jtagsn=args.jtagsn)
finally:
    print("%s : exiting." % prog)
    
