#!/bin/bash

curl -d '{"name":"clients","listen":"0.0.0.0:5672","upstream":"192.168.233.132:5672"}' -H "Content-Type: application/json" -X POST  http://localhost:8474/proxies
curl -d '{"name":"mgmt","listen":"0.0.0.0:15672","upstream":"192.168.233.132:15672"}' -H "Content-Type: application/json" -X POST  http://localhost:8474/proxies