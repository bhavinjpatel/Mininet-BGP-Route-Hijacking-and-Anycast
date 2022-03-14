"""router topology example

chain of 3 routers between two hosts; simpler than the general version

    h0---r1---r2---r3
         |    |    |
        h1   h2   h3

   r1:r1-eth2--------r2-eth1:r2:r2-eth2-----------r3-eth1:r3
     10.0.1.1       10.0.1.2    10.0.2.1          10.0.2.2
Subnets are 10.0.1 (r1--r2) and 10.0.2 (r2--r3_
Last byte (host byte) is 2 on the left and 1 on the right
   10.0.?.?-r1-10.0.1.1
   10.0.1.2-r2-10.0.2.1
   10.0.2.2-r3-10.0.?.?
ri-eth0 is on the left and ri-eth1 is on the right

The "primary" IP address of ri is 10.0.i.1

The interface to the hosts is 10.0.10i.1
the host hi is 10.0.10i.10

"""

# mn --custom router.py --topo rtopo

from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
#from mininet.node import Node, Host, OVSSwitch, OVSKernelSwitch, Controller, RemoteController, DefaultController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import setLogLevel, info
import os

N=5

BGP = True

class RTopo(Topo):

    def build(self, **_opts):     # special names?
        h = [0]*(N+1)		# h[0] is a special case
        r = [0]*(N+1)
        for i in range(1, N+1):
            r[i] = self.addHost( 'r{}'.format(i) )
        # now do the same for h0-hN, with range(0,N+1)   
            
        # now set up the links h0--r1--r2--...--rN
        self.addLink( h[0], r[1], intfName1 = 'h0-eth0', intfName2 = 'r1-eth1')
        for i in range(1,N):
            self.addLink(r[i], r[i+1], intfName1 = 'r{}-eth2'.format(i), intfName2='r{}-eth1'.format(i+1))
            
        # now do the same for the ri--hi links; the interface names are ri-eth0 and hi-eth0
            


def run():
    rtopo = RTopo()
    net = Mininet(topo = rtopo, link=TCLink, autoSetMacs = True)
    net.start()
    
    # set up the ri IP addresses        
    for i in range(1,N+1):
        rname = 'r{}'.format(i)
        r=net[rname]
        r.cmd('ifconfig {}-eth0 10.0.{}.1/24'.format(rname, 10*i))
        r.cmd('ifconfig {}-eth1 10.0.{}.2/24'.format(rname, i-1))
        r.cmd('ifconfig {}-eth2 10.0.{}.1/24'.format(rname, i))
        r.cmd('sysctl net.ipv4.ip_forward=1')
        rp_disable(r)
        
    # now do the same for the hi, for i in range(1, N+1).
    # Each hi should also have a default route: 
    # For h2 this is "ip route add to default via 10.0.20.1"
 
    # now we start up the routing stuff on each router
    for i in range(1,N+1):		# for each router, do this
        rname = 'r{}'.format(i)
        r=net[rname]
        r.cmd('/usr/sbin/sshd')		# not really needed
        start_zebra(r)
        start_bgpd(r)
    
    CLI( net)

    for i in range(1,N+1):
        rname = 'r{}'.format(i)
        r=net[rname]
        r.cmd('/usr/sbin/sshd')
        stop_zebra(r)
        stop_bgpd(r)
    net.stop()
    os.system('stty erase {}'.format(chr(8)))

# in the following, ip(4,2) returns 10.0.4.2
def ip(subnet,host,prefix=None):
    addr = '10.0.'+str(subnet)+'.' + str(host)
    if prefix != None: addr = addr + '/' + str(prefix)
    return addr
    
DIRPREFIX='/home/mininet/loyola/bgp'
# DIRPREFIX='.'			# Apparently the use of relative paths leads to failure of file locking for zebra.pid
    
def start_zebra(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'zebra.conf'
    pid =  dir + 'zebra.pid'
    log =  dir + 'zebra.log'
    zsock=  dir + 'zserv.api'
    r.cmd('> {}'.format(log))
    r.cmd('rm -f {}'.format(pid))    	# we need to delete the pid file
    r.cmd('/usr/sbin/zebra --daemon --config_file {} --pid_file {} --socket {}'.format(config, pid, zsock))

def stop_zebra(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'zebra.pid'
    f = open(pidfile)
    pid = int(f.readline())
    zsock=  dir + 'zserv.api'
    r.cmd('kill {}'.format(pid))
    r.cmd('rm {}'.format(zsock))
    
def start_ripd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'ripd.conf'
    zsock  = dir + 'zserv.api'
    pid    = dir + 'ripd.pid'
    r.cmd('/usr/sbin/ripd --daemon --config_file {} --pid_file {} --socket {}'.format(config, pid, zsock))

def stop_ripd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'ripd.pid'
    f = open(pidfile)
    pid = int(f.readline())
    r.cmd('kill {}'.format(pid))

def start_bgpd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    config = dir + 'bgpd.conf'
    zsock  = dir + 'zserv.api'
    pid    = dir + 'bgpd.pid'
    r.cmd('/usr/sbin/bgpd --daemon --config_file {} --pid_file {} --socket {}'.format(config, pid, zsock))
    
def stop_bgpd(r):
    name = '{}'.format(r)
    dir='{}/{}/'.format(DIRPREFIX, name)
    pidfile =  dir + 'bgpd.pid'
    f = open(pidfile)
    pid = int(f.readline())
    r.cmd('kill {}'.format(pid))


# For some examples we need to disable the default blocking of forwarding of packets with no reverse path
def rp_disable(host):
    ifaces = host.cmd('ls /proc/sys/net/ipv4/conf')
    ifacelist = ifaces.split()    # default is to split on whitespace
    for iface in ifacelist:
       if iface != 'lo': host.cmd('sysctl net.ipv4.conf.' + iface + '.rp_filter=0')
    #print 'host', host, 'iface list:',  ifacelist


setLogLevel('debug')		# or 'info'
run()

