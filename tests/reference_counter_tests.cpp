// SPDX-License-Identifier: MIT
#include "rf/reference_counter.hpp"

#include <cassert>

using namespace wsprrypico::rf;
int main() {
    ReferenceCounter counter;
    assert(!counter.finish().coherent);
    // A physical 1 MHz input, with a conservative hardware capture bound of
    // 70 MHz, sampled every 0.5 ms. Many 16-bit wraps in a 10-second window.
    constexpr auto start = 1'000'000'000ULL;
    constexpr auto ticks = 20'000u;
    assert(counter.begin({65'000, start, start + 1000}, 70'000'000, 1));
    for (unsigned i = 1; i <= ticks; ++i) {
        const auto raw = start + i * 500'000ULL;
        assert(
            counter.sample({static_cast<std::uint16_t>(65'000u + i * 500u), raw, raw + 1000}, 1));
    }
    auto window = counter.finish();
    assert(window.coherent && window.edges == 10'000'000);
    assert(window.end_raw_ns - window.start_raw_ns == 10'000'000'000ULL);
    assert(window.endpoint_uncertainty_ns == 1000);
    const auto measurement = measure_reference(window, 1'000'000, 1, {});
    assert(measurement.valid() && measurement.ratio == 1);
    // A delayed observer cannot infer how many wraps occurred, even though
    // the modular count looks entirely plausible. Reject the whole window.
    assert(!counter.sample({42, window.end_raw_ns + 2'000'000, window.end_raw_ns + 2'001'000}, 1));
    assert(counter.error() == "counter_service_gap");
    assert(!counter.finish().coherent);
    assert(counter.begin({0, start, start + 1000}, 70'000'000, 1));
    assert(!counter.sample({500, start + 500'000, start + 501'000}, 2));
    assert(counter.error() == "plan_changed");
    assert(counter.begin({0, start, start + 1000}, 70'000'000, 1));
    assert(!counter.sample({1, start + 500, start + 1500}, 1));
    assert(counter.error() == "capture_order");
    assert(counter.begin({0, start, start + 1000}, 1'000'000, 1));
    assert(!counter.sample({900, start + 500'000, start + 501'000}, 1));
    assert(counter.error() == "counter_rate_bound");
    assert(!counter.begin({0, start + 1, start}, 1'000'000, 1));
    assert(!counter.begin({0, start, start + 1000}, 0, 1));
}
