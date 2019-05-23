from flask import Flask
from SimplePublisher import SimplePublisher
from command_args import get_args, get_mandatory_arg, get_optional_arg, is_true, as_list, get_mandatory_arg_validated
from BrokerManager import BrokerManager
from printer import console_out, console_out_exception

import random
import time
import datetime
import sys

app = Flask(__name__)

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

args = get_args(sys.argv)
queue = get_optional_arg(args, "--queue", f"q{random.randint(0, 100000)}")
print_mod = int(get_optional_arg(args, "--print-mod", "1000"))
use_confirms = is_true(get_mandatory_arg(args, "--use-confirms"))
mgmt_ip = get_mandatory_arg(args, "--mgmt-ip")
broker_name = get_mandatory_arg(args, "--broker-name")
broker_ip = get_mandatory_arg(args, "--broker-ip")
broker_port = get_mandatory_arg(args, "--broker-port")
amqproxy_ip = get_mandatory_arg(args, "--amqproxy-ip")
amqproxy_port = get_mandatory_arg(args, "--amqproxy-port")

broker_manager = BrokerManager(mgmt_ip, broker_name, broker_ip, broker_port, amqproxy_ip, amqproxy_port)

queue_created = False

while queue_created == False:  
    queue_created = broker_manager.create_queue(queue, False)

    if queue_created == False:
        time.sleep(5)

time.sleep(2)
    
proxy_publisher = SimplePublisher(broker_manager, f"PUBLISHER", True, use_confirms, True, print_mod)
nonproxy_publisher = SimplePublisher(broker_manager, f"PUBLISHER", False, use_confirms, True, print_mod)

@app.route("/proxy")
def send_to_proxy():
    try:
        proxy_publisher.publish_msg_with_new_conn("", "", f"Hello at {datetime.datetime.now()}")
        return ""
    except Exception as e:
        console_out_exception("Proxy", e, "WEB")
        return str(e)

@app.route("/noproxy")
def send_to_broker():
    try:
        nonproxy_publisher.publish_msg_with_new_conn("", "", f"Hello at {datetime.datetime.now()}")
        return ""
    except Exception as e:
        console_out_exception("NoProxy", e, "WEB")
        return str(e)

if __name__ == "__main__":
    app.run(threaded=True, host='0.0.0.0')