#pragma once
#include <charconv>
#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::network {
inline std::optional<std::string> canonical_local_hostname(std::string_view input) {
    if (input.ends_with('.'))
        input.remove_suffix(1);
    if (input.size() < 7 || input.size() > 69)
        return {};
    std::string name(input);
    for (auto& c : name) {
        if (c >= 'A' && c <= 'Z')
            c += 'a' - 'A';
    }
    if (!name.ends_with(".local"))
        return {};
    const auto label = std::string_view(name).substr(0, name.size() - 6);
    if (label.empty() || label.size() > 63 || label.front() == '-' || label.back() == '-')
        return {};
    for (const auto c : label)
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-'))
            return {};
    return name;
}
inline std::string default_hostname(std::string_view device) {
    if (device.size() != 32)
        return {};
    for (auto c : device)
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            return {};
    return "wsprrypico-" + std::string(device) + ".local";
}
inline bool deployment_identity_matches(std::string_view actual, std::string_view configured,
                                        std::string_view hostname) {
    if (configured.empty() && hostname.empty())
        return true; // Legacy IP-only or disabled network build.
    return !default_hostname(actual).empty() && actual == configured &&
           canonical_local_hostname(hostname).has_value();
}
inline bool canonical_ipv4(std::string_view address) {
    for (unsigned i = 0; i < 4; ++i) {
        const auto dot = address.find('.');
        const auto part = address.substr(0, dot);
        if (part.empty() || part.size() > 3 || (part.size() > 1 && part.front() == '0'))
            return false;
        unsigned octet = 0;
        auto result = std::from_chars(part.data(), part.data() + part.size(), octet);
        if (result.ec != std::errc{} || result.ptr != part.data() + part.size() || octet > 255)
            return false;
        if (i == 3)
            return dot == address.npos;
        if (dot == address.npos)
            return false;
        address.remove_prefix(dot + 1);
    }
    return false;
}
// Application authorities are IPv4 or one deployment .local name, never URLs.
inline std::optional<std::string> canonical_authority(std::string_view input) {
    if (input.empty() || input.size() > 76)
        return {};
    const auto colon = input.find(':');
    auto host = input.substr(0, colon);
    std::string port;
    if (colon != input.npos) {
        const auto value = input.substr(colon + 1);
        unsigned number = 0;
        const auto parsed = std::from_chars(value.data(), value.data() + value.size(), number);
        if (value.empty() || value.front() == '0' || parsed.ec != std::errc{} ||
            parsed.ptr != value.data() + value.size() || number == 0 || number > 65535 ||
            number == 443)
            return {};
        port = ":" + std::string(value);
    }
    if (canonical_ipv4(host))
        return std::string(host) + port;
    auto name = canonical_local_hostname(host);
    if (!name)
        return {};
    return *name + port;
}
} // namespace wsprrypico::network
