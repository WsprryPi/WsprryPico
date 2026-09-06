#include "standalone/config.hpp"

#include "encoding/wspr.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <charconv>
#include <numeric>

namespace wsprrypico::standalone {
namespace {
bool printable(std::string_view text, std::size_t minimum, std::size_t maximum) {
    return text.size() >= minimum && text.size() <= maximum &&
           std::all_of(text.begin(), text.end(),
                       [](unsigned char c) { return c >= 32 && c < 127; });
}
bool ipv4(std::string_view text) {
    unsigned first = 0;
    for (unsigned i = 0; i < 4; ++i) {
        const auto dot = text.find('.');
        const auto part = text.substr(0, dot);
        unsigned n = 0;
        auto result = std::from_chars(part.data(), part.data() + part.size(), n);
        if (part.empty() || part.size() > 3 || (part.size() > 1 && part[0] == '0') ||
            result.ec != std::errc{} || result.ptr != part.data() + part.size() || n > 255 ||
            ((i < 3) != (dot != text.npos)))
            return false;
        if (i == 0)
            first = n;
        if (i < 3)
            text.remove_prefix(dot + 1);
    }
    return first > 0 && first < 224 && first != 127;
}
bool integer(wtp::json::Value value, std::uint32_t& n) {
    if ((value.type() < '0' || value.type() > '9') || value.raw.empty())
        return false;
    const auto result = std::from_chars(value.raw.data(), value.raw.data() + value.raw.size(), n);
    return result.ec == std::errc{} && result.ptr == value.raw.data() + value.raw.size();
}
} // namespace
std::optional<Config> parse_config(std::string_view text) {
    using namespace wtp::json;
    if (text.size() > max_config_bytes)
        return {};
    auto root = parse(text);
    if (!root ||
        !fields(*root, {"version", "enabled", "station", "wifi", "schedules"}, {"expires_utc_s"}) ||
        root->get("version")->raw != "1" ||
        (root->get("enabled")->raw != "true" && root->get("enabled")->raw != "false"))
        return {};
    auto station = *root->get("station"), wifi = *root->get("wifi"),
         entries = *root->get("schedules");
    if (!fields(station, {"callsign", "locator", "power_dbm"}) ||
        !fields(wifi, {"ssid", "password", "ntp_ipv4"}) || entries.type() != '[')
        return {};
    for (auto name : {"callsign", "locator"})
        if (station.get(name)->type() != '"')
            return {};
    for (auto name : {"ssid", "password", "ntp_ipv4"})
        if (wifi.get(name)->type() != '"')
            return {};
    Config c;
    c.enabled = root->get("enabled")->boolean();
    if (const auto expiry = root->get("expires_utc_s")) {
        if (expiry->type() < '0' || expiry->type() > '9')
            return {};
        const auto result = std::from_chars(
            expiry->raw.data(), expiry->raw.data() + expiry->raw.size(), c.expires_utc_s);
        if (result.ec != std::errc{} || result.ptr != expiry->raw.data() + expiry->raw.size() ||
            (c.expires_utc_s &&
             (c.expires_utc_s < 1'735'689'600ULL || c.expires_utc_s >= 4'102'444'800ULL)))
            return {};
    }
    c.callsign = station.get("callsign")->string();
    c.locator = station.get("locator")->string();
    std::uint32_t power = 0;
    if (!integer(*station.get("power_dbm"), power) ||
        !encoding::wspr_type1(c.callsign, c.locator, power))
        return {};
    c.power_dbm = power;
    c.ssid = wifi.get("ssid")->string();
    c.password = wifi.get("password")->string();
    c.ntp_ipv4 = wifi.get("ntp_ipv4")->string();
    if (!printable(c.ssid, 1, 32) || !printable(c.password, 8, 63) || !ipv4(c.ntp_ipv4))
        return {};
    const auto schedules = entries.elements(9);
    if (schedules.empty() || schedules.size() > 8)
        return {};
    for (auto entry : schedules) {
        Schedule s;
        if (!fields(entry, {"period_s", "phase_s"}) ||
            !integer(*entry.get("period_s"), s.period_s) ||
            !integer(*entry.get("phase_s"), s.phase_s) || s.period_s < 120 || s.period_s > 86400 ||
            s.period_s % 120 || 86400 % s.period_s || s.phase_s >= s.period_s || s.phase_s % 120)
            return {};
        for (const auto& prior : c.schedules) {
            const auto gcd = std::gcd(prior.period_s, s.period_s);
            if (prior.phase_s % gcd == s.phase_s % gcd)
                return {}; // Recurrences intersect, even if their first slots differ.
        }
        c.schedules.push_back(s);
    }
    return c;
}
std::string serialize_config(const Config& c) {
    using wtp::json::quote;
    std::string result =
        "{\"version\":1,\"enabled\":" + std::string(c.enabled ? "true" : "false") +
        ",\"station\":{\"callsign\":" + quote(c.callsign) + ",\"locator\":" + quote(c.locator) +
        ",\"power_dbm\":" + std::to_string(c.power_dbm) + "},\"wifi\":{\"ssid\":" + quote(c.ssid) +
        ",\"password\":" + quote(c.password) + ",\"ntp_ipv4\":" + quote(c.ntp_ipv4) +
        "},\"schedules\":[";
    for (std::size_t i = 0; i < c.schedules.size(); ++i) {
        if (i)
            result += ',';
        result += "{\"period_s\":" + std::to_string(c.schedules[i].period_s) +
                  ",\"phase_s\":" + std::to_string(c.schedules[i].phase_s) + '}';
    }
    return result + "],\"expires_utc_s\":" + std::to_string(c.expires_utc_s) + "}";
}
} // namespace wsprrypico::standalone
