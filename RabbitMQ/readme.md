# RabbitMQ Perf Test Cpde

## RabbitMQ Setup

The scripts can be run against:

- a local docker-compose cluster
- a local blockade cluster
- or a remote cluster

For now all examples use a remote cluster.

## Publishers

There are three types of publisher:

- Synchronous publisher: Sends one message at a time using a persistent connection
- Asynchronous publisher: Sends a stream of messages asynchronously. The number of in flight messages is controlled by the in-flight-max argument. Higher means higher throughput.
- New connection per message publisher: Sends one message at a time using a new connection per message

### Synchronous Publisher

```bash
$ python publisher_perf.py --name-resolution ip --nodes 192.168.233.136:rabbitmq1:5672 --queue q1 --msg-count 100000 --pub-mode sync --use-confirms true
```

### Asynchronous Publisher

```bash
$ python publisher_perf.py --name-resolution ip --nodes 192.168.233.136:rabbitmq1:5672 --queue q1 --msg-count 100000 --pub-mode async --use-confirms true --in-flight-max 10000
```

### New Connection Per Message Publisher

```bash
$ python publisher_perf.py --name-resolution ip --nodes 192.168.233.136:rabbitmq1:5672 --queue q1 --msg-count 10000 --pub-mode new-conn-per-msg --use-confirms true
```

## Amqproxy

The example Blockade and docker-compose files include an Amqproxy which listens on 5673. To use the proxy simply set the port of your publisher to 5673 instead of 5672.