import sys
import time
import subprocess
import random
import threading
import requests
import json
from printer import console_out, console_out_exception

class BrokerManager:
    def __init__(self, mgmt_ip, broker_name, broker_ip, broker_port, amqproxy_ip, amqproxy_port):
        self.mgmt_ip = mgmt_ip
        self.broker_name = broker_name
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.amqproxy_ip = amqproxy_ip
        self.amqproxy_port = amqproxy_port
        self.user = "test"
        self.password = "test"
            
    def get_broker_name(self):
        return self.broker_name

    def get_broker_ip(self):
        return self.broker_ip

    def get_broker_port(self):
        return self.broker_port

    def get_amqproxy_ip(self):
        return self.amqproxy_ip

    def get_amqproxy_port(self):
        return self.amqproxy_port

    def create_queue(self, queue_name, sac_enabled):
        try:
            queue_node = "rabbit@" + self.broker_name

            if sac_enabled:
                r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": true},\"node\":\"" + queue_node + "\"}",
                        auth=(self.user,self.password))
            else:
                r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                        data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-queue-mode\":\"lazy\"},\"node\":\"" + queue_node + "\"}",
                        auth=(self.user,self.password))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def create_replicated_queue(self, queue_name, replication_factor, queue_type, sac_enabled):
        try:
            queue_node = "rabbit@" + self.broker_name

            if queue_type == "quorum":
                if sac_enabled:
                    r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + ",\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                            auth=(self.user,self.password))
                else:
                    r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"durable\":true,\"arguments\":{\"x-queue-type\":\"quorum\", \"x-quorum-initial-group-size\":" + replication_factor + "},\"node\":\"" + queue_node + "\"}",
                            auth=(self.user,self.password))
            else:
                if sac_enabled:
                    r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"auto_delete\":false,\"durable\":true,\"arguments\":{\"x-single-active-consumer\": false},\"node\":\"" + queue_node + "\"}",
                            auth=(self.user,self.password))
                else:
                    r = requests.put('http://' + self.mgmt_ip + ':15672/api/queues/%2F/' + queue_name, 
                            data = "{\"auto_delete\":false,\"durable\":true,\"node\":\"" + queue_node + "\"}",
                            auth=(self.user,self.password))

                r = requests.put('http://' + self.mgmt_ip + ':15672/api/policies/%2F/ha-queues', 
                        data = "{\"pattern\":\"" + queue_name + "\", \"definition\": {\"ha-mode\":\"exactly\", \"ha-params\": " + replication_factor + ",\"ha-sync-mode\":\"automatic\" }, \"priority\":0, \"apply-to\": \"queues\"}",
                        auth=(self.user,self.password))

            console_out(f"Created {queue_name} with response code {r}", "TEST_RUNNER")

            return r.status_code == 201 or r.status_code == 204
        except Exception as e:
            console_out("Could not create queue. Will retry. " + str(e), "TEST RUNNER")
            return False

    def get_url(self, use_proxy):
        if use_proxy:
            return self.get_url_for(self.get_amqproxy_ip(), self.get_amqproxy_port())
        else:
            return self.get_url_for(self.get_broker_ip(), self.get_broker_port())

    def get_url_for(self, ip, port):
        url = f"amqp://{self.user}:{self.password}@{ip}:{port}/%2F"

        return url

    def add_proxy(self, name):
        try:
            r = requests.post("http://toxiproxy:8474/proxies", 
                    data = "{\"name\":\"" + name + "\",\"listen\":\"0.0.0.0:5672\",\"upstream\":\"" + self.mgmt_ip + ":5672\"}")
            
            console_out(f"Proxy add response: {r}", "TEST RUNNER")
            return r.status_code == 201 or r.status_code == 204 or r.status_code == 409
        except Exception as e:
            console_out_exception("Could not add proxy", e, "TEST RUNNER")
            return False
