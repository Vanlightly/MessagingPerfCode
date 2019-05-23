import pika
from pika import spec
from pika import exceptions
import sys
import time
import subprocess
import datetime
import uuid
import random

from printer import console_out, console_out_exception

class SimplePublisher(object):
    
    def __init__(self, 
                    broker_manager,
                    publisher_id, 
                    use_proxy,
                    use_confirms,
                    new_conn_per_message,
                    print_mod):
        
        self.broker_manager = broker_manager
        self.use_proxy = use_proxy
        self.stopping = True
        self.publisher_id = publisher_id
        self.use_confirms = use_confirms
        self.new_conn_per_message = new_conn_per_message
        self.total = 0
        self.print_mod = print_mod

        # message tracking
        self.last_ack = 0
        self.pos_acks = 0
        self.neg_acks = 0
        self.undeliverable = 0
        self.curr_pos = 0
        self.msg_set = set()
        self.msg_map = dict()
        
        self.actor = ""
        self.set_actor(broker_manager.get_broker_name())

    def get_pos_ack_count(self):
        return self.pos_acks

    def get_total_ack_count(self):
        return self.pos_acks + self.neg_acks

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable}", self.get_actor())

    def get_msg_set(self):
        return self.msg_set

    def set_actor(self, connected_to):
        self.actor = f"{self.publisher_id}->{connected_to}"

    def get_actor(self):
        return self.actor

    def stop_publishing(self):
        self.stopping = True

    def open_persistent_connection(self):
        url = self.broker_manager.get_url(self.use_proxy)
        console_out(f"Attempting to connect to {url}", self.get_actor())

        try:
            parameters = pika.URLParameters(url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            if self.use_confirms:
                self.channel.confirm_delivery()

            return True
        except Exception as e:
            console_out_exception("Connection failed", e, self.get_actor())
            return False

    def publish_sequence_direct(self, queue, count):
        try:
            self.publish_sequence("", queue, count)
        finally:
            self.print_final_count
    
    def publish_sequence(self, exchange, routing_key, count):
        console_out(f"Will publish to exchange {exchange} and routing key {routing_key}", self.get_actor())
        self.exchange = exchange
        self.routing_key = routing_key
        self.total = count

        self.start_continuous_publishing()

    def start_continuous_publishing(self):
        if self.new_conn_per_message:
            console_out(f"Connections to: {self.broker_manager.get_url(self.use_proxy)}", self.get_actor())
        else:
            self.open_persistent_connection()
        self.stopping = False
                
        while not self.stopping and self.curr_pos < self.total:
            self.curr_pos += 1
                       
            body = f"pos={self.curr_pos}"
            self.msg_map[self.curr_pos] = body
            
            if self.new_conn_per_message:
                self.publish_msg_with_new_conn(self.exchange, self.routing_key, body)
            else:
                self.publish_msg_with_existing_conn(self.exchange, self.routing_key, body)

            self.msg_set.add(body)
            
            curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
            if curr_ack > self.last_ack:
                console_out(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable}", self.get_actor())
                self.last_ack = curr_ack

        console_out(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable}", self.get_actor())

    def publish_msg_with_new_conn(self, send_to_exchange, rk, body):
        url = self.broker_manager.get_url(self.use_proxy)
        
        try:
            parameters = pika.URLParameters(url)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            mandatory = False
            if self.use_confirms:
                channel.confirm_delivery()
                mandatory = True
            corr_id = str(uuid.uuid4())

            try:
                channel.basic_publish(exchange=send_to_exchange, 
                            routing_key=rk,
                            body=body,
                            mandatory=mandatory,
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
        except Exception as e:
            console_out_exception(f"Connection to {url} failed", e, self.get_actor())

    def publish_msg_with_existing_conn(self, send_to_exchange, rk, body):
        mandatory = False
        if self.use_confirms:
            mandatory = True

        corr_id = str(uuid.uuid4())

        try:
            self.channel.basic_publish(exchange=send_to_exchange, 
                        routing_key=rk,
                        body=body,
                        mandatory=mandatory,
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
