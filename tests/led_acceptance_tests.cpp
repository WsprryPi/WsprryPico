#include "pico/cyw43_arch.h"
#include "provisioning/button_runtime.hpp"
#include "provisioning/button_safety.hpp"
#include "provisioning/led_acceptance.hpp"
#include "provisioning/pico/indicator_output.hpp"

#include <cassert>
#include <cstdint>

namespace wsprrypico::provisioning {
LedAcceptance led_acceptance;
}
cyw43_t cyw43_state;
namespace {
std::uint64_t now_us = 0;
unsigned writes = 0;
} // namespace
std::uint64_t time_us_64() {
    return now_us;
}
void gpio_init(unsigned) {}
void gpio_put(unsigned, bool) {
    ++writes;
}
void gpio_set_dir(unsigned, bool) {}
int cyw43_gpio_set(cyw43_t*, int, bool) {
    ++writes;
    return 0;
}

int main() {
    using namespace wsprrypico;
    {
        provisioning::ButtonDiagnostic input;
        provisioning::ButtonSafety worker;
        unsigned stops = 0, resets = 0, setups = 0;
        const auto stop = [&]() {
            ++stops;
            return true;
        };
        const auto setup = [&](std::uint64_t, bool) {
            ++setups;
            return true;
        };
        auto runtime =
            provisioning::ButtonRuntime{stop, setup, [](std::uint64_t) {}, [&]() { ++resets; }};
        const auto release_ms = 10 + provisioning::LedAcceptance::hold_duration_ms;
        for (std::uint32_t ms = 0; ms <= release_ms + 110; ++ms) {
            const bool held = ms >= 10 && ms < release_ms;
            const auto event = input.observe(ms * 1000ULL, held);
            runtime.observe(event, ms, held);
            (void)worker.observe(ms * 1000ULL, held);
        }
        assert(stops == 1 && resets == 0 && setups == 0);
        assert(runtime.stop_verified() && runtime.reset_events() == 0);
        assert(worker.inhibited() && !worker.reset() && !worker.fault());
        assert(worker.duration_us() >= provisioning::ButtonDiagnostic::stop_limit_us);
        assert(worker.requested_at_us() < release_ms * 1000ULL);
    }
    auto& f = provisioning::led_acceptance;
    assert(f.ap(10));
    assert(!f.ap(11));
    assert(f.ap_active(20'009));
    assert(!f.ap_active(20'010));
    assert(f.schedule() && !f.schedule());
    assert(f.hold() && !f.hold());
    assert(f.fail(0) && !f.fail(1));
    provisioning::PicoIndicatorOutput onboard;
    assert(onboard.write(false));
    const auto before = writes;
    assert(!onboard.write(true));
    assert(writes == before && f.rejected() == 1);
    hardware::PinPlan p;
    p.indicator = hardware::PinPlan::Indicator::External;
    p.indicator_gp = 15;
    provisioning::PicoIndicatorOutput selected(p);
    provisioning::PicoIndicatorOutput operational(
        p, provisioning::PicoIndicatorOutput::Role::Operational);
    assert(operational.write(true)); // The TX fault never corrupts operational cues.
    assert(!selected.write(true));
    assert(selected.write(false));
    now_us = 80'000'000;
    assert(selected.write(true) && onboard.write(true)); // Local expiration, no USB needed.
    p.indicator = hardware::PinPlan::Indicator::Disabled;
    provisioning::PicoIndicatorOutput disabled(p);
    assert(disabled.write(true));
}
