#!/usr/bin/env python

from AsyncPublisher import AsyncPublisher
from SyncPublisher import SyncPublisher
from OneMsgSyncPublisher import OneMsgSyncPublisher
from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true, as_list
from BrokerManager import BrokerManager
from printer import console_out

import time
import datetime
import sys
import threading
import random

import signal

def sigterm_handler(_signo, _stack_frame):
    print("sigterm_handler executed, %s, %s" % (_signo, _stack_frame))
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sigterm_handler)

    args = get_args(sys.argv)

    name_resolution = get_mandatory_arg(args, "--name-resolution")
    queue = get_optional_arg(args, "--queue", f"q{random.randint(0, 100000)}")
    msg_count = int(get_mandatory_arg(args, "--msg-count"))
    print_mod = int(get_optional_arg(args, "--print-mod", "1000"))
    in_flight_max = int(get_optional_arg(args, "--in-flight-max", "10"))
    publish_mode = get_mandatory_arg(args, "--pub-mode")
    use_confirms = is_true(get_mandatory_arg(args, "--use-confirms"))
    delay_seconds = int(get_optional_arg(args, "--pub-delay", "0"))

    if delay_seconds > 0:
        console_out(f"Starting with delay of {delay_seconds} seconds", "TEST RUNNER")
        time.sleep(delay_seconds)

    broker_manager = BrokerManager()
    
    if name_resolution == "service-name":
        nodes_list = as_list(get_mandatory_arg(args, "--nodes"))
        connect_mode = nodes_list[0][:nodes_list[0].find(":")]
        broker_manager.set_as_service_mode(nodes_list)
    elif name_resolution == "ip":
        nodes_list = as_list(get_mandatory_arg(args, "--nodes"))
        connect_mode = nodes_list[0].split(":")[1]
        broker_manager.set_as_ip_mode(nodes_list)
    elif name_resolution == "blockade-udn":
        node_port  = get_mandatory_arg(args, "--port")
        broker_manager.set_as_blockade_udn_mode(node_port)

    broker_manager.load_initial_nodes()
    initial_nodes = broker_manager.get_initial_nodes()
    console_out(f"Initial nodes: {initial_nodes}", "TEST RUNNER")

    queue_name = queue
    mgmt_node = broker_manager.get_random_init_node()
    queue_created = False

    while queue_created == False:  
        queue_created = broker_manager.create_queue(mgmt_node, queue_name, False)

        if queue_created == False:
            time.sleep(5)

    time.sleep(2)
    
    if publish_mode == "async":
        publisher = AsyncPublisher(broker_manager, f"PUBLISHER", broker_manager.get_random_init_node(), in_flight_max, 120, print_mod)
    elif publish_mode == "sync":
        publisher = SyncPublisher(broker_manager, f"PUBLISHER", broker_manager.get_random_init_node(), in_flight_max, 120, print_mod)
    elif publish_mode == "new-conn-per-msg":
        publisher = OneMsgSyncPublisher(broker_manager, f"PUBLISHER", broker_manager.get_random_init_node(), use_confirms, print_mod)

    console_out(f"Starting publishing", "TEST RUNNER")
    time_start = datetime.datetime.now()


    pub_thread = threading.Thread(target=publisher.publish_direct, args=(queue_name, msg_count, 1, 0, "sequence"))
    pub_thread.start()

    try:
        while pub_thread.is_alive():
            time.sleep(1)
            if publisher.get_total_ack_count() == msg_count:
                break
    except KeyboardInterrupt:
        console_out(f"User requested stop", "TEST RUNNER")
    finally:
        publisher.stop_publishing()
        console_out(f"Stopping...", "TEST RUNNER")
        time_end = datetime.datetime.now()
        pub_thread.join()
        
        console_out(f"Publishing complete", "TEST RUNNER")

        avg_pub_rate = publisher.get_total_ack_count() / (time_end-time_start).total_seconds()
        console_out(f"AVG MESSAGES PER SECOND {avg_pub_rate}", "TEST RUNNER")