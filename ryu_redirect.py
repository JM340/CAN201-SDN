from ryu.base import app_manager
from ryu.controller import ofp_event

from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import in_proto
from ryu.lib.packet import icmp
from ryu.lib.packet import tcp

client_ip = '10.0.1.5'
server_1_ip = '10.0.1.2'
server_2_ip = '10.0.1.3'

client_mac = '00:00:00:00:00:03'
server_1_mac = '00:00:00:00:00:01'
server_2_mac = '00:00:00:00:00:02'

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self,*args,**kwargs):
        super(SimpleSwitch13,self).__init__(*args,**kwargs)
        self.mac_to_port = {}
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        msg = ev.msg
        dp = msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
             ofproto.OFPP_CONTROLLER,
             ofproto.OFPCML_NO_BUFFER   
        )]
        self.add_flow(dp,0,match,actions)

    def add_flow(self,datapath,priority,match,actions,buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, priority=priority, idle_timeout=5,
                                    match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=5,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_flow_timeout(self,datapath,priority,match,actions,buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, priority=priority, idle_timeout=5,
                                    match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=5,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def _packet_in_handler(self,ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        dp = msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        #in_port = msg.in_port
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        dpid = format(dp.id,"d").zfill(16)
        self.mac_to_port.setdefault(dpid,{})
        self.logger.info("packet in %s %s %s %s",dpid,src,dst,in_port)

        self.mac_to_port[dpid][src] = in_port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            if eth.ethertype == ether_types.ETH_TYPE_IP:
                pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
                ip_src = pkt_ipv4.src
                ip_dst = pkt_ipv4.dst
                ip_protocol = pkt_ipv4.proto

                if ip_protocol == in_proto.IPPROTO_ICMP:
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, in_port=in_port, ipv4_src=ip_src,
                        ipv4_dst=ip_dst, ip_proto=ip_protocol)
                elif ip_protocol == in_proto.IPPROTO_TCP:
                    if ip_src == client_ip and ip_dst == server_1_ip:
                        if server_2_mac in self.mac_to_port[dpid]:
                            out_port = self.mac_to_port[dpid][server_2_mac]
                        else:
                            out_port = ofproto.OFPP_FLOOD
                        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ipv4_src=ip_src,ipv4_dst=ip_dst)
                        actions = [parser.OFPActionSetField(eth_dst=server_2_mac),
                                   parser.OFPActionSetField(ipv4_dst=server_2_ip),
                                   parser.OFPActionOutput(port=out_port)]
                    elif ip_src == server_2_ip and ip_dst == client_ip:
                        if client_mac in self.mac_to_port[dpid]:
                            out_port = self.mac_to_port[dpid][client_mac]
                        else:
                            out_port = ofproto.OFPP_FLOOD

                        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,ipv4_src=ip_src,ipv4_dst=ip_dst)
                        actions = [parser.OFPActionSetField(eth_dst=server_2_mac),
                                   parser.OFPActionSetField(ipv4_dst=server_2_ip),
                                   parser.OFPActionOutput(port=out_port)]   
                    else:
                        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, in_port=in_port, ipv4_dst=ip_dst, ip_proto=ip_protocol)
            if eth.ethertype == ether_types.ETH_TYPE_ARP:
                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, in_port=in_port, eth_dst=dst,
                                        eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow_timeout(dp,1,match,actions,msg.buffer_id)
                return
            else:
                self.add_flow_timeout(dp,1,match,actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions,
                                  data=data)
        
        self.logger.info("packout event\n"
                         " dpid=%s\n"
                         " in_port=%s\n"
                         " actions=%s\n"
                         " buffer_id=%s\n",
                         dpid,in_port,actions,msg.buffer_id)

        dp.send_msg(out)


