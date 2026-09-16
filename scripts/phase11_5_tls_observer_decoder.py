#!/usr/bin/env python3
"""Strict decoder for durable Phase 11.5 native TLS observer records."""

import struct


def require(value, message):
    if not value:
        raise ValueError(message)


def decode(data):
    rows = []
    active = {}
    writes = {}
    next_id = 1
    last = 0
    version = None
    while data:
        require(len(data) >= 64, "Truncated record header")
        magic, sequence, kind, identity, mono, utc, pid, length = struct.unpack(">8s7Q", data[:64])
        if version is None:
            version = magic
        require(magic == version and magic in (b"P115TLS1", b"P115TLS2") and
                sequence == len(rows) and mono >= last and pid > 0 and utc > 0 and
                length <= (65536 if magic == b"P115TLS1" else 65552) and
                len(data) >= 64 + length, "Record identity, sequence, time or size")
        payload = data[64:64 + length]
        data = data[64 + length:]
        last = mono
        if not rows:
            require(kind == identity == length == 0, "Missing observer start")
        elif kind == 1:
            require(identity == next_id and length == 0, "Connection identity reused")
            active[identity] = False
            next_id += 1
        elif kind == 2:
            require(identity in active and length == 32, "Certificate record")
            active[identity] = True
        elif kind == 7:
            require(magic == b"P115TLS2" and active.get(identity) is True and length > 0 and
                    identity not in writes, "Invalid write entry")
            writes[identity] = payload
        elif kind == 8:
            require(magic == b"P115TLS2" and identity in writes and length == 0,
                    "Invalid failed write")
            del writes[identity]
        elif kind in (3, 4):
            require(active.get(identity) is True and length > 0, "Unauthenticated or empty I/O record")
            if kind == 3 and magic == b"P115TLS2":
                require(identity in writes and writes.pop(identity).startswith(payload),
                        "Write entry/result mismatch")
        elif kind == 5:
            require(identity in active and identity not in writes and length == 0,
                    "Unknown connection close or unfinished write")
            del active[identity]
        elif kind == 6:
            require(identity == length == 0 and not data and not active, "Incomplete observer finish")
        else:
            raise ValueError("Unexpected observer record")
        rows.append({"sequence": sequence, "kind": kind, "connection_id": identity,
            "monotonic_ns": mono, "utc_ns": utc, "pid": pid, "payload": payload,
            "version": magic.decode()})
    require(rows and rows[-1]["kind"] == 6, "Missing final record")
    require(len({row["pid"] for row in rows}) == 1, "Mixed process identity")
    return rows
