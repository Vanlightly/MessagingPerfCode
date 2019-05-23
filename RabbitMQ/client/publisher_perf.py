#!/usr/bin/env python

from AsyncPublisher import AsyncPublisher
from SimplePublisher import SimplePublisher
from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true, as_list, get_mandatory_arg_validated
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

    queue = get_optional_arg(args, "--queue", f"q{random.randint(0, 100000)}")
    msg_count = int(get_mandatory_arg(args, "--msg-count"))
    print_mod = int(get_optional_arg(args, "--print-mod", "1000"))
    use_confirms = is_true(get_mandatory_arg(args, "--use-confirms"))
    use_amqproxy = is_true(get_mandatory_arg(args, "--use-amqproxy"))
    use_toxiproxy = is_true(get_mandatory_arg(args, "--use-toxiproxy"))
    mgmt_ip = get_mandatory_arg(args, "--mgmt-ip")
    broker_name = get_mandatory_arg(args, "--broker-name")
    
    if use_amqproxy:
        amqproxy_ip = get_mandatory_arg(args, "--amqproxy-ip")
        amqproxy_port = get_mandatory_arg(args, "--amqproxy-port")
        broker_ip = ""
        broker_port = ""
    else:
        broker_ip = get_mandatory_arg(args, "--broker-ip")
        broker_port = get_mandatory_arg(args, "--broker-port")
        amqproxy_ip = ""
        amqproxy_port = ""

    publish_mode = get_mandatory_arg_validated(args, "--pub-mode", ["async", "sync", "new-conn-per-msg", "fire-and-forget"])
    delay_seconds = int(get_optional_arg(args, "--pub-delay", "0"))

    if delay_seconds > 0:
        console_out(f"Starting with delay of {delay_seconds} seconds", "TEST RUNNER")
        time.sleep(delay_seconds)

    broker_manager = BrokerManager(mgmt_ip, broker_name, broker_ip, broker_port, amqproxy_ip, amqproxy_port)

    queue_created = False

    while queue_created == False:  
        queue_created = broker_manager.create_queue(queue, False)

        if queue_created == False:
            time.sleep(5)

    time.sleep(2)

    if use_toxiproxy:
        proxy_created = False
        while proxy_created == False: 
            proxy_created = broker_manager.add_proxy("clients")
            if not proxy_created:
                time.sleep(5)
    
    time.sleep(2)
    
    if publish_mode == "async":
        in_flight_max = int(get_mandatory_arg(args, "--in-flight-max"))
        publisher = AsyncPublisher(broker_manager, f"PUBLISHER", use_amqproxy, use_confirms, in_flight_max, print_mod)
    elif publish_mode == "sync":
        publisher = SimplePublisher(broker_manager, f"PUBLISHER", use_amqproxy, use_confirms, False, print_mod)
    elif publish_mode == "new-conn-per-msg":
        publisher = SimplePublisher(broker_manager, f"PUBLISHER", use_amqproxy, use_confirms, True, print_mod)

    console_out(f"Starting publishing", "TEST RUNNER")
    time_start = datetime.datetime.now()


    pub_thread = threading.Thread(target=publisher.publish_sequence_direct, args=(queue, msg_count))
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