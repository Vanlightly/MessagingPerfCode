#!/bin/bash

echo "No toxic"
sleep $1
echo "Adding slow toxic, 1ms"
bash proxy-toxics-latency-add.sh 1
sleep $1

for DELAY in 5 10 20
do
    echo "Updating slow toxic to $DELAY ms"
    bash proxy-toxics-latency-update.sh $DELAY
    sleep $1
done

echo "Deleting slow toxic"
bash proxy-toxics-latency-remove.sh