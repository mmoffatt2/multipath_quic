#!/usr/bin/env python3
import asyncio
import json
import os
import time

from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.events import (
    QuicEvent,
    StreamDataReceived,
    ProtocolNegotiated,
    HandshakeCompleted,
)

LOG = []
CURRENT_SCHED = "unknown"


class MPQuicProtocol(QuicConnectionProtocol):
    """
    Server-side QUIC protocol:
    - Logs RTT-related fields after handshake
    - Detects scheduler header (SCHED:xxx)
    - Logs incoming data sizes
    - Echoes data back to client (so client receives ACKS)
    """

    def __init__(self, *args, **kwargs):
        self._printed_loss_attrs = False
        super().__init__(*args, **kwargs)

    def quic_event_received(self, event: QuicEvent) -> None:
        global CURRENT_SCHED, LOG

        print("GOT EVENT:", event)
        super().quic_event_received(event)

        # ---- RTT diagnostics after handshake ----
        if isinstance(event, HandshakeCompleted) and not self._printed_loss_attrs:
            self._printed_loss_attrs = True
            loss = self._quic._loss

            print("LOSS ATTRS WITH 'rtt' IN NAME:")
            for name in dir(loss):
                if "rtt" in name.lower():
                    print("   ", name, "=", getattr(loss, name))

        # ---- Handle incoming stream data ----
        if isinstance(event, StreamDataReceived):
            data = event.data
            sid = event.stream_id

            # Detect scheduler header
            if data.startswith(b"SCHED:"):
                print("*** Raw scheduler header:", data[:150], "...")
                try:
                    CURRENT_SCHED = data.decode(errors="ignore").split(":", 1)[1].strip()
                except Exception:
                    CURRENT_SCHED = "unknown"
                print(f"*** Scheduler detected: {CURRENT_SCHED}")

            else:
                # Log payload size
                LOG.append({
                    "timestamp": time.time(),
                    "stream_id": sid,
                    "size": len(data),
                })

            # IMPORTANT: echo data back (client uses ACKs for RTT)
            self._quic.send_stream_data(sid, b"ACK", end_stream=False)
            self.transmit()


async def main():
    conf = QuicConfiguration(
        is_client=False,
        alpn_protocols=["hq-29"],
    )

    conf.load_cert_chain("cert.pem", "key.pem")

    print("*** Starting QUIC server on 0.0.0.0:4443")

    # 🔥 Correct: use our custom protocol
    await serve(
        host="0.0.0.0",
        port=4443,
        configuration=conf,
        create_protocol=MPQuicProtocol,
    )

    # Keep running until Ctrl+C
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass

    # ---- Save logs ----
    sched = CURRENT_SCHED or "unknown"
    log_dir = os.path.join("runs", sched)
    os.makedirs(log_dir, exist_ok=True)

    out_path = os.path.join(log_dir, "server_log.json")
    with open(out_path, "w") as f:
        json.dump(LOG, f, indent=2)

    print(f"*** Server stopped, wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
