import pika
from pika import spec
import sys
import time
import subprocess
import datetime
import uuid
import random

from printer import console_out, console_out_exception
from BrokerManager import BrokerManager

class AsyncPublisher(object):
    
    def __init__(self, 
                broker_manager, 
                publisher_id, 
                use_proxy,
                use_confirms,
                in_flight_limit, 
                print_mod):
        
        self.broker_manager = broker_manager
        self.connection = None
        self.channel = None
        self.stopping = False

        self.publisher_id = publisher_id
        self.use_proxy = use_proxy
        self.use_confirms = use_confirms
        self.exchange = ""   
        self.routing_key = ""
        self.total = 0
        self.in_flight_limit = in_flight_limit
        self.confirm_timeout_sec = 300
        self.print_mod = print_mod

        # message tracking
        self.last_ack_time = datetime.datetime.now()
        self.last_ack = 0
        self.seq_no = 0
        self.curr_pos = 0
        self.expected = 0
        self.pending_messages = list()
        self.pos_acks = 0
        self.neg_acks = 0
        self.undeliverable = 0
        self.no_acks = 0
        self.key_index = 0
        self.val = 1
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.msg_set = set()
        self.msg_map = dict()
        
        self.actor = ""
        self.set_actor(broker_manager.get_broker_name())

    def reset_ack_tracking(self):
        pending_count = len(self.pending_messages)
        if pending_count > 0:
            console_out(f"{pending_count} messages were pending acknowledgement. Adjusted expected count to: {self.expected - pending_count}", self.get_actor())
            self.expected = self.expected - pending_count
        
        self.waiting_for_acks = False
        self.waiting_for_acks_sec = 0
        self.pending_messages.clear()

    def get_pos_ack_count(self):
        return self.pos_acks

    def get_total_ack_count(self):
        return self.pos_acks + self.neg_acks

    def print_final_count(self):
        console_out(f"Final Count => Sent: {self.curr_pos} Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())

    def get_msg_set(self):
        return self.msg_set

    def set_actor(self, connected_to):
        self.actor = f"{self.publisher_id}->{connected_to}"

    def get_actor(self):
        return self.actor

    def connect(self):
        url = self.broker_manager.get_url(self.use_proxy)
        console_out(f"Attempting to connect to {url}", self.get_actor())
        parameters = pika.URLParameters(url)
        return pika.SelectConnection(parameters,
                                     on_open_callback=self.on_connection_open,
                                     on_open_error_callback=self.on_connection_open_error,
                                     on_close_callback=self.on_connection_closed)

    def on_connection_open(self, unused_connection):
        console_out(f'Connection opened: {unused_connection}', self.get_actor())
        self.open_channel()
        
    def on_connection_open_error(self, unused_connection, err):
        console_out(f'Connection open failed, reopening in 5 seconds: {err}', self.get_actor())
        self.connection.ioloop.call_later(5, self.connection.ioloop.stop)

    def on_connection_closed(self, connection, reason):
        self.channel = None
        if self.stopping:
            self.connection.ioloop.stop()                
        else:
            console_out(f"Connection closed. Reason: {reason}. Reopening in 5 seconds.", self.get_actor())
            self.connection.ioloop.call_later(5, self.connection.ioloop.stop)

    def open_channel(self):
        self.connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self.channel = channel
        self.add_on_channel_close_callback()
        console_out('Channel opened, publishing to commence', self.get_actor())
                
        self.reset_ack_tracking()
        self.seq_no = 0
        self.start_publishing()

    def add_on_channel_close_callback(self):
        self.channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        console_out(f"Channel {channel} was closed. Reason: {reason}", self.get_actor())
        self.channel = None
        if not self.stopping:
            if self.connection.is_open:    
                self.connection.close()

    def stop_publishing(self):
        self.stop(True)

    def stop(self, full_stop):
        if not self.stopping:
            if full_stop:
                self.stopping = True

            self.close_connection()

            if full_stop:
                self.print_final_count()
            else:
                console_out("Reopening a new connection in 10 seconds", self.get_actor())
                self.broker_manager.move_to_next_node()
                self.connection.ioloop.call_later(10, self.connection.ioloop.stop)

    def close_channel(self):
        if self.channel is not None:
            self.channel.close()

    def close_connection(self):
        if self.connection is not None and self.connection.is_open:
            try:
                console_out("Closing connection...", self.get_actor())
                self.connection.close()
                console_out("Connection closed", self.get_actor())
            except pika.execeptions.ConnectionWrongStateError:
                console_out("Cannot close connection, already closed", self.get_actor())
            except Exception as e:
                console_out_exception("Failed closing connection", e, self.get_actor())

    def enable_delivery_confirmations(self):
        self.channel.confirm_delivery(self.on_delivery_confirmation)
        self.channel.add_on_return_callback(callback=self.on_undeliverable)

    def on_undeliverable(self, channel, method, properties, body):
        self.undeliverable += 1
        if self.undeliverable % 100 == 0:
            console_out(f"{str(self.undeliverable)} messages could not be delivered", self.get_actor())

    def publish_sequence_direct(self, queue, count):
        self.publish_sequence("", queue, count)
    
    def publish_sequence(self, exchange, routing_key, count):
        self.stopping = False
        console_out(f"Will publish to exchange {exchange} and routing key {routing_key}", self.get_actor())
        self.exchange = exchange
        self.routing_key = routing_key
        self.total = count
        self.expected = self.total
        
        while not self.stopping:
            self.connection = None

            self.connection = self.connect()
            self.connection.ioloop.start()

        console_out("Publisher terminated", self.get_actor())

    def start_publishing(self):
        if self.channel == None or not self.channel.is_open:
            return

        if self.use_confirms:
            self.enable_delivery_confirmations()
        
        while not self.stopping and self.curr_pos < self.total:
            if self.waiting_for_acks_sec > self.confirm_timeout_sec:
                console_out("Confirms timed out. Removing pending confirms from tracking. Opening new connection.", self.get_actor())
                self.no_acks += len(self.pending_messages)
                self.reset_ack_tracking()
                self.stop(False) # close connection but do not shutdown
                break

            if self.channel.is_open:
                if self.curr_pos % 10 == 0:
                    if len(self.pending_messages) >= self.in_flight_limit:
                        self.waiting_for_acks = True
                        self.waiting_for_acks_sec += 1
                        if self.channel.is_open:
                            self.connection.ioloop.call_later(0.1, self.start_publishing)
                            break

                self.waiting_for_acks = False
                self.waiting_for_acks_sec = 0
                self.curr_pos += 1
                self.seq_no += 1
                corr_id = str(uuid.uuid4())
                
                body = f"sequence={self.val}"
                self.msg_map[self.seq_no] = body
                mandatory = self.use_confirms
                                
                self.channel.basic_publish(exchange=self.exchange, 
                                    routing_key=self.routing_key,
                                    body=body,
                                    mandatory=mandatory,
                                    properties=pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=2,
                                                            correlation_id=corr_id))

                
                if self.use_confirms:
                    self.pending_messages.append(self.seq_no)
                else:
                    self.pos_acks += 1
                    curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
                    if curr_ack > self.last_ack:
                        console_out(f"Sent: {self.pos_acks}", self.get_actor())
                        self.last_ack = curr_ack
                        
                        # for some reason, without confirms the select connection does not send messages unless we manually pol the ioloop
                        if not self.use_confirms:
                            self.connection.ioloop.poll() 

                self.val += 1
            else:
                console_out("Channel closed, ceasing publishing", self.get_actor())
                break

    def on_delivery_confirmation(self, frame):
        if isinstance(frame.method, spec.Basic.Ack) or isinstance(frame.method, spec.Basic.Nack):
            if frame.method.multiple == True:
                acks = 0
                messages_to_remove = [item for item in self.pending_messages if item <= frame.method.delivery_tag]
                for val in messages_to_remove:
                    try:
                        self.pending_messages.remove(val)
                        if isinstance(frame.method, spec.Basic.Ack) and val in self.msg_map:
                            self.msg_set.add(self.msg_map[val])
                    except:
                        console_out(f"Could not remove multiple flag message: {val}", self.get_actor())
                    acks += 1
            else:
                try:
                    self.pending_messages.remove(frame.method.delivery_tag) 
                    if isinstance(frame.method, spec.Basic.Ack) and frame.method.delivery_tag in self.msg_map:
                        self.msg_set.add(self.msg_map[frame.method.delivery_tag])
                except:
                    console_out(f"Could not remove non-multiple flag message: {frame.method.delivery_tag}", self.get_actor())
                acks = 1

        if isinstance(frame.method, spec.Basic.Ack):
            self.pos_acks += acks
        elif isinstance(frame.method, spec.Basic.Nack):
            self.neg_acks += acks
        elif isinstance(frame.method, spec.Basic.Return):
            console_out("Undeliverable message", self.get_actor())
        
        curr_ack = int((self.pos_acks + self.neg_acks) / self.print_mod)
        if curr_ack > self.last_ack:
            console_out(f"Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self.last_ack = curr_ack

        if (self.pos_acks + self.neg_acks) >= self.expected:
            console_out(f"Final Count => Pos acks: {self.pos_acks} Neg acks: {self.neg_acks} Undeliverable: {self.undeliverable} No Acks: {self.no_acks}", self.get_actor())
            self.stop(True)
    