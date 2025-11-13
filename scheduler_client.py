import asyncio
import time
import json
import random
import socket
import os
import sys

from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.asyncio.protocol import QuicConnectionProtocol


LOG = []
SEQ = 0

# Schedulers
SCHED_MIN_RTT = "minrtt"
SCHED_WRR = "wrr"
SCHED_REDUNDANT = "redundant"
SCHED_PREDICT = "predict"
VALID_SCHEDULERS = [SCHED_MIN_RTT, SCHED_WRR, SCHED_REDUNDANT, SCHED_PREDICT]

# Prediction weights
alpha = 0.5
beta = 0.8
gamma = 1.2


class PathState:
    def __init__(self, name, conn, stream_id):
        self.name = name
        self.conn = conn
        self.stream = stream_id
        self.rtts = []
        self.last_seq = -1
        self.bytes_sent = 0

    @property
    def rtt(self):
        return sum(self.rtts) / len(self.rtts) if self.rtts else 0.03

    @property
    def jitter(self):
        if len(self.rtts) < 2:
            return 0
        diffs = [abs(self.rtts[i] - self.rtts[i - 1]) for i in range(1, len(self.rtts))]
        return sum(diffs) / len(diffs)

    @property
    def bw(self):
        # rough proxy for bandwidth: more bytes_sent → more bw
        return max(1, self.bytes_sent)

    def log_rtt(self, r):
        self.rtts.append(r)


def score_path(path, other_last_seq):
    pred = path.rtt + alpha * path.jitter + beta * (1 / path.bw)
    reorder_pen = gamma * max(0, path.last_seq - other_last_seq)
    return pred + reorder_pen


async def quic_connect(local_ip, server_ip, port=4443):
    # 1. QUIC config
    conf = QuicConfiguration(is_client=True, alpn_protocols=["hq-29"])

    # 2. Bind UDP to interface
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, 0))

    # 3. Create low-level QUIC connection
    quic = QuicConnection(configuration=conf)

    # 4. Wrap inside protocol handler
    protocol = QuicConnectionProtocol(quic)

    # 5. Register with event loop
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(lambda: protocol, sock=sock)

    # 6. Connect + handshake
    quic.connect((server_ip, port), now=time.time())
    protocol.transmit()

    return protocol


def open_stream_id(quic):
    try:
        return quic.get_next_available_stream_id(is_unidirectional=False)
    except TypeError:
        return quic.get_next_available_stream_id()


def send_chunk(pstate, stream_id, chunk):
    # write bytes into a specific stream ID
    pstate.conn._quic.send_stream_data(stream_id, chunk, end_stream=False)
    pstate.conn.transmit()


async def main(sched=SCHED_PREDICT):
    global SEQ, LOG

    print(f"*** Starting scheduler: {sched}")

    # Connect both paths
    connA = await quic_connect("10.0.1.1", "10.0.1.2")
    connB = await quic_connect("10.0.2.1", "10.0.2.2")

    # Open streams
    streamA = open_stream_id(connA._quic)
    streamB = open_stream_id(connB._quic)

    # Path state
    pathA = PathState("A", connA, streamA)
    pathB = PathState("B", connB, streamB)

    # send scheduler header on both streams
    header = f"SCHED:{sched}".encode()
    pA = pathA.conn._quic
    pB = pathB.conn._quic
    pA.send_stream_data(streamA, header, end_stream=False)
    pB.send_stream_data(streamB, header, end_stream=False)
    pathA.conn.transmit()
    pathB.conn.transmit()

    CHUNK = b"x" * 500
    TOTAL = 500

    while SEQ < TOTAL:
        # Fake RTT sampling for now (will replace w/ ACK timing)
        pathA.log_rtt(random.uniform(0.01, 0.03))
        pathB.log_rtt(random.uniform(0.03, 0.07))

        # Choose scheduler
        if sched == SCHED_MIN_RTT:
            chosen = pathA if pathA.rtt < pathB.rtt else pathB

        elif sched == SCHED_WRR:
            chosen = pathA if random.random() < 0.5 else pathB

        elif sched == SCHED_REDUNDANT:
            send_chunk(pathA, pathA.stream, CHUNK)
            send_chunk(pathB, pathB.stream, CHUNK)
            for p in [pathA, pathB]:
                p.bytes_sent += len(CHUNK)
                p.last_seq = SEQ

            LOG.append({
                "seq": SEQ,
                "path": "A+B",
                "rttA": pathA.rtt,
                "rttB": pathB.rtt,
                "jitA": pathA.jitter,
                "jitB": pathB.jitter,
                "bwA": pathA.bw,
                "bwB": pathB.bw,
                "time": time.time()
            })
            SEQ += 1
            await asyncio.sleep(0)
            continue

        elif sched == SCHED_PREDICT:
            scoreA = score_path(pathA, pathB.last_seq)
            scoreB = score_path(pathB, pathA.last_seq)
            chosen = pathA if scoreA < scoreB else pathB

        # send chunk
        send_chunk(chosen, chosen.stream, CHUNK)
        chosen.bytes_sent += len(CHUNK)
        chosen.last_seq = SEQ

        LOG.append({
            "seq": SEQ,
            "path": chosen.name,
            "rttA": pathA.rtt,
            "rttB": pathB.rtt,
            "jitA": pathA.jitter,
            "jitB": pathB.jitter,
            "bwA": pathA.bw,
            "bwB": pathB.bw,
            "time": time.time()
        })

        SEQ += 1
        await asyncio.sleep(0)

    log_dir = f"runs/{sched}"
    os.makedirs(log_dir, exist_ok=True)

    out_path = f"{log_dir}/client_log.json"
    with open(out_path, "w") as f:
        json.dump(LOG, f, indent=2)

    print(f"*** Done - wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_SCHEDULERS:
        print("Usage: python3 scheduler_client.py [minrtt|wrr|redundant|predict]")
        sys.exit(1)

    scheduler = sys.argv[1]
    SEQ = 0
    LOG = []
    asyncio.run(main(scheduler))