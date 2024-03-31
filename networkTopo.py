from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.node import Host, Node
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.term import makeTerm


def BuildminiNetWork():
    info("start init...\n")

    net = Mininet(topo=None,
                  autoSetMacs=True,
                  build=False,
                  ipBase='10.0.1.0/24')
    
    c1 = net.addController(
        name="c1",
        controller=RemoteController
    )
    h1 = net.addHost('h1',cls=Host,defaultRoute=None)
    h2 = net.addHost('h2',cls=Host,defaultRoute=None)
    h3 = net.addHost('h3',cls=Host,defaultRoute=None)
    
    s1 = net.addSwitch(
        name="s1",
        cls=OVSKernelSwitch,
        failMode='secure',
    )

    net.addLink(h1,s1)
    net.addLink(h2,s1)
    net.addLink(h3,s1)

    net.build()

    h1.setMAC(intf="h1-eth0",mac="00:00:00:00:00:03")
    h2.setMAC(intf="h2-eth0",mac="00:00:00:00:00:01")
    h3.setMAC(intf="h3-eth0",mac="00:00:00:00:00:02")

    h1.setIP(intf="h1-eth0",ip="10.0.1.5/24")
    h2.setIP(intf="h2-eth0",ip="10.0.1.2/24")
    h3.setIP(intf="h3-eth0",ip="10.0.1.3/24")

    net.start()

    net.terms += makeTerm(h1)
    net.terms += makeTerm(h2)
    net.terms += makeTerm(h3)
    net.terms += makeTerm(s1)
    net.terms += makeTerm(c1)

    CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel("info")
    BuildminiNetWork()