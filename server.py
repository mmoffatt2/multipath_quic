import asyncio, time, json, os
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio import serve

log = []
current_sched = "unknown"

async def handle_stream(reader, writer):
    global log, current_sched

    # Read possible scheduler header
    first = await reader.read(200)
    if first.startswith(b"SCHED:"):
        current_sched = first.decode().split(":",1)[1].strip()
        print(f"*** Detected scheduler: {current_sched}")
    else:
        log.append({"timestamp": time.time(), "size": len(first)})

    while True:
        data = await reader.read(1200)
        if not data:
            break

        log.append({
            "timestamp": time.time(),
            "size": len(data)
        })

        writer.write(b"ack")
        await writer.drain()

async def main():
    conf = QuicConfiguration(is_client=False)
    conf.load_cert_chain("cert.pem", "key.pem")

    print("*** QUIC server running on port 4443")
    server = await serve(
        host="0.0.0.0",
        port=4443,
        configuration=conf,
        stream_handler=handle_stream
    )

    # ✅ Keep server running until Ctrl+C
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass

    # ✅ Save logs on shutdown
    sched = current_sched if current_sched else "unknown"
    log_dir = f"runs/{sched}"
    os.makedirs(log_dir, exist_ok=True)

    with open(f"{log_dir}/server_log.json", "w") as f:
        json.dump(log, f, indent=2)

    print(f"✅ Saved server logs to runs/{sched}/server_log.json")

if __name__ == "__main__":
    asyncio.run(main())
