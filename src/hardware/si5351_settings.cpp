// SPDX-License-Identifier: MIT
#include "hardware/si5351_settings.hpp"

#include "wtp/json.hpp"

#include <charconv>

namespace wsprrypico::hardware {
std::string validate_si5351_settings(const Si5351Settings& settings) {
    if (const auto error = rf::si5351::validate(settings.synthesis); !error.empty())
        return std::string(error);
    if (settings.address != 0x60)
        return "unsupported_address";
    if (settings.synthesis.loopback.has_value() != settings.loopback_input.has_value())
        return "partial_loopback";
    if (settings.loopback_input &&
        (!eligible(*settings.loopback_input) || !(*settings.loopback_input & 1u)))
        return "unsupported_capture_pin";
    if (settings.gate && (!eligible(*settings.gate) || settings.gate == settings.loopback_input))
        return "invalid_gate_pin";
    rf::ReferencePolicy policy;
    policy.use = settings.reference_use;
    policy.trusted_uncertainty_ppb = settings.trusted_uncertainty_ppb;
    if (!rf::valid_reference_policy(policy) ||
        (settings.reference_use == rf::ReferenceUse::TrustedLocal && !settings.loopback_input))
        return "invalid_reference_policy";
    if (settings.manual_correction_ppb < -rf::correction_limit_ppb ||
        settings.manual_correction_ppb > rf::correction_limit_ppb)
        return "invalid_correction";
    if (settings.automatic_calibration)
        return "automatic_calibration_unavailable";
    return {};
}
namespace {
template <class T> bool integer(wtp::json::Value value, T& result) {
    if (value.raw.size() > 11)
        return false;
    const std::string raw(value.raw);
    if (raw.empty())
        return false;
    const auto converted = std::from_chars(raw.data(), raw.data() + raw.size(), result);
    return converted.ec == std::errc{} && converted.ptr == raw.data() + raw.size() &&
           std::to_string(result) == raw;
}
template <class T> std::string optional_number(const std::optional<T>& value) {
    return value ? std::to_string(*value) : "null";
}
} // namespace
std::optional<Si5351Settings> parse_si5351(std::string_view text) {
    using namespace wtp::json;
    if (text.size() > 768)
        return {};
    const auto root = parse(text);
    if (!root || !fields(*root, {"reference_hz", "reference_source", "crystal_load_pf", "address",
                                 "drive_ma", "transmit_output", "loopback_output",
                                 "loopback_input_gp", "rf_gate_gp", "rf_gate_active_high",
                                 "reference_use", "trusted_uncertainty_ppb",
                                 "manual_correction_ppb", "automatic_calibration"}))
        return {};
    Si5351Settings settings;
    if (!integer(*root->get("reference_hz"), settings.synthesis.reference_hz) ||
        !integer(*root->get("address"), settings.address) ||
        !integer(*root->get("drive_ma"), settings.synthesis.drive_ma) ||
        !integer(*root->get("manual_correction_ppb"), settings.manual_correction_ppb))
        return {};
    const auto source = root->get("reference_source");
    if (source->type() != '"')
        return {};
    if (source->string() == "crystal")
        settings.synthesis.reference = rf::si5351::Reference::Crystal;
    else if (source->string() == "external_xa")
        settings.synthesis.reference = rf::si5351::Reference::ExternalXa;
    else
        return {};
    const auto use = root->get("reference_use");
    if (use->type() != '"')
        return {};
    if (use->string() == "measurement_only")
        settings.reference_use = rf::ReferenceUse::MeasurementOnly;
    else if (use->string() == "trusted_local")
        settings.reference_use = rf::ReferenceUse::TrustedLocal;
    else
        return {};
    for (auto [key, destination] : std::array<std::pair<const char*, std::optional<unsigned>*>, 3>{
             {{"crystal_load_pf", &settings.synthesis.crystal_load_pf},
              {"loopback_input_gp", &settings.loopback_input},
              {"rf_gate_gp", &settings.gate}}}) {
        const auto value = *root->get(key);
        if (value.raw == "null")
            destination->reset();
        else {
            unsigned number = 0;
            if (!integer(value, number))
                return {};
            *destination = number;
        }
    }
    if (root->get("trusted_uncertainty_ppb")->raw != "null") {
        std::uint32_t uncertainty = 0;
        if (!integer(*root->get("trusted_uncertainty_ppb"), uncertainty))
            return {};
        settings.trusted_uncertainty_ppb = uncertainty;
    }
    unsigned tx = 0;
    if (!integer(*root->get("transmit_output"), tx) || tx > 2)
        return {};
    settings.synthesis.transmit = static_cast<rf::si5351::Output>(tx);
    const auto loopback = *root->get("loopback_output");
    if (loopback.raw != "null") {
        unsigned output = 0;
        if (!integer(loopback, output) || output > 2)
            return {};
        settings.synthesis.loopback = static_cast<rf::si5351::Output>(output);
    }
    for (auto [key, destination] : std::array<std::pair<const char*, bool*>, 2>{
             {{"rf_gate_active_high", &settings.gate_active_high},
              {"automatic_calibration", &settings.automatic_calibration}}}) {
        const auto value = *root->get(key);
        if (value.raw != "true" && value.raw != "false")
            return {};
        *destination = value.boolean();
    }
    if (!validate_si5351_settings(settings).empty())
        return {};
    return settings;
}
std::string serialize_si5351(const Si5351Settings& settings) {
    const auto& c = settings.synthesis;
    return "{\"reference_hz\":" + std::to_string(c.reference_hz) + ",\"reference_source\":" +
           wtp::json::quote(c.reference == rf::si5351::Reference::Crystal ? "crystal"
                                                                          : "external_xa") +
           ",\"crystal_load_pf\":" + optional_number(c.crystal_load_pf) +
           ",\"address\":" + std::to_string(settings.address) +
           ",\"drive_ma\":" + std::to_string(c.drive_ma) +
           ",\"transmit_output\":" + std::to_string(static_cast<unsigned>(c.transmit)) +
           ",\"loopback_output\":" +
           (c.loopback ? std::to_string(static_cast<unsigned>(*c.loopback)) : "null") +
           ",\"loopback_input_gp\":" + optional_number(settings.loopback_input) +
           ",\"rf_gate_gp\":" + optional_number(settings.gate) +
           ",\"rf_gate_active_high\":" + (settings.gate_active_high ? "true" : "false") +
           ",\"reference_use\":" +
           wtp::json::quote(settings.reference_use == rf::ReferenceUse::MeasurementOnly
                                ? "measurement_only"
                                : "trusted_local") +
           ",\"trusted_uncertainty_ppb\":" + optional_number(settings.trusted_uncertainty_ppb) +
           ",\"manual_correction_ppb\":" + std::to_string(settings.manual_correction_ppb) +
           ",\"automatic_calibration\":" + (settings.automatic_calibration ? "true" : "false") +
           "}";
}
Si5351Allocation validate_si5351(const PinPlan& plan, const Si5351Settings& settings,
                                 unsigned unavailable_pwm_slices, const FilterSettings& filters) {
    Si5351Allocation result;
    result.pins = validate(plan);
    if (!result.pins.valid())
        return result;
    if (const auto error = validate_filters(filters, plan); !error.empty()) {
        result.error = error;
        return result;
    }
    auto complete = plan;
    for (unsigned i = 0; i < filters.output_count; ++i)
        complete.lpf.push_back(filters.outputs[i].gp);
    result.pins = validate(complete);
    if (plan.engine != PinPlan::Engine::I2c) {
        result.error = "inactive_si5351";
        return result;
    }
    if (const auto error = validate_si5351_settings(settings); !error.empty()) {
        result.error = error;
        return result;
    }
    auto claim = [&](unsigned gp, std::string_view role) {
        if (!eligible(gp)) {
            result.error = "invalid_gp";
            result.pins.gp = gp;
            result.pins.role = role;
            return false;
        }
        if (!result.pins.owners[gp].empty()) {
            result.error = "pin_conflict";
            result.pins.gp = gp;
            result.pins.role = role;
            result.pins.owner = result.pins.owners[gp];
            return false;
        }
        result.pins.owners[gp] = role;
        return true;
    };
    if (settings.gate && !claim(*settings.gate, "si5351_gate"))
        return result;
    if (settings.loopback_input) {
        const auto gp = *settings.loopback_input;
        if (!claim(gp, "loopback"))
            return result;
        // RP2350 SDK PWM_GPIO_SLICE_NUM for exposed GPIOs <32. Odd GPIOs
        // are B inputs; GP7 is slice 3 B, aliased by GP23 (board-reserved).
        if ((gp & 1u) == 0) {
            result.error = "unsupported_capture_pin";
            return result;
        }
        const unsigned slice = (gp >> 1u) & 7u;
        if (unavailable_pwm_slices & (1u << slice)) {
            result.error = "pwm_slice_conflict";
            return result;
        }
        result.pwm_slice = slice;
    }
    return result;
}
} // namespace wsprrypico::hardware
