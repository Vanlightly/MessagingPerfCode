#!/bin/bash

echo ""
echo "TEST docker-compose-files/$1 -------------------------------"
cd docker-compose-files/$1

if docker-compose ps | grep python > /dev/null 2>&1; then
    echo "There is an existing cluster, executing docker-compose down..."
    docker-compose down
    echo "Sleeping for two minutes to provide separation"
    sleep 120
fi

echo "Starting a client"
docker-compose up -d

cd ../../../../../cluster
echo "Adding ToxiProxy proxy"
bash proxy-add.sh

for LATENCY in 0 1 5 10 20 50 100
do
    echo "------- BEGINNING $LATENCY OF LATENCY STARTED AT $(date +%Y/%m/%dT%H:%M:%S)"
    
    if [[ $LATENCY == 0 ]]; then
        echo "Test with no added latency"
    elif [[ $LATENCY == 1 ]]; then
        echo "Test with $LATENCY ms of latency"
        bash proxy-toxics-latency-add.sh 1
    else
        echo "Test with $LATENCY ms of latency"
        bash proxy-toxics-latency-update.sh $LATENCY
    fi
    sleep $2
done

cd ../client/docker-compose-files/$1 
docker-compose down

