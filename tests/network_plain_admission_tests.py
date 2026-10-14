#!/usr/bin/env python3
"""Plain WTP must respond while an independent TLS handshake is paused."""
import json
import pathlib
import select
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder

expected_block = sys.argv[2:] == ["--expect-blocked"]
assert not sys.argv[2:] or expected_block
process = subprocess.Popen([sys.argv[1], "0", "a", "--plain-with-tls"],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)


def line():
    assert select.select([process.stdout], [], [], 3)[0], "driver response deadline"
    return process.stdout.readline().strip()


def control(command):
    process.stdin.write(command + "\n")
    process.stdin.flush()


def network():
    control("NETWORK STATUS")
    value = line().split()
    assert value[0] == "NETWORK", value
    return tuple(map(int, value[1:]))


def request(stream, decoder, sequence, operation, body):
    identifier = f"{sequence:032x}"
    stream.sendall(frame(json.dumps({"type": "request", "protocol": "WTP/1",
                                    "session_id": "1" * 32, "request_id": identifier,
                                    "op": operation, "body": body},
                                   separators=(",", ":")).encode()))
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        stream.settimeout(deadline - time.monotonic())
        data = stream.recv(4096)
        assert data, "Plain WTP closed without a response"
        for payload in decoder.feed(data):
            reply = json.loads(payload)
            if reply.get("request_id") == identifier:
                assert reply.get("ok") is True, reply
                return reply
    raise TimeoutError("five-second WTP response deadline")


try:
    assert line() == "READY 18443 PSA 1 PEAK 2 PLAIN 18444"
    control("HANDSHAKE PAUSE")
    assert network() == (0, 0, 0)
    with socket.create_connection(("127.0.0.1", 18443), timeout=3) as stalled:
        deadline = time.monotonic() + 2
        while network()[0] != 1:
            assert time.monotonic() < deadline, "TLS slot did not activate"
            time.sleep(.005)
        with socket.create_connection(("127.0.0.1", 18444), timeout=3) as plain:
            decoder = FrameDecoder()
            try:
                hello = request(plain, decoder, 1, "HELLO",
                                {"versions": ["WTP/1"], "client_name": "admission test",
                                 "client_version": "1"})
            except TimeoutError:
                assert expected_block, "unfinished TLS blocked independent Plain WTP"
                assert network()[1] == 1, "old control did not retain the pending Plain slot"
                print("OLD CONTROL: Plain HELLO blocked behind paused TLS handshake")
            else:
                assert not expected_block, "old control unexpectedly admitted Plain WTP"
                assert hello["body"]["device_id"] == "a" * 32
                status = request(plain, decoder, 2, "STATUS", {})
                assert status["body"]["state"] == "empty"
                assert network()[:2] == (2, 0)
                with socket.create_connection(("127.0.0.1", 18444), timeout=3) as duplicate:
                    duplicate.settimeout(3)
                    try:
                        assert duplicate.recv(1) == b"", "duplicate WTP client was admitted"
                    except ConnectionResetError:
                        pass
                stalled.settimeout(.05)
                try:
                    assert not stalled.recv(1), "paused TLS advanced application traffic"
                except TimeoutError:
                    pass
                print("Plain HELLO/STATUS responded during paused TLS; duplicate WTP rejected")
        control("HANDSHAKE RESUME")
finally:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    stderr = process.stderr.read()
    if stderr:
        print(stderr, file=sys.stderr)
    assert process.returncode == 0, process.returncode
