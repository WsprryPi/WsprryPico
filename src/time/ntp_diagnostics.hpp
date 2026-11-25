#pragma once

#include "time/ntp_filter.hpp"
#include "runtime/json.hpp"
#include "runtime/sha256.hpp"

#include <charconv>
#include <string_view>

namespace wsprrypico::time {
struct NtpDiagnosticBinding {
    std::string_view device, boot, firmware, revision, endpoint;
    unsigned slot = 0;
    std::uint64_t epoch = 0;
};
} // namespace wsprrypico::time
