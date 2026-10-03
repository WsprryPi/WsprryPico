#include "hardware/pins.hpp"

#include "wtp/json.hpp"

#include <charconv>

namespace wsprrypico::hardware {
Validation validate(const PinPlan& p) {
    Validation v;
    auto fail = [&](std::string error, std::string role) {
        v.error = std::move(error);
        v.role = std::move(role);
    };
    if ((p.engine != PinPlan::Engine::Direct && p.engine != PinPlan::Engine::I2c) ||
        (p.engine == PinPlan::Engine::Direct && (!p.rf || p.i2c_pair)) ||
        (p.engine == PinPlan::Engine::I2c && (p.rf || !p.i2c_pair))) {
        fail("engine_allocation", "rf");
        return v;
    }
    auto claim = [&](unsigned gp, std::string role) {
        if (!eligible(gp)) {
            fail("invalid_gp", role);
            v.gp = gp;
            return false;
        }
        if (!v.owners[gp].empty()) {
            fail("pin_conflict", role);
            v.gp = gp;
            v.owner = v.owners[gp];
            return false;
        }
        v.owners[gp] = std::move(role);
        return true;
    };
    if (p.rf && !claim(*p.rf, "rf"))
        return v;
    if (p.i2c_pair) {
        if (*p.i2c_pair >= i2c_pairs.size()) {
            fail("invalid_pair", "i2c");
            return v;
        }
        const auto pair = i2c_pairs[*p.i2c_pair];
        if (!claim(pair.sda, "i2c_sda") || !claim(pair.scl, "i2c_scl"))
            return v;
    }
    if (p.button && !claim(*p.button, "button"))
        return v;
    if (p.amplifier && !claim(*p.amplifier, "amplifier"))
        return v;
    if (p.lpf.size() > 26) {
        fail("too_many_selectors", "lpf");
        return v;
    }
    for (std::size_t i = 0; i < p.lpf.size(); ++i)
        if (!claim(p.lpf[i], "lpf_" + std::to_string(i)))
            return v;
    if ((p.indicator != PinPlan::Indicator::Onboard &&
         p.indicator != PinPlan::Indicator::External &&
         p.indicator != PinPlan::Indicator::Disabled) ||
        ((p.indicator == PinPlan::Indicator::External) != p.indicator_gp.has_value())) {
        fail("indicator_allocation", "indicator");
        return v;
    }
    if (p.indicator_gp)
        (void)claim(*p.indicator_gp, "indicator");
    return v;
}
namespace {
bool number(wtp::json::Value value, unsigned& result) {
    if (value.raw.empty() || value.type() < '0' || value.type() > '9')
        return false;
    const std::string raw(value.raw);
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), result);
    return parsed.ec == std::errc{} && parsed.ptr == raw.data() + raw.size();
}
} // namespace
std::optional<PinPlan> parse_plan(std::string_view text) {
    using namespace wtp::json;
    if (text.size() > 2048)
        return {};
    auto root = parse(text);
    if (!root || !fields(*root,
                         {"engine", "rf_gp", "i2c_pair", "button_gp", "amplifier_gp", "lpf_gps",
                          "indicator", "indicator_gp"},
                         {"indicator_active_high"}))
        return {};
    PinPlan p;
    if (auto polarity = root->get("indicator_active_high")) {
        if (polarity->raw != "true" && polarity->raw != "false")
            return {};
        p.indicator_active_high = polarity->boolean();
    }
    auto engine = root->get("engine"), indicator = root->get("indicator");
    if (engine->type() != '"' || indicator->type() != '"')
        return {};
    if (engine->string() == "direct")
        p.engine = PinPlan::Engine::Direct;
    else if (engine->string() == "i2c")
        p.engine = PinPlan::Engine::I2c;
    else
        return {};
    if (indicator->string() == "onboard_led")
        p.indicator = PinPlan::Indicator::Onboard;
    else if (indicator->string() == "external")
        p.indicator = PinPlan::Indicator::External;
    else if (indicator->string() == "disabled")
        p.indicator = PinPlan::Indicator::Disabled;
    else
        return {};
    const std::array<std::pair<const char*, std::optional<unsigned>*>, 5> pins{
        {{"rf_gp", &p.rf},
         {"i2c_pair", &p.i2c_pair},
         {"button_gp", &p.button},
         {"amplifier_gp", &p.amplifier},
         {"indicator_gp", &p.indicator_gp}}};
    for (auto [key, dest] : pins) {
        const auto value = *root->get(key);
        if (value.raw == "null")
            dest->reset();
        else {
            unsigned gp = 0;
            if (!number(value, gp))
                return {};
            *dest = gp;
        }
    }
    const auto lpf = *root->get("lpf_gps");
    if (lpf.type() != '[')
        return {};
    // Read one beyond the allocation bound; never silently truncate a candidate.
    const auto entries = lpf.elements(27);
    if (entries.size() > 26)
        return {};
    for (auto entry : entries) {
        unsigned gp = 0;
        if (!number(entry, gp))
            return {};
        p.lpf.push_back(gp);
    }
    return p;
}
bool operational(const PinPlan& p) {
    return validate(p).valid() && p.engine == PinPlan::Engine::Direct && !p.amplifier &&
           p.lpf.empty();
}
std::string serialize_plan(const PinPlan& p) {
    const auto pin = [](std::optional<unsigned> gp) { return gp ? std::to_string(*gp) : "null"; };
    std::string out =
        "{\"engine\":" + wtp::json::quote(p.engine == PinPlan::Engine::Direct ? "direct" : "i2c") +
        ",\"rf_gp\":" + pin(p.rf) + ",\"i2c_pair\":" + pin(p.i2c_pair) +
        ",\"button_gp\":" + pin(p.button) + ",\"amplifier_gp\":" + pin(p.amplifier) +
        ",\"lpf_gps\":[";
    for (std::size_t i = 0; i < p.lpf.size(); ++i) {
        if (i)
            out += ',';
        out += std::to_string(p.lpf[i]);
    }
    return out + "],\"indicator\":" +
           wtp::json::quote(p.indicator == PinPlan::Indicator::Onboard    ? "onboard_led"
                            : p.indicator == PinPlan::Indicator::External ? "external"
                                                                          : "disabled") +
           ",\"indicator_gp\":" + pin(p.indicator_gp) +
           ",\"indicator_active_high\":" + (p.indicator_active_high ? "true}" : "false}");
}
std::string describe(const PinPlan& p) {
    using wtp::json::quote;
    const auto v = validate(p);
    std::string out = "{\"valid\":" + std::string(v.valid() ? "true" : "false") +
                      ",\"error\":" + quote(v.error) + ",\"role\":" + quote(v.role) +
                      ",\"owner\":" + quote(v.owner) +
                      ",\"gp\":" + (v.gp ? std::to_string(*v.gp) : "null") + ",\"owners\":{";
    bool comma = false;
    for (unsigned gp = 0; gp < v.owners.size(); ++gp) {
        if (v.owners[gp].empty())
            continue;
        if (comma)
            out += ',';
        comma = true;
        out += quote("GP" + std::to_string(gp)) + ':' + quote(v.owners[gp]);
    }
    out += "},\"i2c_available\":[";
    for (std::size_t i = 0; i < i2c_pairs.size(); ++i) {
        if (i)
            out += ',';
        const auto pair = i2c_pairs[i];
        out += v.owners[pair.sda].empty() && v.owners[pair.scl].empty() ? "true" : "false";
    }
    return out + "],\"operational_supported\":" + (operational(p) ? "true" : "false") +
           ",\"applied\":false}";
}
std::string choices() {
    std::string out = "{\"version\":1,\"numbering\":\"pico_gp\",\"eligible_gps\":[";
    bool comma = false;
    for (unsigned gp = 0; gp <= 28; ++gp) {
        if (!eligible(gp))
            continue;
        if (comma)
            out += ',';
        comma = true;
        out += std::to_string(gp);
    }
    out += "],\"i2c_pairs\":[";
    for (std::size_t i = 0; i < i2c_pairs.size(); ++i) {
        if (i)
            out += ',';
        const auto p = i2c_pairs[i];
        out += "{\"id\":" + std::to_string(i) + ",\"controller\":" + std::to_string(p.controller) +
               ",\"sda_gp\":" + std::to_string(p.sda) + ",\"scl_gp\":" + std::to_string(p.scl) +
               '}';
    }
    return out +
           "],\"indicator_choices\":[\"onboard_led\",\"external\",\"disabled\"],"
           "\"activation_supported\":true,\"adapter_support\":{\"rf\":\"configurable_pio_gpio\","
           "\"button\":\"configurable_active_low_when_enabled\",\"indicator\":\"configurable_"
           "shared_cues_and_tx\","
           "\"amplifier\":false,\"lpf\":false,\"i2c_rf\":false}}";
}
} // namespace wsprrypico::hardware
