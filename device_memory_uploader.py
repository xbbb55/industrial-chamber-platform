import argparse
import json
import time
import urllib.error
import urllib.request

from backend.shared_memory_store import SharedMemoryNotReady, attach_existing, read_snapshot


def read_local_snapshot() -> dict:
    shm = attach_existing()
    try:
        return read_snapshot(shm)
    finally:
        shm.close()


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local shared-memory chamber data to central FastAPI.")
    parser.add_argument("--edge-id", default="EDGE-CHAMBER-001")
    parser.add_argument("--server", default="http://127.0.0.1:8010")
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--agent-version", default="0.1.0")
    args = parser.parse_args()

    endpoint = args.server.rstrip("/") + "/api/device-ingest/snapshots"
    print(f"device uploader started: edge_id={args.edge_id}, endpoint={endpoint}")
    print("press Ctrl+C to stop")

    while True:
        try:
            snapshot = read_local_snapshot()
            result = post_json(endpoint, {
                "edge_id": args.edge_id,
                "agent_version": args.agent_version,
                "uploaded_at": time.time(),
                "snapshot": snapshot,
            })
            print(
                f"uploaded sequence={result.get('sequence')} "
                f"devices={result.get('device_count')} "
                f"received_at={result.get('received_at')}"
            )
        except SharedMemoryNotReady as exc:
            print(f"shared memory not ready: {exc}")
        except urllib.error.URLError as exc:
            print(f"upload failed: {exc}")
        except KeyboardInterrupt:
            print("uploader stopped")
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

