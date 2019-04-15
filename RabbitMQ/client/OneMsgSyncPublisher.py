import pika
from pika import spec
from pika import exceptions
import sys
import time
import subprocess
import datetime
import uuid
import random

from printer import console_out

class OneMsgSyncPublisher(object):
    
    def __init__(self, 
                    broker_manager,
                    publisher_id, 
                    connect_node, 
                    use_confirms,
                    print_mod):
        
        self.broker_manager = broker_manager
        self.stopping = True
        self.publisher_id = publisher_id
        self.message_type = ""
        self.exchange = ""   
        self.exchanges = list()
        self.user = "guest"
        self.password = "guest"
        self.use_confirms = use_confirms
        self.routing_key = ""
        self.count = 0
        self.sequence_count = 0
        self.dup_rate = 0.0
        self.total = 0
        self.print_mod = print_mod

        # message tracking
        self.last_ack_time = datetime.datetime.now()
        self.last_ack = 0
        self.seq_no = 0
        self.curr_pos = 0
        self.pos_acks = 0
        self.neg_acks = 0
        self.undeliverable = 0
        self.no_acks = 0
        self.key_index = 0
        self.keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        self.val = 1
        self.msg_set = set()
        self.msg_map = dict()
        
        self.actor = ""
        self.connected_node = connect_node
        self.broker_manager.set_current_node(connect_node)
        self.set_actor()

    def get_pos_ack_count(self):
        return self.pos_acks

    def set_actor(self):
        self.actor = f"{self.publisher_id}->{self.connected_node}"

    def get_actor(self):
        return self.actor

    def stop_publishing(self):
        self.stopping = True

    def get_url(self):
        self.connected_node = self.broker_manager.get_current_node()
        address = self.broker_manager.get_node_ip(self.connected_node)
        port = self.broker_manager.get_node_port(self.connected_node)
        url = f"amqp://{self.user}:{self.password}@{address}:{port}/%2F"

        return url

    def publish_msg(self, send_to_exchange, rk, body):
        url = self.get_url()
        parameters = pika.URLParameters(url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        if self.use_confirms:
            channel.confirm_delivery()
        corr_id = str(uuid.uuid4())

        try:
            channel.basic_publish(exchange=send_to_exchange, 
                        routing_key=rk,
                        body=body,
                        mandatory=True,
                        properties=pika.BasicProperties(content_type='text/plain',
                                                delivery_mode=2,
                                                correlation_id=corr_id))
            self.pos_acks += 1
        except exceptions.UnroutableError:                                            
            self.undeliverable += 1
            if self.undeliverable % 100 == 0:
                console_out(f"{str(self.undeliverable)} messages could not be delivered", self.get_actor())
        except exceptions.NackError:
            self.neg_acks += 1

        connection.close()        


    def start_publishing(self):
        console_out(f"Connections to: {self.get_url()}", self.get_actor())
        self.stopping = False
        rk = self.routing_key
        body = ""
        curr_exchange = 0
        send_to_exchange = None
        
        while not self.stopping and self.curr_pos < self.total:
            self.curr_pos += 1
            self.seq_no += 1
                       
            if self.message_type == "partitioned-sequence":
                rk = self.keys[self.key_index]
                body = f"{self.keys[self.key_index]}={self.val}"
                self.msg_map[self.seq_no] = body
            elif self.message_type == "sequence":
                body = f"{self.keys[self.key_index]}={self.val}"
                self.msg_map[self.seq_no] = body
            else:
                body = "hello"
            
            if self.exchange != None:
                send_to_exchange = self.exchange
            else:
                if curr_exchange >= len(self.exchanges):
                    curr_exchange = 0
                
                send_to_exchange = self.exchanges[curr_exchange]
                curr_exchange += 1
                
            self.publish_msg(send_to_exchange, rk, body)

            self.msg_set.add(body)
            self.key_index += 1
            if self.key_index == self.sequence_count:
                self.key_index = 0
                self.val += 1

            curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
            if curr_ack > self.last_ack:
                console_out(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
                self.last_ack = curr_ack


        console_out(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())


    def publish_direct(self, queue, count, sequence_count, dup_rate, message_type):
        try:
            self.publish("", queue, count, sequence_count, dup_rate, message_type)
        except KeyboardInterrupt:
            self.print_final_count
    
    def publish_to_exchanges(self, exchanges, routing_key, count, sequence_count, dup_rate, message_type):
        try:
            self.exchanges = exchanges
            self.publish(None, routing_key, count, sequence_count, dup_rate, message_type)
        except KeyboardInterrupt:
            self.print_final_count

    def publish(self, exchange, routing_key, count, sequence_count, dup_rate, message_type):
        console_out(f"Will publish to exchange {exchange} and routing key {routing_key}", self.get_actor())
        self.exchange = exchange
        self.routing_key = routing_key
        self.count = count
        self.sequence_count = sequence_count
        self.dup_rate = dup_rate

        if count == -1:
            self.total = 100000000
        else:
            self.total = count * sequence_count

        self.message_type = message_type

        if self.message_type == "partitioned-sequence":
            console_out("Routing key is ignored with the sequence type", self.get_actor())

        if self.sequence_count > 10:
            console_out("Key count limit is 10", self.get_actor())
            exit(1)

        allowed_types = ["partitioned-sequence", "sequence", "large-msgs", "hello"]
        if self.message_type not in allowed_types:
            console_out(f"Valid message types are: {allowed_types}", self.get_actor())
            exit(1)

        self.start_publishing()

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())

    def get_msg_set(self):
        return self.msg_set