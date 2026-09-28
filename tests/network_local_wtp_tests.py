#!/usr/bin/env python3
"""Real TLS/ALPN coverage for the consumer LAN WTP admission mode."""
import json
import pathlib
import socket
import ssl
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder

exe, credentials = sys.argv[1:]
credentials = pathlib.Path(credentials)
process = subprocess.Popen([exe, "0", "a", "--local-wtp"], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def connect(protocol):
    context = ssl.create_default_context(cafile=str(credentials / "client-ca.crt"))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    if protocol:
        context.set_alpn_protocols([protocol])
    raw = socket.create_connection(("127.0.0.1", 18443), timeout=5)
    return context.wrap_socket(raw, server_hostname="127.0.0.1")


try:
    assert process.stdout.readline().strip() == "READY 18443 PSA 1 PEAK 2"
    with connect("wtp/1") as stream:
        assert stream.version() == "TLSv1.3"
        assert stream.selected_alpn_protocol() == "wtp/1"
        decoder = FrameDecoder()
        for sequence, operation, body in (
            (1, "HELLO", {"versions": ["WTP/1"], "client_name": "LAN test", "client_version": "1"}),
            (2, "STATUS", {}),
        ):
            request_id = f"{sequence:032x}"
            request = json.dumps({"type": "request", "protocol": "WTP/1",
                                  "session_id": "1" * 32, "request_id": request_id,
                                  "op": operation, "body": body}, separators=(",", ":")).encode()
            stream.sendall(frame(request))
            while True:
                chunk = stream.recv(4096)
                assert chunk, f"{operation}: connection closed without a WTP response"
                replies = [json.loads(payload) for payload in decoder.feed(chunk)]
                if any(reply.get("request_id") == request_id and reply.get("ok") for reply in replies):
                    break
    for protocol in ("http/1.1", None):
        with connect(protocol) as stream:
            stream.sendall(b"GET /api/v1/status HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            assert not stream.recv(4096), "LAN WTP mode exposed the browser API"
    print("LAN WTP accepted a TLS 1.3 client without a client certificate; HTTP was rejected")
finally:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    stderr = process.stderr.read()
    if stderr:
        print(stderr, file=sys.stderr)
