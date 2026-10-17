#include "standalone/progress.hpp"

#include "encoding/wspr.hpp"

#include <algorithm>
#include <numeric>

namespace wsprrypico::standalone {
namespace {
using namespace wtp::json;
void member(std::string& out, std::string_view key, std::string_view value) {
    if (out.size() > 1)
        out += ',';
    out += quote(key) + ':' + std::string(value);
}
bool boolean(Value v) {
    return v.raw == "true" || v.raw == "false";
}
bool number(Value v) {
    return !v.raw.empty() && v.raw.size() <= 10 &&
           std::all_of(v.raw.begin(), v.raw.end(), [](char c) { return c >= '0' && c <= '9'; });
}
std::string record(const std::array<std::optional<std::string>, progress_fields.size()>& values) {
    std::string out = "{";
    for (std::size_t i = 0; i < values.size(); ++i)
        if (values[i])
            member(out, progress_fields[i], *values[i]);
    return out + '}';
}
} // namespace
bool valid_progress_field(std::string_view name, wtp::json::Value value) {
    if (name == "gpio_drive_ma")
        return valid_gpio_drive_token(value);
    if (value.raw == "null")
        return true; // Explicit absence, never fallback to applied.
    if (name == "callsign")
        return value.type() == '"' && encoding::valid_station_callsign(value.string());
    if (name == "locator")
        return value.type() == '"' && encoding::valid_station_locator(value.string());
    if (name == "power_dbm")
        return number(value) && value.raw.size() <= 2 &&
               encoding::valid_station_power(value.integer());
    if (name == "enabled")
        return boolean(value);
    if (name == "ntp_ipv4")
        return value.type() == '"' && valid_time_server(value.string());
    if (name == "expires_utc_s")
        return number(value) && (value.integer() == 0 || (value.integer() >= 1'735'689'600 &&
                                                          value.integer() <= 2'147'483'647));
    if (name == "pins") {
        const auto plan = hardware::parse_plan(std::string(value.raw));
        return plan && hardware::operational(*plan);
    }
    if (name == "frequency_policy") {
        if (!wtp::json::fields(value,
                               {"allow_unqualified_frequency", "allow_non_amateur_frequency"}))
            return false;
        const auto a = *value.get("allow_unqualified_frequency"),
                   b = *value.get("allow_non_amateur_frequency");
        return boolean(a) && boolean(b) && (!b.boolean() || a.boolean());
    }
    if (name == "wifi") {
        if (!wtp::json::fields(value, {"ssid", "password"}) || value.get("ssid")->type() != '"' ||
            value.get("password")->type() != '"')
            return false;
        const auto ssid = value.get("ssid")->string(), password = value.get("password")->string();
        return (ssid.empty() && password.empty()) ||
               valid_wifi_credentials(ssid, password, default_time_server);
    }
    if (name != "schedules" || value.type() != '[')
        return false;
    const auto schedules = value.elements(9);
    if (schedules.size() > 8)
        return false;
    std::vector<Schedule> checked;
    for (const auto row : schedules) {
        if (!wtp::json::fields(row, {"period_s", "phase_s"}))
            return false;
        const auto period = *row.get("period_s"), phase = *row.get("phase_s");
        if (!number(period) || !number(phase))
            return false;
        const auto p = period.integer(), f = phase.integer();
        if (p < 120 || p > 86400 || p % 120 || 86400 % p || f < 0 || f >= p || f % 120)
            return false;
        for (const auto& prior : checked)
            if (prior.phase_s % std::gcd(prior.period_s, unsigned(p)) ==
                unsigned(f) % std::gcd(prior.period_s, unsigned(p)))
                return false;
        checked.push_back({unsigned(p), unsigned(f)});
    }
    return true;
}
bool Progress::load() {
    healthy_ = false;
    values_ = {};
    receipt_ = "null";
    outcomes_ = "{}";
    if (!journal_.load())
        return false;
    if (!journal_.data().empty()) {
        const auto root = wtp::json::parse(journal_.data());
        if (!root || !wtp::json::fields(*root, {"schema", "fields", "receipt", "outcomes"}) ||
            (root->get("schema")->string() != "saved-progress/1" &&
             root->get("schema")->string() != "saved-progress/2" &&
             root->get("schema")->string() != "saved-progress/3"))
            return false;
        const auto input = *root->get("fields");
        if (input.raw.size() > max_progress_bytes ||
            !wtp::json::fields(input, {},
                               {"callsign", "locator", "power_dbm", "enabled", "schedules",
                                "expires_utc_s", "pins", "frequency_policy", "wifi", "ntp_ipv4",
                                "gpio_drive_ma"}))
            return false;
        if (input.get("gpio_drive_ma") && root->get("schema")->string() == "saved-progress/1")
            return false;
        for (std::size_t i = 0; i < values_.size(); ++i)
            if (const auto value = input.get(progress_fields[i])) {
                if (!valid_progress_field(progress_fields[i], *value))
                    return false;
                values_[i] = std::string(value->raw);
            }
        if (amplifier_view_required() && root->get("schema")->string() != "saved-progress/3")
            return false;
        if (root->get("receipt")->type() != '"' || root->get("receipt")->string().size() != 64 ||
            root->get("outcomes")->type() != '{')
            return false;
        const auto receipt = root->get("receipt")->string();
        if (!std::all_of(receipt.begin(), receipt.end(),
                         [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
            !wtp::json::fields(*root->get("outcomes"), {},
                               {"callsign", "locator", "power_dbm", "enabled", "schedules",
                                "expires_utc_s", "pins", "frequency_policy", "wifi", "ntp_ipv4",
                                "gpio_drive_ma"}))
            return false;
        for (const auto name : progress_fields)
            if (const auto outcome = root->get("outcomes")->get(name))
                if (outcome->type() != '"' ||
                    (outcome->string() != "saved" && outcome->string() != "cleared" &&
                     outcome->string() != "invalid"))
                    return false;
        receipt_ = std::string(root->get("receipt")->raw);
        outcomes_ = std::string(root->get("outcomes")->raw);
    }
    healthy_ = true;
    return true;
}
bool Progress::erase() {
    healthy_ = false;
    if (!flash_.erase(0) || !flash_.erase(4096))
        return false;
    return load();
}
std::optional<std::string> Progress::save(Value input, std::string_view receipt) {
    if (!healthy() || receipt.size() != 64 ||
        !std::all_of(receipt.begin(), receipt.end(),
                     [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
        input.raw.size() > 2048 ||
        !wtp::json::fields(input, {},
                           {"callsign", "locator", "power_dbm", "enabled", "schedules",
                            "expires_utc_s", "pins", "frequency_policy", "wifi", "ntp_ipv4",
                            "gpio_drive_ma"}) ||
        wtp::json::fields(input, {}))
        return {};
    if (const auto drive = input.get("gpio_drive_ma"); drive && !valid_gpio_drive_token(*drive))
        return {};
    if (const auto pins = input.get("pins"); pins && !valid_progress_field("pins", *pins))
        return {};
    auto next = values_;
    std::string outcomes = "{";
    bool accepted = false;
    for (std::size_t i = 0; i < next.size(); ++i) {
        const auto value = input.get(progress_fields[i]);
        if (!value)
            continue;
        const bool valid = valid_progress_field(progress_fields[i], *value);
        member(outcomes, progress_fields[i],
               quote(valid ? value->raw == "null" ? "cleared" : "saved" : "invalid"));
        if (valid) {
            next[i] = progress_fields[i] == "pins" && value->raw != "null"
                          ? hardware::serialize_plan(*hardware::parse_plan(std::string(value->raw)))
                          : std::string(value->raw);
            accepted = true;
        }
    }
    outcomes += '}';
    if (!accepted)
        return outcomes;
    const auto fields = record(next);
    if (fields.size() > max_progress_bytes)
        return {};
    const auto receipt_json = quote(receipt);
    const auto plan = next[6] && *next[6] != "null" ? hardware::parse_plan(*next[6]) : std::nullopt;
    const auto text = "{\"schema\":" +
                      quote(plan && hardware::requires_amplifier_view(*plan) ? "saved-progress/3"
                            : next[10]                                       ? "saved-progress/2"
                                                                             : "saved-progress/1") +
                      ",\"fields\":" + fields + ",\"receipt\":" + receipt_json +
                      ",\"outcomes\":" + outcomes + '}';
    if (!journal_.append(text)) {
        healthy_ = false;
        return {};
    }
    values_ = std::move(next);
    receipt_ = receipt_json;
    outcomes_ = outcomes;
    return outcomes;
}
std::string Progress::fields(bool redacted, bool station_only, bool drive,
                             bool amplifier_view) const {
    auto values = values_;
    if (!drive)
        values[10].reset();
    if (station_only)
        for (std::size_t i = 3; i < values.size(); ++i)
            values[i].reset();
    if (amplifier_view && values[6] && *values[6] != "null")
        values[6] = hardware::serialize_plan(*hardware::parse_plan(*values[6]), true);
    if (redacted && values[8] && *values[8] != "null") {
        const auto wifi = wtp::json::parse(*values[8]);
        values[8] = "{\"ssid\":" + std::string(wifi->get("ssid")->raw) + ",\"password\":null}";
    }
    return record(values);
}
std::string Progress::outcomes(bool station_only, bool drive) const {
    if (!station_only && drive)
        return outcomes_;
    const auto root = wtp::json::parse(outcomes_);
    std::string result = "{";
    for (std::size_t i = 0; i < (station_only ? 3U : 10U); ++i)
        if (const auto v = root->get(progress_fields[i]))
            member(result, progress_fields[i], std::string(v->raw));
    return result + '}';
}
std::optional<Config> Progress::candidate(const std::optional<Config>& applied,
                                          std::string_view domain, bool drive,
                                          bool amplifier) const {
    if (!healthy())
        return {};
    if (domain != "all" && domain != "station" && domain != "network" && domain != "radio" &&
        !(drive && domain == "drive"))
        return {};
    if (!applied && domain != "station" && domain != "all")
        return {};
    Config c = applied.value_or(Config{});
    const auto value = [&](std::size_t i) -> std::optional<wtp::json::Value> {
        return values_[i] ? std::optional{wtp::json::Value{*values_[i]}} : std::nullopt;
    };
    for (std::size_t i = 0; i < values_.size(); ++i) {
        if (i == 10 && (!drive || domain != "drive"))
            continue;
        const auto field_domain = i == 10 ? "drive"
                                  : i < 3 ? "station"
                                  : i < 8 ? "radio"
                                          : "network";
        if (domain != "all" && domain != field_domain)
            continue;
        const auto v = value(i);
        if (!v) {
            if (i < 3 && !applied)
                return {};
            continue;
        }
        if (v->raw == "null")
            return {}; // Missing explicitly, not an invented default.
        switch (i) {
        case 0:
            c.callsign = v->string();
            break;
        case 1:
            c.locator = v->string();
            break;
        case 2:
            c.power_dbm = unsigned(v->integer());
            break;
        case 3:
            c.enabled = v->boolean();
            break;
        case 4:
            c.schedules.clear();
            for (const auto row : v->elements(8))
                c.schedules.push_back({unsigned(row.get("period_s")->integer()),
                                       unsigned(row.get("phase_s")->integer())});
            break;
        case 5:
            c.expires_utc_s = v->integer();
            break;
        case 6:
            c.pins = *hardware::parse_plan(std::string(v->raw));
            if (!amplifier && applied) {
                c.pins.amplifier = applied->pins.amplifier;
                c.pins.amplifier_active_high = applied->pins.amplifier_active_high;
            }
            break;
        case 7:
            c.allow_unqualified_frequency = v->get("allow_unqualified_frequency")->boolean();
            c.allow_non_amateur_frequency = v->get("allow_non_amateur_frequency")->boolean();
            break;
        case 8:
            c.ssid = v->get("ssid")->string();
            c.password = v->get("password")->string();
            break;
        case 9:
            c.ntp_ipv4 = v->string();
            break;
        case 10:
            c.gpio_drive_ma = unsigned(v->integer());
            break;
        }
    }
    return parse_config(serialize_config(c));
}
bool Progress::amplifier_view_required() const {
    if (!values_[6] || *values_[6] == "null")
        return false;
    const auto plan = hardware::parse_plan(*values_[6]);
    return plan && hardware::requires_amplifier_view(*plan);
}
std::string Progress::station_fields(const std::optional<Config>& applied) const {
    std::string result = "{";
    for (std::size_t i = 0; i < 3; ++i) {
        const auto prior = !applied ? "null"
                           : i == 0 ? quote(applied->callsign)
                           : i == 1 ? quote(applied->locator)
                                    : std::to_string(applied->power_dbm);
        member(result, progress_fields[i], values_[i].value_or(prior));
    }
    return result + '}';
}
std::optional<Config> Progress::station_candidate(const std::optional<Config>& applied) const {
    if (!healthy())
        return {};
    const auto text = station_fields(applied);
    const auto station = wtp::json::parse(text);
    for (const auto name : {"callsign", "locator", "power_dbm"})
        if (station->get(name)->raw == "null")
            return {};
    Config c = applied.value_or(Config{});
    c.callsign = station->get("callsign")->string();
    c.locator = station->get("locator")->string();
    c.power_dbm = unsigned(station->get("power_dbm")->integer());
    return encoding::valid_station_details(c.callsign, c.locator, c.power_dbm) ? std::optional{c}
                                                                               : std::nullopt;
}
} // namespace wsprrypico::standalone
