#include "wtp/codec.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace wsprrypico::wtp {
namespace {
using json::quote;
using json::Value;
Value get(Value v, std::string_view key) {
    return v.get(key).value_or(Value{});
}
bool text(Value v, std::size_t min, std::size_t max) {
    return v.type() == '"' && v.string().size() >= min && v.string().size() <= max;
}
bool version(std::string_view v) {
    return v.starts_with("WTP/") && v.size() >= 5 && v[4] >= '1' && v[4] <= '9' &&
           std::all_of(v.begin() + 5, v.end(), [](char c) { return c >= '0' && c <= '9'; });
}
bool operation(std::string_view v) {
    return !v.empty() && v.size() <= 64 && v[0] >= 'A' && v[0] <= 'Z' &&
           std::all_of(v.begin() + 1, v.end(), [](char c) {
               return (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
           });
}
std::string ns(std::uint64_t n) {
    return quote(std::to_string(n));
}
std::string nullable(const std::optional<std::string>& s) {
    return s ? quote(*s) : "null";
}
std::string boolean(bool b) {
    return b ? "true" : "false";
}
std::string clock_json(const ClockSnapshot& c) {
    constexpr std::array states{"unsynchronized", "synchronized", "holdover"};
    constexpr std::array leaps{"normal", "insert_pending", "delete_pending", "unknown"};
    std::string out =
        "{\"state\":" + quote(states[static_cast<unsigned>(c.state)]) +
        ",\"utc_now_ns\":" + ns(c.utc_now_ns) + ",\"monotonic_now_ns\":" + ns(c.monotonic_now_ns) +
        ",\"uncertainty_ns\":" + ns(c.uncertainty_ns) + ",\"sync_age_ns\":" + ns(c.sync_age_ns) +
        ",\"leap\":" + quote(leaps[static_cast<unsigned>(c.leap)]);
    if (c.leap_transition_utc_ns)
        out += ",\"leap_transition_utc_ns\":" + ns(*c.leap_transition_utc_ns);
    return out + '}';
}
bool body(Request& r, Value b) {
    const auto& op = r.operation;
    if (op == "HELLO") {
        HelloBody h;
        auto versions = get(b, "versions");
        bool valid = versions.type() == '[';
        for (auto v : versions.elements(16)) {
            if (v.type() != '"' || !version(v.string()))
                valid = false;
            h.versions.push_back(v.string());
        }
        valid = valid && !h.versions.empty() && h.versions.size() <= 16;
        for (std::size_t i = 0; i < h.versions.size(); ++i)
            if (std::find(h.versions.begin(), h.versions.begin() + i, h.versions[i]) !=
                h.versions.begin() + i)
                valid = false;
        r.body = std::move(h);
        return valid && json::fields(b, {"versions", "client_name", "client_version"}) &&
               text(get(b, "client_name"), 1, 64) && text(get(b, "client_version"), 1, 64);
    }
    if (op == "CLAIM" || op == "RENEW") {
        auto owner = get(b, "owner_id"), lease = get(b, "lease_ms");
        if (!json::fields(b, {"owner_id", "lease_ms"}) || !json::identifier(owner) ||
            lease.type() < '0' || lease.type() > '9' || lease.integer() < 5000 ||
            lease.integer() > 60000)
            return false;
        if (op == "CLAIM")
            r.body = ClaimBody{owner.string(), static_cast<std::uint32_t>(lease.integer())};
        else
            r.body = RenewBody{owner.string(), static_cast<std::uint32_t>(lease.integer())};
        return true;
    }
    if (op == "ARM") {
        ArmBody a;
        if (!json::fields(b, {"job_id", "start_utc_ns", "max_start_uncertainty_ns"}) ||
            !json::identifier(get(b, "job_id")) ||
            !json::decimal(get(b, "start_utc_ns"), a.start_utc_ns) ||
            !json::decimal(get(b, "max_start_uncertainty_ns"), a.max_start_uncertainty_ns))
            return false;
        a.job_id = get(b, "job_id").string();
        r.body = std::move(a);
        return true;
    }
    if (op == "ABORT") {
        if (!json::fields(b, {"job_id"}) || !json::identifier(get(b, "job_id")))
            return false;
        r.body = AbortBody{get(b, "job_id").string()};
        return true;
    }
    if (op == "PING") {
        if (!json::fields(b, {}, {"token"}))
            return false;
        PingBody p;
        if (auto token = b.get("token")) {
            if (!text(*token, 0, 64))
                return false;
            p.token = token->string();
        }
        r.body = std::move(p);
        return true;
    }
    if (op == "LOAD") {
        Job j;
        if (!json::fields(b, {"job_id", "profile", "mode", "total_duration_ns", "events"},
                          {"allow_frequency_adjustment"}) ||
            !json::identifier(get(b, "job_id")) || get(b, "profile").type() != '"' ||
            get(b, "profile").string() != "rf-events/1" || get(b, "mode").type() != '"' ||
            !json::decimal(get(b, "total_duration_ns"), j.total_duration_ns, true) ||
            get(b, "events").type() != '[')
            return false;
        j.job_id = get(b, "job_id").string();
        j.mode = get(b, "mode").string();
        constexpr std::array modes{"wspr", "qrss", "fskcw", "dfcw", "cw", "tone"};
        if (std::find(modes.begin(), modes.end(), j.mode) == modes.end())
            return false;
        if (auto allow = b.get("allow_frequency_adjustment")) {
            if (allow->raw != "true" && allow->raw != "false")
                return false;
            j.allow_frequency_adjustment = allow->boolean();
        }
        auto events = get(b, "events").elements();
        if (events.empty() || events.size() > 512)
            return false;
        for (auto e : events) {
            RfEvent event;
            if (!json::fields(e, {"offset_ns", "duration_ns", "rf_on"}, {"frequency_nhz"}) ||
                !json::decimal(get(e, "offset_ns"), event.offset_ns) ||
                !json::decimal(get(e, "duration_ns"), event.duration_ns, true) ||
                (get(e, "rf_on").raw != "true" && get(e, "rf_on").raw != "false"))
                return false;
            event.rf_on = get(e, "rf_on").boolean();
            auto f = e.get("frequency_nhz");
            if (event.rf_on != f.has_value())
                return false;
            if (f) {
                std::uint64_t frequency;
                if (!json::decimal(*f, frequency, true))
                    return false;
                event.frequency_nhz = frequency;
            }
            j.events.push_back(event);
        }
        r.body = std::move(j);
        return true;
    }
    return (op == "CAPS" || op == "STATUS" || op == "GET_CLOCK" || op == "RELEASE") &&
           json::fields(b, {});
}
std::string caps(const ServiceConfig& c) {
    // This engine accepts numeric events for inhibited simulation only. These
    // are input limits, never a claim of physical RF frequency coverage.
    return "{\"profiles\":[\"rf-events/"
           "1\"],\"modes\":[\"wspr\",\"qrss\",\"fskcw\",\"dfcw\",\"cw\",\"tone\"],"
           "\"engine\":\"inhibited-no-rf\",\"frequency_ranges\":[{\"minimum_nhz\":\"1\",\"maximum_"
           "nhz\":\"18446744073709551615\"}],"
           "\"max_payload_bytes\":65536,\"max_events\":" +
           std::to_string(c.max_events) + ",\"max_job_duration_ns\":" + ns(c.max_job_duration_ns) +
           ",\"minimum_arm_lead_ns\":" + ns(c.minimum_arm_lead_ns) +
           ",\"maximum_arm_ahead_ns\":" + ns(c.maximum_arm_ahead_ns) +
           ",\"maximum_arm_uncertainty_ns\":" + ns(c.maximum_arm_uncertainty_ns) +
           ",\"maximum_holdover_age_ns\":" + ns(c.maximum_holdover_age_ns) +
           ",\"output_disable_timeout_ns\":" + ns(c.output_disable_timeout_ns) +
           ",\"minimum_lease_ms\":5000,\"maximum_lease_ms\":60000,\"response_cache_entries\":" +
           std::to_string(c.response_cache_entries) + ",\"response_cache_ttl_seconds\":" +
           std::to_string(c.response_cache_ttl_ns / 1'000'000'000ULL) +
           ",\"terminal_record_entries\":" + std::to_string(c.terminal_record_entries) +
           ",\"terminal_record_ttl_seconds\":" +
           std::to_string(c.terminal_record_ttl_ns / 1'000'000'000ULL) + '}';
}
} // namespace
std::optional<Request> decode_request(Value root, std::string_view principal,
                                      std::span<const std::uint8_t> payload) {
    if (!json::fields(root, {"type", "protocol", "session_id", "request_id", "op", "body"}) ||
        get(root, "type").string() != "request" || !json::identifier(get(root, "session_id")) ||
        !json::identifier(get(root, "request_id")) || get(root, "protocol").type() != '"' ||
        !version(get(root, "protocol").string()) || get(root, "op").type() != '"' ||
        !operation(get(root, "op").string()) || get(root, "body").type() != '{')
        return std::nullopt;
    Request r;
    r.protocol = get(root, "protocol").string();
    r.session_id = get(root, "session_id").string();
    r.request_id = get(root, "request_id").string();
    r.operation = get(root, "op").string();
    r.principal = principal;
    r.payload_digest = sha256(payload);
    r.body_valid = body(r, get(root, "body"));
    return r;
}
std::string state_name(State s) {
    constexpr std::array names{"empty",    "loaded",  "armed",  "running",
                               "complete", "aborted", "missed", "failed"};
    return names[static_cast<unsigned>(s)];
}
std::string error_json(ErrorCode code) {
    constexpr std::array names{"INTERNAL_ERROR",
                               "INVALID_FRAME",
                               "INVALID_MESSAGE",
                               "UNSUPPORTED_VERSION",
                               "HELLO_REQUIRED",
                               "UNKNOWN_OPERATION",
                               "AUTHENTICATION_REQUIRED",
                               "SESSION_REPLACED",
                               "BUSY",
                               "NOT_OWNER",
                               "LEASE_EXPIRED",
                               "REQUEST_ID_REUSE",
                               "INVALID_STATE",
                               "JOB_NOT_FOUND",
                               "JOB_ID_CONFLICT",
                               "JOB_LIMIT_EXCEEDED",
                               "UNSUPPORTED_PROFILE",
                               "UNSUPPORTED_MODE",
                               "FREQUENCY_REJECTED",
                               "ARM_CONFLICT",
                               "CLOCK_UNSYNCHRONIZED",
                               "CLOCK_UNCERTAIN",
                               "LEAP_UNSAFE",
                               "ARM_TOO_LATE",
                               "ARM_TOO_FAR",
                               "MISSED_START",
                               "OUTPUT_STATE_UNKNOWN",
                               "DEVICE_FAULT",
                               "INTERNAL_ERROR"};
    auto name = names[static_cast<unsigned>(code)];
    const bool retry = code == ErrorCode::Busy || code == ErrorCode::ClockUnsynchronized ||
                       code == ErrorCode::ClockUncertain;
    return "{\"code\":" + quote(name) + ",\"message\":" + quote(name) +
           ",\"retryable\":" + boolean(retry) + '}';
}
std::string status_json(const ServiceStatus& s) {
    std::string out =
        "{\"boot_id\":" + quote(s.boot_id) + ",\"state\":" + quote(state_name(s.state)) +
        ",\"output_active\":" + boolean(s.output_active) + ",\"owner_id\":" + nullable(s.owner_id) +
        ",\"job_id\":" + nullable(s.job_id) + ",\"terminal_records\":[";
    bool first = true;
    for (const auto& t : s.terminal_records) {
        if (!first)
            out += ',';
        first = false;
        out += "{\"job_id\":" + quote(t.job_id) + ",\"state\":" + quote(state_name(t.state)) +
               ",\"ended_monotonic_ns\":" + ns(t.ended_monotonic_ns) +
               ",\"output_active\":" + boolean(t.output_active);
        if (t.error != ErrorCode::None)
            out += ",\"error\":" + error_json(t.error);
        out += '}';
    }
    return out + "]}";
}
std::string encode_response(const Request& r, const Response& s, const ServiceConfig& config,
                            std::string_view device, std::string_view firmware) {
    std::string out =
        "{\"type\":\"response\",\"protocol\":\"WTP/1\",\"session_id\":" + quote(r.session_id) +
        ",\"request_id\":" + quote(r.request_id) + ",\"op\":" + quote(r.operation) +
        ",\"ok\":" + boolean(s.ok);
    if (!s.ok)
        return out + ",\"error\":" + error_json(s.error) + '}';
    std::string b = "{}";
    if (r.operation == "HELLO")
        b = "{\"selected_version\":\"WTP/1\",\"device_id\":" + quote(device) +
            ",\"boot_id\":" + quote(s.boot_id) +
            ",\"product\":\"WsprryPico\",\"firmware_version\":" + quote(firmware) + '}';
    else if (r.operation == "CAPS")
        b = caps(config);
    else if (r.operation == "STATUS" && s.status_snapshot)
        b = status_json(*s.status_snapshot);
    else if (r.operation == "GET_CLOCK" && s.clock_snapshot)
        b = clock_json(*s.clock_snapshot);
    else if (r.operation == "PING" && s.ping_token)
        b = "{\"token\":" + quote(*s.ping_token) + '}';
    else if (r.operation == "CLAIM" || r.operation == "RENEW")
        b = "{\"owner_id\":" + quote(s.owner_id) +
            ",\"granted_lease_ms\":" + std::to_string(s.granted_lease_ms) +
            ",\"expires_monotonic_ns\":" + ns(s.expires_monotonic_ns) + '}';
    else if (r.operation == "LOAD") {
        b = "{\"job_id\":" + quote(s.job_id) + ",\"state\":\"loaded\",\"adjustments\":[";
        bool first = true;
        for (const auto& a : s.adjustments) {
            if (!first)
                b += ',';
            first = false;
            b += "{\"event_index\":" + std::to_string(a.event_index) +
                 ",\"requested_frequency_nhz\":" + ns(a.requested_frequency_nhz) +
                 ",\"realized_frequency_nhz\":" + ns(a.realized_frequency_nhz) + '}';
        }
        b += "]}";
    } else if (r.operation == "ARM" && s.clock_snapshot)
        b = "{\"job_id\":" + quote(s.job_id) +
            ",\"state\":\"armed\",\"start_utc_ns\":" + ns(s.start_utc_ns) +
            ",\"start_monotonic_ns\":" + ns(s.start_monotonic_ns) +
            ",\"clock\":" + clock_json(*s.clock_snapshot) + '}';
    else if (r.operation == "ABORT")
        b = "{\"job_id\":" + quote(s.job_id) + ",\"state\":\"aborted\",\"output_active\":false}";
    return out + ",\"body\":" + b + '}';
}
} // namespace wsprrypico::wtp
