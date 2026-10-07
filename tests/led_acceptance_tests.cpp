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
struct LampOutput : wsprrypico::provisioning::IndicatorOutput {
    bool on = false, fail_on = false, fail_off = false;
    unsigned calls = 0;
    bool write(bool value) override {
        ++calls;
        if ((value && fail_on) || (!value && fail_off))
            return false;
        on = value;
        return true;
    }
};
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
        using Lamp = provisioning::LedAcceptance::Lamp;
        provisioning::LedAcceptance fixture;
        LampOutput output;
        provisioning::IndicatorController indicator(output, "DUT");
        indicator.softap_ready(true);
        assert(indicator.identify("identify", "DUT", true, true, 0) ==
               provisioning::IndicatorCode::Ok);
        assert(fixture.lamp(indicator, Lamp::On, 0) && output.on);
        for (const auto now : {1'000ULL, 20'000ULL, 864'000'000ULL}) {
            assert(fixture.poll_lamp(indicator, now) && output.on);
        }
        const auto calls = output.calls;
        assert(fixture.lamp(indicator, Lamp::On, 864'000'000ULL));
        assert(output.calls == calls); // Repeating ON neither expires nor pulses the lamp.
        assert(!fixture.ap(1) && !fixture.fail(1) && !fixture.schedule() && !fixture.hold());
        assert(fixture.lamp(indicator, Lamp::Off, 864'000'001ULL) && !output.on);
        assert(fixture.poll_lamp(indicator, 1'728'000'000ULL) && !output.on);
        assert(fixture.lamp(indicator, Lamp::Normal, 1'728'000'000ULL));
        assert(!fixture.lamp_active() && output.on); // Normal AP cue resumes.
        assert(fixture.fail(1'728'000'001ULL));
        assert(!fixture.lamp(indicator, Lamp::On, 1'728'000'002ULL));
    }
    {
        provisioning::LedAcceptance fixture;
        LampOutput output;
        provisioning::IndicatorController indicator(output, "DUT");
        assert(fixture.lamp(indicator, provisioning::LedAcceptance::Lamp::On, 0));
        output.fail_off = true;
        assert(!fixture.lamp(indicator, provisioning::LedAcceptance::Lamp::Off, 1));
        assert(output.on && !indicator.status(1).output_known);
        output.fail_off = false;
        assert(!fixture.poll_lamp(indicator, 2)); // Fault remains latched even after OFF succeeds.
        assert(!output.on && indicator.status(2).output_known);
        assert(indicator.status(2).output_fault);
    }
    {
        provisioning::LedAcceptance fixture;
        LampOutput output;
        output.fail_on = true;
        provisioning::IndicatorController indicator(output, "DUT");
        assert(!fixture.lamp(indicator, provisioning::LedAcceptance::Lamp::On, 0));
        assert(!output.on && output.calls == 2);
        assert(fixture.lamp() == provisioning::LedAcceptance::Lamp::Off);
        assert(indicator.status(0).output_known && indicator.status(0).output_fault);
    }
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
