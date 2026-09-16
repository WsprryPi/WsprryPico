"""Small authenticated HTTPS evidence helper for Package 5 only."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import threading
import time

from phase11_5_inventory import require


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def exchange(root, packet, case, emit, *, name, peer_sha, device):
    context = ssl.create_default_context(cafile=str(root / "credentials/browser/client-ca.crt"))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_alpn_protocols(["http/1.1"])
    context.load_cert_chain(str(root / "credentials/browser/client.crt"),
                            str(root / "credentials/browser/client.key"))
    began = time.monotonic_ns()
    deadline = time.monotonic() + 15
    emit("http_tx", case)
    with socket.create_connection((packet["address"], packet["port"]), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=name) as stream:
            peer = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
            require(peer == peer_sha and stream.selected_alpn_protocol() == "http/1.1",
                    "Package 5 authenticated TLS peer")
            stream.settimeout(max(.001, deadline - time.monotonic()))

            def expire():
                try:
                    stream.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

            timer = threading.Timer(max(.001, deadline - time.monotonic()), expire)
            timer.daemon = True
            timer.start()
            try:
                raw_request = bytes.fromhex(case["wire_hex"])
                stream.sendall(raw_request)
                emit("http_write_complete", dict(label=case["label"], bytes=len(raw_request)))
                response = http.client.HTTPResponse(stream)
                response.begin()
                body = response.read(131073)
            finally:
                timer.cancel()
                timer.join(1)
            emit("http_response", dict(label=case["label"], status=response.status,
                 headers=response.getheaders(), body_hex=body.hex(), peer_sha256=peer,
                 began_monotonic_ns=began))
            require(time.monotonic() <= deadline and len(body) <= 131072 and
                    response.status == case["expected_status"], "Package 5 HTTP outcome/deadline")
            value = json.loads(body)
            if case["error_code"] is not None:
                require(value.get("ok") is False and value["error"]["code"] == case["error_code"],
                        "Package 5 HTTP classified error")
            else:
                require(value["ok"] is True and value["result"]["device_id"] == device and
                        value["result"]["boot_id"] == packet["boot_id"],
                        "Package 5 HTTP success identity")
            return value


def get_status(root, packet, emit, *, name, peer_sha, device):
    context = ssl.create_default_context(cafile=str(root / "credentials/browser/client-ca.crt"))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_alpn_protocols(["http/1.1"])
    context.load_cert_chain(str(root / "credentials/browser/client.crt"),
                            str(root / "credentials/browser/client.key"))
    request = (f"GET /api/v1/status HTTP/1.1\r\nHost: {name}:{packet['port']}\r\n"
               "Connection: close\r\n\r\n").encode()
    began = time.monotonic_ns()
    deadline = time.monotonic() + 15
    emit("status_tx", dict(request_hex=request.hex(), began_monotonic_ns=began))
    with socket.create_connection((packet["address"], packet["port"]), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=name) as stream:
            peer = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
            require(peer == peer_sha and stream.selected_alpn_protocol() == "http/1.1",
                    "Package 5 authenticated status peer")
            stream.settimeout(max(.001, deadline - time.monotonic()))
            stream.sendall(request)
            response = http.client.HTTPResponse(stream)
            response.begin()
            body = response.read(131073)
    emit("status_response", dict(status=response.status, headers=response.getheaders(),
         body_hex=body.hex(), peer_sha256=peer, began_monotonic_ns=began))
    require(time.monotonic() <= deadline and response.status == 200 and len(body) <= 131072,
            "Package 5 authenticated status outcome/deadline")
    value = json.loads(body)
    require(value["job"]["boot_id"] == packet["boot_id"],
            "Package 5 authenticated status boot identity")
    return value
