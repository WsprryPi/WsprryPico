#include "pico/cyw43_arch.h"
#include "provisioning/pico/indicator_output.hpp"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace wsprrypico;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " #x "\n";                                                 \
            std::abort();                                                                          \
        }                                                                                          \
    } while (false)

cyw43_t cyw43_state;
namespace {
std::vector<std::string> calls;
int result = 0;
} // namespace
void gpio_init(unsigned gp) {
    calls.push_back("init " + std::to_string(gp));
}
void gpio_put(unsigned gp, bool value) {
    calls.push_back("put " + std::to_string(gp) + " " + (value ? "1" : "0"));
}
void gpio_set_dir(unsigned gp, bool output) {
    CHECK(output);
    calls.push_back("out " + std::to_string(gp));
}
int cyw43_gpio_set(cyw43_t* state, int pin, bool value) {
    CHECK(state == &cyw43_state && pin == CYW43_WL_GPIO_LED_PIN);
    calls.push_back(value ? "onboard on" : "onboard off");
    return result;
}

int main() {
    hardware::PinPlan pins;
    provisioning::PicoIndicatorOutput onboard(pins);
    CHECK(onboard.write(true));
    result = -1;
    CHECK(!onboard.write(false));
    result = 0;
    CHECK(onboard.write(false));
    CHECK(calls == std::vector<std::string>({"onboard on", "onboard off", "onboard off"}));
    for (const bool active_high : {true, false}) {
        pins.indicator = hardware::PinPlan::Indicator::External;
        pins.indicator_gp = 18;
        pins.indicator_active_high = active_high;
        for (const bool initially_on : {false, true}) {
            calls.clear();
            provisioning::PicoIndicatorOutput external(pins);
            CHECK(external.write(initially_on));
            CHECK(external.write(!initially_on));
            const auto level = initially_on == active_high ? "1" : "0";
            const auto next = initially_on == active_high ? "0" : "1";
            CHECK(calls == std::vector<std::string>({"init 18", std::string("put 18 ") + level,
                                                     "out 18", std::string("put 18 ") + next}));
        }
    }
    for (const auto gp : {2u, 14u, 23u, 29u}) {
        calls.clear();
        pins.indicator_gp = gp;
        provisioning::PicoIndicatorOutput invalid(pins);
        CHECK(!invalid.write(true) && calls.empty());
    }
    calls.clear();
    pins.indicator_gp = 18;
    provisioning::PicoIndicatorOutput operational(
        pins, provisioning::PicoIndicatorOutput::Role::Operational);
    CHECK(operational.write(true) && operational.write(false));
    CHECK(calls == std::vector<std::string>({"onboard on", "onboard off"}));
    calls.clear();
    pins.indicator_gp.reset();
    provisioning::PicoIndicatorOutput missing(pins);
    CHECK(!missing.write(true) && calls.empty());
    pins = {};
    pins.indicator = hardware::PinPlan::Indicator::Disabled;
    provisioning::PicoIndicatorOutput disabled(pins);
    CHECK(disabled.write(true) && disabled.write(false) && calls.empty());
    std::cout << "Pico indicator adapter: checked onboard writes, both polarities, preload, "
                 "onboard cue routing, disabled and invalid allocation passed\n";
}
