#!/bin/bash
set -e

echo "=== Configuring routing tables for multipath QUIC ==="

# Mininet sets $HOST in the environment
if [[ -z "$HOST" ]]; then
    echo "HOST variable not set - this script must run inside Mininet host (h1/h2)."
    exit 1
fi

echo "Detected Mininet host: $HOST"

# Detect interfaces by IP prefix
IF1=$(ip -o -4 addr show | grep -E '10.0.1.' | awk '{print $2}')
IF2=$(ip -o -4 addr show | grep -E '10.0.2.' | awk '{print $2}')

IP1=$(ip -o -4 addr show $IF1 | awk '{print $4}' | cut -d'/' -f1)
IP2=$(ip -o -4 addr show $IF2 | awk '{print $4}' | cut -d'/' -f1)

if [[ "$HOST" == "h1" ]]; then
    PEER1="10.0.1.2"
    PEER2="10.0.2.2"
elif [[ "$HOST" == "h2" ]]; then
    PEER1="10.0.1.1"
    PEER2="10.0.2.1"
else
    echo "Unexpected HOST: $HOST"
    exit 1
fi

# Clear old rules
ip rule del from $IP1 table 1 2>/dev/null || true
ip rule del from $IP2 table 2 2>/dev/null || true

# Add rules
ip rule add from $IP1 table 1
ip rule add from $IP2 table 2

# Table 1 (Path A)
ip route add 10.0.1.0/24 dev $IF1 table 1
ip route add default via $PEER1 dev $IF1 table 1

# Table 2 (Path B)
ip route add 10.0.2.0/24 dev $IF2 table 2
ip route add default via $PEER2 dev $IF2 table 2

echo "--- Table 1 ---"
ip route show table 1
echo "--- Table 2 ---"
ip route show table 2

echo "Testing connectivity..."
ping -c 1 -I $IF1 $PEER1
ping -c 1 -I $IF2 $PEER2

echo "DONE"
