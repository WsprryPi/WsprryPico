// SPDX-License-Identifier: MIT
#include "rf/pico/reference_capture.hpp"
#include "sdk.hpp"

#include <cassert>

using namespace wsprrypico;
int main() {
    hardware::PinPlan pins;
    pins.engine = hardware::PinPlan::Engine::I2c;
    pins.rf.reset();
    pins.i2c_pair = 1;
    hardware::Si5351Settings settings;
    settings.synthesis = {25'000'000,
                          rf::si5351::Reference::ExternalXa,
                          {},
                          rf::si5351::Output::Clk0,
                          rf::si5351::Output::Clk2,
                          2};
    settings.loopback_input = 7;
    rf::PicoReferenceCapture first, second;
    assert(first.open(pins, settings));
    assert(!second.open(pins, settings));
    assert(capture_mock::input_enabled[7] && !capture_mock::output[7]);
    assert(!capture_mock::pwm_enabled[3] && !capture_mock::irq_enabled[3]);
    assert(first.begin(1));
    for (unsigned i = 0; i < 40'000; ++i) {
        capture_mock::raw_us += 250;
        capture_mock::counters[3] += 250;
        assert(first.poll(1));
    }
    const auto window = first.finish();
    assert(window.coherent && window.edges == 10'000'000);
    assert(window.end_raw_ns - window.start_raw_ns == 10'000'000'000ULL);
    assert(!capture_mock::pwm_enabled[3]);
    assert(rf::measure_reference(window, 1'000'000, 1, {}).valid());
    assert(first.begin(2));
    capture_mock::raw_us += 1000; // Enough time to hide more than one hardware wrap.
    assert(!first.poll(2) && !capture_mock::pwm_enabled[3]);
    assert(!first.finish().coherent);
    assert(first.begin(3));
    capture_mock::raw_us += 250;
    capture_mock::system_hz = 150'000'000;
    assert(!first.poll(3) && !capture_mock::pwm_enabled[3]);
    assert(!first.begin(4)); // Changed clock tree needs a new allocation/open.
    first.close();
    assert(second.open(pins, settings));
    assert(second.begin(4));
    capture_mock::raw_us += 250;
    assert(!second.poll(5)); // Hardware-plan revision mismatch.
    second.close();
    assert(!capture_mock::output[7] && !capture_mock::pwm_enabled[3]);
    assert((mock_bank.io[7].ctrl & IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS) == GPIO_FUNC_SIO);
    assert(capture_mock::transitions > 10);
}
