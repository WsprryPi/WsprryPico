"""Frozen Package 5 replay/session/terminal and reclamation policy."""
import hashlib
import json

from phase11_5_inventory import require


POLICY = "phase115-package5-retained-v1"
RETAINED_SOURCE = "ca3c5dce40360b7eea2f9c45618232caa68cdbb6"
RETAINED_IMAGE = "6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59"
RETAINED_BOOT = "5e0d6bc3e383b8c1cb4b0db9ed636bf5"
SOURCE = "2b25ca05c270819466a04498f9bc4894a4c5bace"
IMAGE = "16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51"
BOOT = "80d558e5804547749eca849c53ba27e1"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
NAME = "wsprrypico-0a60df.local"
PEER = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"


def ident(seed, label):
    return hashlib.sha256((seed + ":" + label).encode()).hexdigest()[:32]


def request_case(label, session, request, operation, body, *, status=200, error=None,
                 phase="saturate"):
    value = dict(session_id=session, request_id=request, operation=operation, body=body)
    raw = json.dumps(value, separators=(",", ":")).encode()
    header = (f"POST /api/v1/jobs HTTP/1.1\r\nHost: {NAME}:18443\r\n"
              f"Origin: https://{NAME}:18443\r\nX-WsprryPico-Request: 1\r\n"
              f"Content-Type: application/json\r\nContent-Length: {len(raw)}\r\n"
              "Connection: close\r\n\r\n").encode()
    return dict(label=label, phase=phase, request=value, wire_hex=(header + raw).hex(),
                expected_status=status, error_code=error)


def hello(label, session, request, version="1", **kwargs):
    return request_case(label, session, request, "HELLO",
                        dict(versions=["WTP/1"], client_name="Package5-retained",
                             client_version=version), **kwargs)


def retention_cases(seed, owner_id):
    sessions = [ident(seed, f"session-{n}") for n in range(17)]
    hellos = [ident(seed, f"hello-{n}") for n in range(17)]
    result = [hello(f"session-{n}", sessions[n], hellos[n]) for n in range(16)]
    result.append(hello("session-16-overflow", sessions[16], hellos[16], status=409,
                        error="BUSY"))
    result.append(hello("session-15-reuse", sessions[15], ident(seed, "reuse-15")))
    replay = [hellos[0]] + [ident(seed, f"replay-{n}") for n in range(1, 9)]
    result.extend(hello(f"replay-fill-{n}", sessions[0], replay[n]) for n in range(1, 8))
    result.append(hello("replay-exact", sessions[0], replay[0]))
    result.append(hello("replay-conflict", sessions[0], replay[0], "2", status=409,
                        error="REQUEST_ID_REUSE"))
    result.append(hello("replay-ninth", sessions[0], replay[8]))
    result.append(hello("replay-evicted", sessions[0], replay[1], "2"))
    result.append(hello("replay-touched", sessions[0], replay[0], "2", status=409,
                        error="REQUEST_ID_REUSE"))
    renew = dict(owner_id=owner_id, lease_ms=60000)
    result.append(request_case("session-0-expired", sessions[0], ident(seed, "expired-0"),
                               "RENEW", renew, status=409, error="HELLO_REQUIRED",
                               phase="expired"))
    result.append(request_case("session-15-expired", sessions[15], ident(seed, "expired-15"),
                               "RENEW", renew, status=409, error="HELLO_REQUIRED",
                               phase="expired"))
    result.append(hello("replay-expired", sessions[0], replay[0], "2", phase="expired"))
    result.append(hello("overflow-now-admitted", sessions[16], hellos[16], phase="expired"))
    result.append(request_case("final-status", sessions[16], ident(seed, "final-status"),
                               "STATUS", {}, phase="expired"))
    return result


def validate_retention(packet):
    require(packet["policy"] == POLICY and packet["source_revision"] == RETAINED_SOURCE and
            packet["image_sha256"] == RETAINED_IMAGE and packet["boot_id"] == RETAINED_BOOT and
            packet["device_id"] == DEVICE, "Package 5 retained identity")
    plan = packet["retention"]
    require(plan == dict(seed=plan["seed"], owner_id=plan["owner_id"],
                         cases=retention_cases(plan["seed"], plan["owner_id"]),
                         replay_entries_per_session=8, maximum_sessions=16,
                         replay_session_ttl_seconds=300, initial_quiet_seconds=360,
                         expiry_quiet_seconds=360), "Frozen replay/session plan")
    require(len(plan["seed"]) == len(plan["owner_id"]) == 32 and
            all(c in "0123456789abcdef" for c in plan["seed"] + plan["owner_id"]),
            "Package 5 retained identifiers")
    require(packet["runtime_seconds"] == 1500 and packet["restoration_seconds"] == 150 and
            packet["configuration_writes"] == packet["controlled_reboots"] ==
            packet["wifi_cycles"] == packet["flashes"] == packet["rf_jobs"] == 0,
            "Package 5 retained bounds")
    return packet


def terminal_jobs(seed):
    result = []
    for n in range(9):
        result.append(dict(job_id=ident(seed, f"terminal-{n}"), profile="rf-events/1",
                           mode="tone", total_duration_ns="1000000000",
                           allow_frequency_adjustment=True,
                           events=[dict(offset_ns="0", duration_ns="1000000000", rf_on=True,
                                        frequency_nhz="135500000000000")]))
    return result


def validate_terminal(packet):
    require(packet["closure_policy"] == "phase115-package5-terminal-capacity-v1" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT, "Package 5 terminal identity")
    require(packet["jobs"] == terminal_jobs(packet["terminal_seed"]) and
            packet["runtime_seconds"] == 720 and packet["restoration_seconds"] == 150 and
            packet["maximum_renewals"] == 2 and packet["terminal_capacity"] ==
            dict(entries=8, touch_after_completions=8, evicted_job_index=1,
                 retained_job_indexes=[8, 0, 7, 6, 5, 4, 3, 2]),
            "Frozen Package 5 terminal workload")
    require(packet["maximum_initial_terminal_records"] <= 8 and
            packet["initial_a_state"] == "empty" and packet["initial_a_job_id"] is None,
            "Package 5 terminal initial state")
    return packet


def expiry_cases(seed):
    after_session = ident(seed, "after-session")
    return [
        hello("after-hello", after_session, ident(seed, "after-hello"), phase="after"),
    ]


def validate_expiry(packet):
    require(packet["policy"] == "phase115-package5-terminal-expiry-v1" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["device_id"] == DEVICE,
            "Package 5 expiry identity")
    plan = packet["terminal_expiry"]
    require(plan == dict(seed=plan["seed"], cases=expiry_cases(plan["seed"]),
                         terminal_entries=8, source_ttl_seconds=3600,
                         quiet_seconds=3660, authenticated_recovery_seconds=15,
                         initial_terminal_records=plan["initial_terminal_records"]),
            "Frozen Package 5 expiry plan")
    require(len(plan["initial_terminal_records"]) == 8 and
            all(record["state"] == "complete" and record["output_active"] is False
                for record in plan["initial_terminal_records"]),
            "Package 5 expiry initial terminals")
    require(packet["runtime_seconds"] == 3900 and packet["restoration_seconds"] == 150 and
            packet["configuration_writes"] == packet["controlled_reboots"] ==
            packet["wifi_cycles"] == packet["flashes"] == packet["rf_jobs"] == 0,
            "Package 5 expiry bounds")
    return packet
