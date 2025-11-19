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
from aioquic.quic.events import QuicEvent  # for type hinting in protocol


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

BASE_WEIGHT = 100_000

class PathState:
    def __init__(self, name, conn, stream_id):
        self.name = name
        self.conn = conn          # QuicConnectionProtocol
        self.stream = stream_id

        # RTT / jitter history
        self.rtts = []

        # sequence number of last chunk sent on this path
        self.last_seq = -1

        # sending stats
        self.bytes_sent = 0
        self.first_send_time = None
        self.last_send_time = None

        # Used for WRR scheduler
        self.weight = 1
        self.current_weight = 0

    @property
    def rtt(self):
        """Smoothed RTT: mean of logged samples, default 30ms if none yet."""
        return sum(self.rtts) / len(self.rtts) if self.rtts else 0.03

    @property
    def jitter(self):
        """Mean absolute difference between consecutive RTTs."""
        if len(self.rtts) < 2:
            return 0.0
        diffs = [abs(self.rtts[i] - self.rtts[i - 1]) for i in range(1, len(self.rtts))]
        return sum(diffs) / len(diffs)

    @property
    def bw(self):
        """
        Approximate bandwidth as bytes_sent / elapsed_time on this path.

        This is not perfect BBR-style delivery-rate (which would need per-ACK
        byte counts), but it is a *real* time-based send rate for the path.
        """
        if self.first_send_time is None:
            return 1.0  # avoid division by zero before any sends

        end_time = self.last_send_time or time.time()
        dt = end_time - self.first_send_time
        if dt <= 0:
            return float(self.bytes_sent) if self.bytes_sent > 0 else 1.0

        return max(1.0, self.bytes_sent / dt)  # bytes / second

    def log_rtt(self, r: float):
        """Record a new RTT sample (seconds)."""
        self.rtts.append(r)


def score_path(path, other_last_seq):
    """
    Predictive cost function for SCHED_PREDICT.

    Lower = better. Combines:
      - RTT
      - jitter
      - inverse bandwidth
      - reordering penalty
    """
    pred = path.rtt + alpha * path.jitter + beta * (1 / path.bw)
    reorder_pen = gamma * max(0, path.last_seq - other_last_seq)
    return pred + reorder_pen


class MPQuicProtocol(QuicConnectionProtocol):
    """
    Custom protocol that exposes per-path RTT back to PathState.

    We don't get explicit ACK events from aioquic at the app layer, but every
    time an event is delivered, the loss-recovery module has up-to-date RTT.
    We read _loss._latest_rtt and push it into the associated PathState.
    """

    def __init__(self, *args, **kwargs):
        # We'll attach path_state *after* construction
        self.path_state = None
        super().__init__(*args, **kwargs)

    def quic_event_received(self, event: QuicEvent) -> None:
        print("GOT EVENT:", event)

        # Continue normal aioquic processing
        super().quic_event_received(event)

        # Read RTT estimate directly from loss-recovery
        if self.path_state is not None:
            loss = self._quic._loss
            latest_rtt = getattr(loss, "_rtt_latest", None)
            print("LATEST_RTT:", latest_rtt)
            if latest_rtt is not None:
                self.path_state.log_rtt(latest_rtt)


async def quic_connect(local_ip, server_ip, port=4443):
    import ssl  # must import ssl here or at top of file

    # 1. QUIC client configuration
    conf = QuicConfiguration(
        is_client=True,
        alpn_protocols=["hq-29"],
    )

    # Disable certificate verification (self-signed cert)
    conf.verify_mode = ssl.CERT_NONE

    # 2. Bind UDP to specific interface / IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, 0))

    # 3. Create low-level QUIC connection
    quic = QuicConnection(configuration=conf)

    # 4. Wrap inside our custom protocol
    protocol = MPQuicProtocol(quic)

    # 5. Register with asyncio event loop
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(lambda: protocol, sock=sock)

    # 6. Connect + kick off handshake
    quic.connect((server_ip, port), now=time.time())
    protocol.transmit()

    return protocol


def open_stream_id(quic):
    try:
        return quic.get_next_available_stream_id(is_unidirectional=False)
    except TypeError:
        # older aioquic versions have a different signature
        return quic.get_next_available_stream_id()


def send_chunk(pstate: PathState, stream_id: int, chunk: bytes):
    """
    Send a single chunk on the given path / stream.
    Updates timing needed for bandwidth estimation.
    """
    now = time.time()
    if pstate.first_send_time is None:
        pstate.first_send_time = now
    pstate.last_send_time = now

    pstate.conn._quic.send_stream_data(stream_id, chunk, end_stream=False)
    pstate.conn.transmit()
    print(f"SENDING {len(chunk)} bytes on path", pstate.name)


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

    # Attach path states to protocols so RTT logging works
    connA.path_state = pathA
    connB.path_state = pathB

    print("connA type =", type(connA))
    print("protocol internal =", connA._quic)

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
        # NOTE: RTT is now populated by MPQuicProtocol.quic_event_received

        # Choose scheduler
        if sched == SCHED_MIN_RTT:
            chosen = pathA if pathA.rtt < pathB.rtt else pathB

        elif sched == SCHED_WRR:
            # Update weights based on estimated bandwidth
            pathA.weight = max(1, int(pathA.bw / BASE_WEIGHT))
            pathB.weight = max(1, int(pathB.bw / BASE_WEIGHT))

            total_weight = pathA.weight + pathB.weight

            # Smooth weighted round robin
            # we add the weight to the running “priority” counter for that path
            # Fast path accumulates priority quickly (bigger weight)
            # Slow path accumulates priority slowly (smaller weight)
            pathA.current_weight += pathA.weight
            pathB.current_weight += pathB.weight

            # choose heavier
            chosen = pathA if pathA.current_weight >= pathB.current_weight else pathB

            # decrease chosen path’s current weight by total
            # resets the chosen path’s priority downward
            chosen.current_weight -= total_weight

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

        else:
            # fallback just in case
            print("*** Unknown scheduler, defaulting to path A ***")
            chosen = pathA

        # send chunk on chosen path
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
