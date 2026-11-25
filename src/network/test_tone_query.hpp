// SPDX-License-Identifier: MIT
#pragma once
#include "network/identity.hpp"
namespace wsprrypico::network {
struct TestToneQuery {
    std::string_view device, boot, selector;
    bool by_job = false;
};
inline std::optional<TestToneQuery> test_tone_query(std::string_view path) {
    constexpr std::string_view prefix = "/api/control/v1/test-tone/status?";
    if (!path.starts_with(prefix) || path.size() > 256)
        return {};
    path.remove_prefix(prefix.size());
    TestToneQuery result;
    unsigned seen = 0;
    while (!path.empty()) {
        const auto end = path.find('&');
        const auto part = path.substr(0, end);
        const auto equals = part.find('=');
        if (equals == part.npos)
            return {};
        const auto key = part.substr(0, equals), value = part.substr(equals + 1);
        if (!valid_device_id(value))
            return {};
        unsigned bit = 0;
        if (key == "device_id") {
            bit = 1;
            result.device = value;
        } else if (key == "boot_id") {
            bit = 2;
            result.boot = value;
        } else if (key == "request_id" || key == "job_id") {
            bit = 4;
            result.selector = value;
            result.by_job = key == "job_id";
        } else
            return {};
        if (seen & bit)
            return {};
        seen |= bit;
        if (end == path.npos)
            break;
        path.remove_prefix(end + 1);
        if (path.empty())
            return {};
    }
    return seen == 7 ? std::optional<TestToneQuery>(result) : std::nullopt;
}
inline bool test_tone_status_path(std::string_view method, std::string_view path) {
    return method == "GET" && test_tone_query(path).has_value();
}
} // namespace wsprrypico::network
