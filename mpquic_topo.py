#!/usr/bin/python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI

class MPTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Path A: low latency
        self.addLink(h1, s1,
            cls=TCLink, bw=8, delay='10ms', jitter='1ms', max_queue_size=20)
        self.addLink(s1, h2,
            cls=TCLink, bw=8, delay='10ms', jitter='1ms', max_queue_size=20)

        # Path B: higher latency but more bandwidth
        self.addLink(h1, s2,
            cls=TCLink, bw=20, delay='40ms')
        self.addLink(s2, h2,
            cls=TCLink, bw=20, delay='40ms')

def run():
    net = Mininet(topo=MPTopo(), link=TCLink, controller=None)
    net.start()

    h1, h2 = net.get('h1', 'h2')
    print("*** Assigning IPs")
    h1.setIP("10.0.1.1/24", intf="h1-eth0")
    h2.setIP("10.0.1.2/24", intf="h2-eth0")
    h1.setIP("10.0.2.1/24", intf="h1-eth1")
    h2.setIP("10.0.2.2/24", intf="h2-eth1")

    print("*** Mininet ready - run server on h2 and client on h1")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run()
