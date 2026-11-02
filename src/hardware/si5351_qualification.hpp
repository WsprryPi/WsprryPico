// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/si5351_qualification_profile.hpp"
#include "hardware/si5351_settings.hpp"

namespace wsprrypico::hardware {
inline bool si5351_profile_matches(const PinPlan& pins, const Si5351Settings& settings,
                                   std::uint64_t clock_hz, const FilterSettings& filters = {}) {
    const auto& s = settings.synthesis;
    return pins.engine == PinPlan::Engine::I2c && pins.i2c_pair == si5351_support::i2c_pair &&
           clock_hz == si5351_support::system_clock_hz &&
           settings.address == si5351_support::address &&
           s.reference_hz == si5351_support::reference_hz &&
           s.reference == rf::si5351::Reference::ExternalXa &&
           static_cast<unsigned>(s.transmit) == si5351_support::transmit_output &&
           s.drive_ma == si5351_support::drive_ma && !settings.gate &&
           (!s.loopback || (static_cast<unsigned>(*s.loopback) == si5351_support::loopback_output &&
                            settings.loopback_input == si5351_support::loopback_input_gp)) &&
           validate_si5351(pins, settings, 0, filters).valid();
}
inline bool si5351_ordinary_qualified(const PinPlan& pins, const Si5351Settings& settings,
                                      std::uint64_t clock_hz, const FilterSettings& filters = {}) {
    return si5351_support::qualified && si5351_profile_matches(pins, settings, clock_hz, filters);
}
} // namespace wsprrypico::hardware
