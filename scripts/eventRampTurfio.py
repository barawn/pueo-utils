#hacky hacks
# assumes turfManualStartup.py is already done

from EventTester import EventServer
from PueoTURF import PueoTURF
from PueoTURFIO import PueoTURFIO

# this is the one we're using
TURFIO_NUM = 0

es = EventServer()
dev = PueoTURF(None, 'Ethernet')
tio = PueoTURFIO((dev, TURFIO_NUM), 'TURFGTP')

# start off with everyone masked
mask = 0xF
# now null out the one that isn't
mask = mask & (~(1<<TURFIO_NUM))

dev.event.mask = mask
dev.event.reset()

# fill the acks
es.open()
# start the stuff
dev.trig.runcmd(dev.trig.RUNCMD_RESET)

# force the stupid trigger
tio.write(0xC, 1)

# the 2000 here is because we haven't
# increased stuff up to jumbo frames yet.
# we probably should. it's just a parameter
# set command.
frg = []
for i in range(449):
    frg.append(es.es.recv(2000))

# uh i dunno do someting
