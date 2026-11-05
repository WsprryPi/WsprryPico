#!/usr/bin/env python3
"""Plain WTP must respond while an independent TLS handshake is paused."""
import json
import pathlib
import socket
import select
import ssl
import subprocess
from fixture_process import FixtureProcess, process_scope
from network_socket import connect_socket
from network_control import NetworkControl
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder


with process_scope(timeout=8):
    expected_block = sys.argv[2:] == ["--expect-blocked"]
    assert not sys.argv[2:] or expected_block
    process = FixtureProcess([sys.argv[1], "0", "a", "--plain-with-tls"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)


    controls = NetworkControl(process)

    def line():
        return controls.line().strip()


    def control(command, **options):
        controls.send(command, **options)


    def network(deadline=None):
        control("NETWORK STATUS",deadline=deadline)
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
        with connect_socket(("127.0.0.1", 18443),deadline=process.deadline,timeout=3) as stalled:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # Only emits ClientHello; no peer is trusted.
            context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
            context.set_alpn_protocols(['http/1.1'])
            incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
            handshake = context.wrap_bio(incoming, outgoing, server_hostname='127.0.0.1')
            try:handshake.do_handshake()
            except ssl.SSLWantReadError:pass
            client_hello = outgoing.read()
            assert client_hello, 'actual TLS ClientHello required before paused-handshake assertion'
            stalled.sendall(client_hello)
            deadline = time.monotonic() + 2
            while (snapshot := network(deadline))[0] != 1 or snapshot[2] == 0:
                assert time.monotonic() < deadline, "TLS slot did not activate"
                time.sleep(.005)
            with connect_socket(("127.0.0.1", 18444),deadline=process.deadline,timeout=3) as plain:
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
                    with connect_socket(("127.0.0.1", 18444),deadline=process.deadline,timeout=3) as duplicate:
                        duplicate.settimeout(3)
                        try:
                            assert duplicate.recv(1) == b"", "duplicate WTP client was admitted"
                        except ConnectionResetError:
                            pass
                    assert network()[2] > 0, 'actual TLS bytes must remain queued after independent Plain STATUS progress'
                    assert not select.select([stalled], [], [], 0)[0], 'paused TLS emitted a server flight'
                    print("Plain HELLO/STATUS responded during paused TLS; duplicate WTP rejected")
            control("HANDSHAKE RESUME")
    finally:
        process.finish()
        stderr = process.stderr_text()
        if stderr:
            print(stderr, file=sys.stderr)
        assert process.returncode == 0, process.returncode
