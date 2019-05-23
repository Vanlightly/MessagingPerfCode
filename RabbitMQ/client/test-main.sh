#!/bin/bash

set -e

# bash test-adding-publishers.sh "/continuous/async/without-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/async/with-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/sync/with-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/new-conn-per-msg/no-proxy-no-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/new-conn-per-msg/no-proxy-with-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/new-conn-per-msg/with-proxy-no-confirms" 5 60
# bash test-adding-publishers.sh "/continuous/new-conn-per-msg/with-proxy-with-confirms" 5 60

bash test-adding-latency.sh "/continuous/async/without-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/async/with-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/sync/with-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/new-conn-per-msg/no-proxy-no-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/new-conn-per-msg/no-proxy-with-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/new-conn-per-msg/with-proxy-no-confirms" 60
sleep 120
bash test-adding-latency.sh "/continuous/new-conn-per-msg/with-proxy-with-confirms" 60


