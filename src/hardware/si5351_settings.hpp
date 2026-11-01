// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/filter_settings.hpp"
#include "rf/reference_measurement.hpp"
#include "rf/si5351_plan.hpp"

namespace wsprrypico::hardware {
struct Si5351Settings {
    bool operator==(const Si5351Settings&) const = default;
    rf::si5351::Configuration synthesis;
    unsigned address = 0x60;
    std::optional<unsigned> loopback_input;
    // Optional independent, externally biased RF gate. Its electrical and
    // execution contract must be established before it authorizes operation;
    // allocating a GPIO or accepting I2C readback cannot prove RF shutdown.
    std::optional<unsigned> gate;
    bool gate_active_high = true;
    rf::ReferenceUse reference_use = rf::ReferenceUse::MeasurementOnly;
    std::optional<std::uint32_t> trusted_uncertainty_ppb;
    std::int32_t manual_correction_ppb = 0;
    // GPS/PPS calibration is deliberately unavailable in this task slice.
    bool automatic_calibration = false;
};
std::string validate_si5351_settings(const Si5351Settings&);
std::optional<Si5351Settings> parse_si5351(std::string_view);
std::string serialize_si5351(const Si5351Settings&);
struct Si5351Allocation {
    Validation pins;
    std::optional<unsigned> pwm_slice;
    std::string error;
    bool valid() const {
        return pins.valid() && error.empty();
    }
};
// A PWM input uses the B channel and reserves its whole slice. The optional
// unavailable mask represents other platform owners, independently of GPIOs.
Si5351Allocation validate_si5351(const PinPlan&, const Si5351Settings&,
                                 unsigned unavailable_pwm_slices = 0,
                                 const FilterSettings& filters = {});
} // namespace wsprrypico::hardware
