#!/bin/bash

RUN_DURATION=300
COOLDOWN_DURATION=120
#RUN_DURATION=10
#COOLDOWN_DURATION=10

run_subscribe_benchmark () {
    echo "Starting $1..."
    echo "=============================================================="

    python "$1" &

    sleep $RUN_DURATION

    pkill -f "$1"

    echo "Cooldown $1..."

    sleep $COOLDOWN_DURATION

    echo "Finished $1"
    echo "=============================================================="
    echo ""
}

python ping.py &
python pong-prometheus.py &

run_subscribe_benchmark "./subscribe-benchmark-poll-config.py"
run_subscribe_benchmark "./subscribe-benchmark-poll-state.py"
run_subscribe_benchmark "./subscribe-benchmark-poll-operational.py"
run_subscribe_benchmark "./subscribe-benchmark-poll-all.py"

run_subscribe_benchmark "./subscribe-benchmark-subscribe-sample.py"
run_subscribe_benchmark "./subscribe-benchmark-subscribe-on_change.py"

pkill -f ping.py
pkill -f pong-prometheus.py
