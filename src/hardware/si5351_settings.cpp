// SPDX-License-Identifier: MIT
#include "hardware/si5351_settings.hpp"

namespace wsprrypico::hardware {
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
    if (const auto error = rf::si5351::validate(settings.synthesis); !error.empty()) {
        result.error = error;
        return result;
    }
    // Supported arrangement: Si5351A 10-MSOP, standard address, CLK0..CLK2.
    // No identity is inferred from an ACK, nor support for custom-order parts.
    if (settings.address != 0x60) {
        result.error = "unsupported_address";
        return result;
    }
    if (settings.synthesis.loopback.has_value() != settings.loopback_input.has_value()) {
        result.error = "partial_loopback";
        return result;
    }
    rf::ReferencePolicy policy;
    policy.use = settings.reference_use;
    policy.trusted_uncertainty_ppb = settings.trusted_uncertainty_ppb;
    if (!rf::valid_reference_policy(policy) ||
        (settings.reference_use == rf::ReferenceUse::TrustedLocal && !settings.loopback_input)) {
        result.error = "invalid_reference_policy";
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
