#!/usr/bin/python3
"""
Network topologies for testing multipath QUIC schedulers
Based on evaluation scenarios from the paper:
"Reinforcement Learning Based Multipath QUIC Scheduler for Multimedia Streaming"
https://www.mdpi.com/1424-8220/22/17/6333
"""
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.node import Controller
import os
import sys


class Topo1(Topo):
    """
    Topology 1 (Default/Original): WiFi-like + Cellular-like paths
    Path A: 8 Mbps, 10ms delay, 1ms jitter (WiFi-like)
    Path B: 20 Mbps, 40ms delay (LTE-like)
    """
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Path A: low-latency, moderate bandwidth
        self.addLink(h1, s1, cls=TCLink, bw=8, delay='10ms', jitter='1ms', max_queue_size=20)
        self.addLink(s1, h2, cls=TCLink, bw=8, delay='10ms', jitter='1ms', max_queue_size=20)

        # Path B: high-latency, high-bandwidth
        self.addLink(h1, s2, cls=TCLink, bw=20, delay='40ms', max_queue_size=40)
        self.addLink(s2, h2, cls=TCLink, bw=20, delay='40ms', max_queue_size=40)


class Topo2(Topo):
    """
    Topology 2: Diverse RTT Paths (from paper Section 5.2)
    Path A: 20 Mbps, 5ms delay (fast path)
    Path B: 15 Mbps, 77ms delay (slow path)
    No packet loss
    """
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Path A: fast path
        self.addLink(h1, s1, cls=TCLink, bw=20, delay='5ms', max_queue_size=50)
        self.addLink(s1, h2, cls=TCLink, bw=20, delay='5ms', max_queue_size=50)

        # Path B: slow path
        self.addLink(h1, s2, cls=TCLink, bw=15, delay='77ms', max_queue_size=50)
        self.addLink(s2, h2, cls=TCLink, bw=15, delay='77ms', max_queue_size=50)


class Topo3(Topo):
    """
    Topology 3: Similar RTT with Packet Loss (from paper Section 5.3)
    Path A: 50 Mbps, 6ms delay (fast, reliable)
    Path B: 5 Mbps, 8ms delay, high packet loss (slow, lossy)
    """
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Path A: fast, reliable
        self.addLink(h1, s1, cls=TCLink, bw=50, delay='6ms', max_queue_size=100)
        self.addLink(s1, h2, cls=TCLink, bw=50, delay='6ms', max_queue_size=100)

        # Path B: slow with packet loss
        self.addLink(h1, s2, cls=TCLink, bw=5, delay='8ms', loss=10, max_queue_size=100)
        self.addLink(s2, h2, cls=TCLink, bw=5, delay='8ms', loss=10, max_queue_size=100)


class Topo4(Topo):
    """
    Topology 4: Adaptive Bitrate Test (from paper Section 5.5 - Figure 15)
    Path A: 7 Mbps, 10ms delay (fast)
    Path B: 6 Mbps, 200ms delay, 10% loss (slow with loss)
    Similar bandwidth but large delay difference - tests adaptive bitrate selection
    """
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Path A: low latency, moderate bandwidth
        self.addLink(h1, s1, cls=TCLink, bw=7, delay='10ms', max_queue_size=50)
        self.addLink(s1, h2, cls=TCLink, bw=7, delay='10ms', max_queue_size=50)

        # Path B: high latency, similar bandwidth, with packet loss
        self.addLink(h1, s2, cls=TCLink, bw=6, delay='200ms', loss=10, max_queue_size=50)
        self.addLink(s2, h2, cls=TCLink, bw=6, delay='200ms', loss=10, max_queue_size=50)


# Topology registry
TOPOLOGIES = {
    1: (Topo1, "WiFi-like + Cellular-like (8Mbps/10ms + 20Mbps/40ms) [DEFAULT]"),
    2: (Topo2, "Diverse RTT (20Mbps/5ms + 15Mbps/77ms) [Paper Sec 5.2]"),
    3: (Topo3, "Similar RTT with Loss (50Mbps/6ms + 5Mbps/8ms/10%loss) [Paper Sec 5.3]"),
    4: (Topo4, "Adaptive Bitrate (7Mbps/10ms + 6Mbps/200ms/10%loss) [Paper Sec 5.5 - Fig 15]"),
}


# Keep backward compatibility
MPTopo = Topo1

def run(topo_num=1):
    """Run Mininet with specified topology number"""
    
    if topo_num not in TOPOLOGIES:
        print(f"Error: Unknown topology number '{topo_num}'")
        print(f"\nAvailable topologies:")
        for num, (_, desc) in TOPOLOGIES.items():
            print(f"  {num} - {desc}")
        sys.exit(1)
    
    topo_class, description = TOPOLOGIES[topo_num]
    info(f"*** Creating Topology {topo_num}: {description}\n")
    
    net = Mininet(topo=topo_class(), link=TCLink, controller=Controller)
    net.start()

    h1, h2 = net.get('h1', 'h2')

    info("*** Assigning IPs\n")
    h1.setIP("10.0.1.1/24", intf="h1-eth0")
    h2.setIP("10.0.1.2/24", intf="h2-eth0")

    h1.setIP("10.0.2.1/24", intf="h1-eth1")
    h2.setIP("10.0.2.2/24", intf="h2-eth1")

    # Ensure startup.sh exists in current directory
    if not os.path.exists("startup.sh"):
        raise FileNotFoundError("startup.sh not found in current directory!")

    info("*** Running startup script on h1\n")
    h1.cmd("chmod +x startup.sh")
    print(h1.cmd(f"HOST={h1.name} ./startup.sh"))

    info("*** Running startup script on h2\n")
    h2.cmd("chmod +x startup.sh")
    print(h2.cmd(f"HOST={h2.name} ./startup.sh"))

    info(f"\n*** Topology {topo_num} ready - routing configured automatically\n")
    info("*** Run QUIC server on h2 and client on h1\n")
    info("*** Use 'source run_all_experiments.sh' to run all schedulers\n")

    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    
    # Parse command line argument for topology choice
    topo_num = 1  # default
    if len(sys.argv) > 1:
        try:
            topo_num = int(sys.argv[1])
        except ValueError:
            print(f"Error: Topology number must be an integer")
            print(f"\nAvailable topologies:")
            for num, (_, desc) in TOPOLOGIES.items():
                print(f"  {num} - {desc}")
            sys.exit(1)
    
    run(topo_num)
