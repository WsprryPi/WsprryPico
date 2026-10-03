#!/usr/bin/env python3
"""Real TCP framing and admission checks for explicitly plain LAN WTP."""
import json
import os
import pathlib
import socket
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder


def rejected(stream, explanation):
    try:
        assert stream.recv(1) == b"", explanation
    except ConnectionResetError:
        pass  # lwIP may abort a rejected peer instead of sending FIN.

process = subprocess.Popen([sys.argv[1], "0", "a", "--plain-wtp"],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)


def request(stream, decoder, sequence, operation, body):
    request_id = f"{sequence:032x}"
    stream.sendall(frame(json.dumps({"type": "request", "protocol": "WTP/1",
                                    "session_id": "1" * 32, "request_id": request_id,
                                    "op": operation, "body": body},
                                   separators=(",", ":")).encode()))
    for _ in range(16):
        chunk = stream.recv(4096)
        assert chunk, f"{operation}: plain stream closed without response"
        for payload in decoder.feed(chunk):
            reply = json.loads(payload)
            if reply.get("request_id") == request_id:
                assert reply.get("ok") is True, reply
                return reply
    raise AssertionError(f"{operation}: response missing")


try:
    assert process.stdout.readline().strip() == "READY 18443 PSA 1 PEAK 2 PLAIN 18444"
    with socket.create_connection(("127.0.0.1", 18444), timeout=5) as stream:
        stream.settimeout(5)
        decoder = FrameDecoder()
        hello = request(stream, decoder, 1, "HELLO",
                        {"versions": ["WTP/1"], "client_name": "plain LAN test",
                         "client_version": "1"})
        assert hello["body"]["device_id"] == "a" * 32
        status = request(stream, decoder, 2, "STATUS", {})
        assert status["body"]["state"] == "empty"
        with socket.create_connection(("127.0.0.1", 18444), timeout=5) as second:
            second.settimeout(5)
            rejected(second, "second WTP owner was not rejected")
    with socket.create_connection(("127.0.0.1", 18444), timeout=5) as stream:
        # Production expires partial frames after 5,000 ms. Leave one second
        # for host receipt of its close; the target deadline is unchanged.
        stream.settimeout(6)
        stream.sendall(b"GET /api/v1/status HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
        rejected(stream, "plain WTP port exposed HTTP")
    with socket.create_connection(("127.0.0.1", 18443), timeout=5) as stream:
        stream.settimeout(5)
        rejected(stream, "SoftAP-only TLS admitted a station client")
    print("plain TCP WTP accepted HELLO/STATUS and rejected duplicate WTP and HTTP")
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

ap_process = subprocess.Popen([sys.argv[1], "0", "a", "--plain-wtp"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              env={**os.environ, "WSPRRY_TEST_SOFTAP_INTERFACE": "1"})
try:
    assert ap_process.stdout.readline().strip() == "READY 18443 PSA 1 PEAK 2 PLAIN 18444"
    with socket.create_connection(("127.0.0.1", 18444), timeout=5) as stream:
        stream.settimeout(5)
        rejected(stream, "plain WTP accepted an AP-classified client")
finally:
    ap_process.terminate()
    try:
        ap_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        ap_process.kill()
        ap_process.wait()
