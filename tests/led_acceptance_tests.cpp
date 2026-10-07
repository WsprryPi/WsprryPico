#include "pico/cyw43_arch.h"
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
