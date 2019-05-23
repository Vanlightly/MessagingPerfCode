#!/bin/bash

echo ""
echo "TEST docker-compose-files/$1 -------------------------------"
cd docker-compose-files/$1

for LATENCY in 0 1 5 10 20 50 100
do
    if docker-compose ps | grep python > /dev/null 2>&1; then
        echo "There is an existing cluster, executing docker-compose down..."
        docker-compose down
        echo "Sleeping for two minutes to provide separation"
        sleep 120
    fi

    echo "-------------------------------------------------------"
    echo TEST $1 WITH $LATENCY OF LATENCY STARTED AT $(date +%Y/%m/%dT%H:%M:%S) 
    echo "Starting client 1"
    docker-compose up -d

    cd ../../../../../cluster
    echo "Adding ToxiProxy proxy"
    bash proxy-add.sh

    if [[ $LATENCY == 0 ]]; then
        echo "Test with no added latency"
    elif [[ $LATENCY == 1 ]]; then
        echo "Test with $LATENCY ms of latency"
        bash proxy-toxics-latency-add.sh 1
    else
        echo "Test with $LATENCY ms of latency"
        bash proxy-toxics-latency-add.sh $LATENCY
    fi
    sleep $3
    cd ../client/docker-compose-files/$1  

    for ((NUM=2; NUM<=$2; NUM++))
    do
        echo "Starting client $NUM"
        docker-compose up -d --scale rmq-publisher=$NUM
        sleep $3
    done
    docker-compose down
    echo TEST $1 WITH $LATENCY OF LATENCY ENDED AT $(date +%Y/%m/%dT%H:%M:%S) 
    echo "-------------------------------------------------------"

    sleep 120
done

