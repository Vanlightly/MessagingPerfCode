#!/bin/bash

curl -d '{"name":"slow","type":"latency","attributes":{"latency":'"$1"'}}' -H "nt-Type: application/json" -X POST  http://localhost:8474/proxies/clients/toxics