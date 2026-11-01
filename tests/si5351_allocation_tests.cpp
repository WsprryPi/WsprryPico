// SPDX-License-Identifier: MIT
#include "hardware/si5351_settings.hpp"

#include <cassert>

using namespace wsprrypico;
int main() {
    hardware::PinPlan p;
    p.engine = hardware::PinPlan::Engine::I2c;
    p.rf.reset();
    p.i2c_pair = 1; // GP4/5.
    hardware::Si5351Settings s;
    s.synthesis = {25'000'000,
                   rf::si5351::Reference::Crystal,
                   8,
                   rf::si5351::Output::Clk0,
                   rf::si5351::Output::Clk2,
                   2};
    s.loopback_input = 7;
    auto allocation = hardware::validate_si5351(p, s);
    assert(allocation.valid() && allocation.pwm_slice == 3);
    assert(!hardware::validate_si5351(p, s, 1u << 3).valid());
    assert(hardware::validate_si5351(p, s, 1u << 2).valid());
    p.i2c_pair = 7; // GP6/7 conflicts with the loopback wire.
    assert(!hardware::validate_si5351(p, s).valid());
    p.i2c_pair = 1;
    for (unsigned gp = 0; gp <= 29; ++gp) {
        s.loopback_input = gp;
        const bool expected = hardware::eligible(gp) && (gp & 1u) && gp != 5;
        assert(hardware::validate_si5351(p, s).valid() == expected);
    }
    s.loopback_input = 7;
    p.button = 7;
    assert(!hardware::validate_si5351(p, s).valid());
    p.button = 14;
    p.amplifier = 7;
    assert(!hardware::validate_si5351(p, s).valid());
    p.amplifier.reset();
    s.gate = 7;
    assert(!hardware::validate_si5351(p, s).valid());
    s.gate = 6;
    assert(hardware::validate_si5351(p, s).valid()); // SIO gate does not own PWM.
    hardware::FilterSettings filters;
    filters.output_count = 1;
    filters.outputs[0] = {1, 7, "LPF", true};
    assert(!hardware::validate_si5351(p, s, 0, filters).valid());
    filters.outputs[0].gp = 6;
    assert(!hardware::validate_si5351(p, s, 0, filters).valid());
    filters.outputs[0].gp = 12;
    assert(hardware::validate_si5351(p, s, 0, filters).valid());
    s.loopback_input.reset();
    assert(!hardware::validate_si5351(p, s).valid());
    s.synthesis.loopback.reset();
    allocation = hardware::validate_si5351(p, s);
    assert(allocation.valid() && !allocation.pwm_slice);
    s.reference_use = rf::ReferenceUse::TrustedLocal;
    s.trusted_uncertainty_ppb = 100;
    assert(!hardware::validate_si5351(p, s).valid());
    s.synthesis.loopback = rf::si5351::Output::Clk2;
    s.loopback_input = 7;
    assert(hardware::validate_si5351(p, s).valid());
    s.address = 0x61;
    assert(!hardware::validate_si5351(p, s).valid());
    s.address = 0x60;
    p.engine = hardware::PinPlan::Engine::Direct;
    p.rf = 2;
    p.i2c_pair.reset();
    assert(!hardware::validate_si5351(p, s).valid());
}
