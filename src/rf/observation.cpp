// SPDX-License-Identifier: MIT
#include "rf/observation.hpp"
#include "runtime/json.hpp"
#include <array>
namespace wsprrypico::execution {
namespace {
using json::quote;
std::string ns(std::uint64_t n) {return quote(std::to_string(n));}
std::string nullable(const std::optional<std::string>& s) {return s ? quote(*s) : "null";}
std::string boolean(bool b) {return b ? "true" : "false";}
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
}
