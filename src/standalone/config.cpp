#include "standalone/config.hpp"

#include "application/frequency_policy.hpp"
#include "encoding/wspr.hpp"
#include "rf/calibration.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <limits>
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
    if (value.raw.size() > 10)
        return false;
    std::array<char, 10> text{};
    std::copy(value.raw.begin(), value.raw.end(), text.begin());
    const auto result = std::from_chars(text.data(), text.data() + value.raw.size(), n);
    return result.ec == std::errc{} && result.ptr == text.data() + value.raw.size();
}
} // namespace
bool valid_gpio_drive(unsigned ma) {
    return ma == 2 || ma == 4 || ma == 8 || ma == 12;
}
bool valid_ntp_timeout_token(wtp::json::Value value, bool unlimited) {
    std::uint32_t seconds = 0;
    return integer(value, seconds) && std::to_string(seconds) == value.raw &&
           ((unlimited && seconds == 0) || seconds >= minimum_ntp_timeout_s) &&
           seconds <= maximum_ntp_timeout_s && seconds % 60 == 0;
}
std::optional<std::array<std::uint64_t, 4>> wspr_tones(std::uint64_t dial_hz) {
    constexpr auto nhz_per_hz = 1'000'000'000ULL;
    constexpr auto highest_offset = audio_offset_nhz + center_to_tone0_nhz;
    if (!dial_hz ||
        dial_hz > (std::numeric_limits<std::uint64_t>::max() - highest_offset) / nhz_per_hz)
        return {};
    const auto tone0 = dial_hz * nhz_per_hz + audio_offset_nhz - center_to_tone0_nhz;
    std::array<std::uint64_t, 4> tones{};
    for (unsigned k = 0; k < tones.size(); ++k)
        tones[k] = tone0 + k * spacing_nhz;
    return tones;
}
bool valid_wspr_frequency_token(wtp::json::Value value) {
    std::uint32_t frequency = 0;
    return integer(value, frequency) && std::to_string(frequency) == value.raw &&
           frequency >= minimum_wspr_dial_hz && frequency <= maximum_wspr_dial_hz;
}
bool wspr_frequency_allowed(const Config& config, std::uint64_t minimum_nhz,
                            std::uint64_t maximum_nhz) {
    if (!config.wspr_dial_frequency_hz)
        return false;
    const auto tones = wspr_tones(*config.wspr_dial_frequency_hz);
    if (!tones)
        return false;
    for (const auto tone : *tones) {
        if (tone < minimum_nhz || tone > maximum_nhz ||
            !application::frequency_allowed(tone, config.allow_unqualified_frequency,
                                            config.allow_non_amateur_frequency))
            return false;
    }
    return true;
}
bool valid_gpio_drive_token(wtp::json::Value value) {
    return value.raw == "2" || value.raw == "4" || value.raw == "8" || value.raw == "12";
}
bool valid_time_server(std::string_view text) {
    if (ipv4(text))
        return true;
    // lwIP also accepts legacy integer/octal/hex address spellings. Reject
    // numeric-looking alternatives rather than bypassing canonical peer checks.
    bool numeric = true;
    for (auto rest = text; !rest.empty();) {
        const auto dot = rest.find('.');
        auto label = rest.substr(0, dot);
        const bool hex = label.starts_with("0x") || label.starts_with("0X");
        if (hex)
            label.remove_prefix(2);
        numeric =
            numeric && !label.empty() && std::all_of(label.begin(), label.end(), [hex](char c) {
                return (c >= '0' && c <= '9') ||
                       (hex && ((c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')));
            });
        if (dot == rest.npos)
            break;
        rest.remove_prefix(dot + 1);
    }
    if (text.empty() || text.size() > 253 || numeric)
        return false;
    if (text.back() == '.')
        text.remove_suffix(1);
    while (!text.empty()) {
        const auto dot = text.find('.');
        const auto label = text.substr(0, dot);
        if (label.empty() || label.size() > 63 || label.front() == '-' || label.back() == '-' ||
            !std::all_of(label.begin(), label.end(), [](char c) {
                return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                       c == '-';
            }))
            return false;
        if (dot == text.npos)
            return true;
        text.remove_prefix(dot + 1);
        if (text.empty())
            return false;
    }
    return false;
}
bool valid_wifi_credentials(std::string_view ssid, std::string_view password,
                            std::string_view time_server) {
    return printable(ssid, 1, 32) && printable(password, 8, 63) && valid_time_server(time_server);
}
std::optional<Config> parse_config(std::string_view text) {
    using namespace wtp::json;
    if (text.size() > max_config_bytes)
        return {};
    auto root = parse(text);
    if (!root ||
        !fields(*root, {"version", "enabled", "station", "wifi", "schedules"},
                {"expires_utc_s", "pins", "allow_unqualified_frequency",
                 "allow_non_amateur_frequency", "gpio_drive_ma", "manual_correction_ppb",
                 "ntp_rf_calibration", "wspr_dial_frequency_hz", "ntp_timeout_s",
                 "amplifier_timing"}) ||
        (root->get("version")->raw != "1" && root->get("version")->raw != "2") ||
        (root->get("enabled")->raw != "true" && root->get("enabled")->raw != "false"))
        return {};
    auto station = *root->get("station"), wifi = *root->get("wifi"),
         entries = *root->get("schedules");
    if (!fields(station, {"callsign", "locator", "power_dbm"}) ||
        !fields(wifi, {"ssid", "password"}, {"ntp_ipv4"}) || entries.type() != '[')
        return {};
    for (auto name : {"callsign", "locator"})
        if (station.get(name)->type() != '"')
            return {};
    for (auto name : {"ssid", "password"})
        if (wifi.get(name)->type() != '"')
            return {};
    const bool unlimited = root->get("version")->raw == "2";
    if (unlimited && (!root->get("ntp_timeout_s") || root->get("ntp_timeout_s")->raw != "0"))
        return {};
    Config c;
    if (const auto timing = root->get("amplifier_timing")) {
        std::uint32_t lead = 0, tail = 0;
        if (!fields(*timing, {"lead_ms", "tail_ms"}) || !integer(*timing->get("lead_ms"), lead) ||
            !integer(*timing->get("tail_ms"), tail) ||
            std::to_string(lead) != timing->get("lead_ms")->raw ||
            std::to_string(tail) != timing->get("tail_ms")->raw ||
            lead > rf::AmplifierTiming::maximum_ms || tail > rf::AmplifierTiming::maximum_ms)
            return {};
        c.amplifier_timing = {lead, tail};
    }
    if (const auto timeout = root->get("ntp_timeout_s")) {
        if (!valid_ntp_timeout_token(*timeout, unlimited))
            return {};
        c.ntp_timeout_s = unsigned(timeout->integer());
    }
    if (const auto frequency = root->get("wspr_dial_frequency_hz")) {
        if (!valid_wspr_frequency_token(*frequency))
            return {};
        c.wspr_dial_frequency_hz = std::uint32_t(frequency->integer());
    }
    if (const auto correction = root->get("manual_correction_ppb")) {
        std::int32_t value = 0;
        const auto raw = std::string(correction->raw);
        const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), value);
        if (raw.empty() || parsed.ec != std::errc{} || parsed.ptr != raw.data() + raw.size() ||
            std::to_string(value) != raw || value < -rf::correction_limit_ppb ||
            value > rf::correction_limit_ppb)
            return {};
        c.manual_correction_ppb = value;
    }
    if (const auto mode = root->get("ntp_rf_calibration")) {
        if (mode->raw != "true" && mode->raw != "false")
            return {};
        c.ntp_rf_calibration = mode->boolean();
    }
    if (const auto drive = root->get("gpio_drive_ma")) {
        if (!valid_gpio_drive_token(*drive))
            return {};
        c.gpio_drive_ma = unsigned(drive->integer());
    }
    for (const auto name : {"allow_unqualified_frequency", "allow_non_amateur_frequency"}) {
        if (const auto flag = root->get(name)) {
            if (flag->raw != "true" && flag->raw != "false")
                return {};
            (name == std::string_view("allow_unqualified_frequency")
                 ? c.allow_unqualified_frequency
                 : c.allow_non_amateur_frequency) = flag->boolean();
        }
    }
    if (const auto pins = root->get("pins")) {
        auto parsed = hardware::parse_plan(std::string(pins->raw));
        if (!parsed || !hardware::operational(*parsed))
            return {};
        c.pins = *parsed;
    }
    c.enabled = root->get("enabled")->boolean();
    if (const auto expiry = root->get("expires_utc_s")) {
        if (expiry->type() < '0' || expiry->type() > '9')
            return {};
        std::uint32_t seconds = 0;
        if (!integer(*expiry, seconds))
            return {};
        c.expires_utc_s = seconds;
        if (c.expires_utc_s &&
            (c.expires_utc_s < 1'735'689'600ULL || c.expires_utc_s >= 4'102'444'800ULL))
            return {};
    }
    c.callsign = station.get("callsign")->string();
    c.locator = station.get("locator")->string();
    std::uint32_t power = 0;
    if (!integer(*station.get("power_dbm"), power) ||
        !encoding::valid_station_details(c.callsign, c.locator, power))
        return {};
    c.power_dbm = power;
    c.ssid = wifi.get("ssid")->string();
    c.password = wifi.get("password")->string();
    if (const auto time_server = wifi.get("ntp_ipv4")) {
        if (time_server->type() != '"')
            return {};
        c.ntp_ipv4 = time_server->string();
    }
    if (!((c.ssid.empty() && c.password.empty() && valid_time_server(c.ntp_ipv4)) ||
          valid_wifi_credentials(c.ssid, c.password, c.ntp_ipv4)))
        return {};
    const auto schedules = entries.elements(9);
    if ((c.enabled && schedules.empty()) || schedules.size() > 8)
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
std::string serialize_config(const Config& c, bool amplifier_view) {
    using wtp::json::quote;
    std::string result =
        "{\"version\":" + std::string(c.ntp_timeout_s == 0 ? "2" : "1") +
        ",\"enabled\":" + std::string(c.enabled ? "true" : "false") +
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
    result += "],\"expires_utc_s\":" + std::to_string(c.expires_utc_s);
    // Keep the legacy canonical payload for default assignments. Nondefault
    // assignments require the new firmware; older images reject that extension.
    if (amplifier_view || c.pins != hardware::PinPlan{})
        result += ",\"pins\":" + hardware::serialize_plan(c.pins, amplifier_view);
    // Default-off records retain their legacy canonical bytes. Opt-ins require
    // firmware that understands these extensions; old firmware rejects them.
    if (c.allow_unqualified_frequency)
        result += ",\"allow_unqualified_frequency\":true";
    if (c.allow_non_amateur_frequency)
        result += ",\"allow_non_amateur_frequency\":true";
    if (c.gpio_drive_ma != 4)
        result += ",\"gpio_drive_ma\":" + std::to_string(c.gpio_drive_ma);
    if (c.manual_correction_ppb)
        result += ",\"manual_correction_ppb\":" + std::to_string(c.manual_correction_ppb);
    if (c.ntp_rf_calibration)
        result += ",\"ntp_rf_calibration\":true";
    if (c.wspr_dial_frequency_hz)
        result += ",\"wspr_dial_frequency_hz\":" + std::to_string(*c.wspr_dial_frequency_hz);
    if (c.ntp_timeout_s != default_ntp_timeout_s)
        result += ",\"ntp_timeout_s\":" + std::to_string(c.ntp_timeout_s);
    if (c.amplifier_timing != rf::AmplifierTiming{})
        result +=
            ",\"amplifier_timing\":{\"lead_ms\":" + std::to_string(c.amplifier_timing.lead_ms) +
            ",\"tail_ms\":" + std::to_string(c.amplifier_timing.tail_ms) + "}";
    return result + "}";
}
} // namespace wsprrypico::standalone
