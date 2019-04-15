import sys
import time
import subprocess
import random
import threading
import requests
import json
from printer import console_out

class BrokerManager:
    def __init__(self):
        self.init_live_nodes = list()
        self.ports = dict()
        self.name_resolution = ""
        self.curr_node = 0
        self.fixed_port = ""

    def set_nodes_and_ports(self, nodes):
        for node_and_port in nodes:
            colon_index = node_and_port.find(":")
            if colon_index == -1:
                raise ValueError("Nodes must specify a port")
            node = node_and_port[:colon_index]
            port = node_and_port[colon_index+1:]
            self.init_live_nodes.append(node)
            self.ports[node] = port

    def set_as_service_mode(self, nodes):
        self.name_resolution = "service-name"
        self.set_nodes_and_ports(nodes)

    def set_as_localhost_mode(self, nodes):
        self.name_resolution = "localhost"
        self.init_live_nodes = nodes
        self.set_nodes_and_ports(nodes)

    def set_as_blockade_udn_mode(self, port):
        self.name_resolution = "blockade-udn"
        self.fixed_port = port
            
    def load_initial_nodes(self):
        self.init_live_nodes =  self.get_live_nodes()

    def get_initial_nodes(self):
        return self.init_live_nodes

    def get_node_index(self, node_name):
        index = 0
        for node in self.init_live_nodes:
            if node == node_name:
                return index

            index +=1

        return -1

    def set_current_node(self, node_name):
        index = self.get_node_index(node_name)
        if index == -1:
            raise ValueError(f"Node name '{node_name}' does not exist")

        self.curr_node = index

    def move_to_next_node(self):
        self.curr_node += 1
        if self.curr_node >= len(self.init_live_nodes):
            self.curr_node = 0
    
    def get_current_node(self):
        return self.init_live_nodes[self.curr_node]

    def get_node_ip(self, node_name):
        if self.name_resolution == "service-name":
            return node_name
        elif self.name_resolution == "localhost":
            return "127.0.0.1"
        elif self.name_resolution == "blockade-udn":
            bash_command = "bash ../cluster/get-node-ip.sh " + node_name
            process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            ip = output.decode('ascii').replace('\n', '')
            return ip
        else:
            raise ValueError("name_resolution value not supported")

    def get_node_port(self, node_name):
        if self.name_resolution == "blockade-udn":
            return self.fixed_port
        else:
            return self.ports[node_name]

    def get_live_nodes(self):
        if self.name_resolution == "service-name":
            return self.init_live_nodes
        elif self.name_resolution == "localhost":
            return self.init_live_nodes
        elif self.name_resolution == "blockade-udn":
            bash_command = "bash ../cluster/list-live-nodes.sh"
            process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            nodes_line = output.decode('ascii').replace('\n', '')
            nodes = list()
            for node in nodes_line.split(' '):
                if node != '' and node.isspace() == False:
                    nodes.append(node)

            return nodes

    def get_node_ips(self, live_nodes):
        ips = list()
        for node in live_nodes:
            ips.append(self.get_node_ip(node))

        return ips


    def create_queue(self, mgmt_node, queue_name, sac_enabled):
        try:
            mgmt_node_ip = self.get_node_ip(mgmt_node)
            queue_node = "rabbit@" + mgmt_node

            if sac_enabled:
                r = requests.put('htself.init_live_nodestp://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=('guest','guest'))
            else:
                r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"node\":\"" + queue_node + "\"}",
                        auth=('guest','guest'))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def create_replicated_queue(self, mgmt_node, queue_name, replication_factor, queue_type, sac_enabled):
        try:
            mgmt_node_ip = self.get_node_ip(mgmt_node)
            queue_node = "rabbit@" + mgmt_node

            if queue_type == "quorum":
                if sac_enabled:
                    r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + ",\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                            auth=('guest','guest'))
                else:
                    r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + "},\"node\":\"" + queue_node + "\"}",
                            auth=('guest','guest'))
            else:
                if sac_enabled:
                    r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                            auth=('guest','guest'))
                else:
                    r = requests.put('http://' + mgmt_node_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"auto_delete\":false,\"durable\":true,\"node\":\"" + queue_node + "\"}",
                            auth=('guest','guest'))

                r = requests.put('http://' + mgmt_node_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + replication_factor + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
                        auth=('guest','guest'))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return Falseself.init_live_nodes

    def get_init_node(self, index):
        next_index =  index % len(self.init_live_nodes)
        return self.init_live_nodes[next_index]
    
    def get_random_init_node(self):
        index = random.randint(1, len(self.init_live_nodes))
        return self.get_init_node(index)
