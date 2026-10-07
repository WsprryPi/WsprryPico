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
int get_result = 0;
bool onboard_level = false, mismatch = false;
bool levels[30] = {};
} // namespace
void gpio_init(unsigned gp) {
    calls.push_back("init " + std::to_string(gp));
}
void gpio_put(unsigned gp, bool value) {
    levels[gp] = value;
    calls.push_back("put " + std::to_string(gp) + " " + (value ? "1" : "0"));
}
void gpio_set_dir(unsigned gp, bool output) {
    CHECK(output);
    calls.push_back("out " + std::to_string(gp));
}
int cyw43_gpio_set(cyw43_t* state, int pin, bool value) {
    CHECK(state == &cyw43_state && pin == CYW43_WL_GPIO_LED_PIN);
    calls.push_back(value ? "onboard on" : "onboard off");
    if (!result)
        onboard_level = value;
    return result;
}
bool gpio_get(unsigned gp) {
    return mismatch ? !levels[gp] : levels[gp];
}
int cyw43_gpio_get(cyw43_t* state, int pin, bool* value) {
    CHECK(state == &cyw43_state && pin == CYW43_WL_GPIO_LED_PIN);
    if (!get_result)
        *value = mismatch ? !onboard_level : onboard_level;
    return get_result;
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
    bool readback = true;
    CHECK(onboard.read(readback) == 0 && !readback);
    get_result = -7;
    CHECK(!onboard.write(true) && onboard.read(readback) == -7);
    get_result = 0;
    mismatch = true;
    CHECK(!onboard.write(true));
    mismatch = false;
    {
        provisioning::PicoIndicatorOutput output;
        provisioning::IndicatorController controller(output, "DUT");
        rf::IndicatorGate gate;
        CHECK(!gate.request_launch());
        get_result = -7;
        controller.poll_transmit(gate, 0);
        CHECK(!gate.ready() && !controller.status(0).output_known);
        get_result = 0;
        mismatch = true;
        controller.poll_transmit(gate, 1);
        CHECK(!gate.ready());
        mismatch = false;
        controller.poll_transmit(gate, 2);
        CHECK(gate.ready() && onboard_level);
        gate.inactive();
        controller.poll_transmit(gate, 3);
        CHECK(!onboard_level);
    }
    for (const bool active_high : {true, false}) {
        pins.indicator = hardware::PinPlan::Indicator::External;
        pins.indicator_gp = 18;
        pins.indicator_active_high = active_high;
        for (const bool initially_on : {false, true}) {
            calls.clear();
            provisioning::PicoIndicatorOutput external(pins);
            CHECK(external.read(readback) != 0); // Never claim an uninitialized pad.
            CHECK(external.write(initially_on));
            CHECK(external.write(!initially_on));
            const auto level = initially_on == active_high ? "1" : "0";
            const auto next = initially_on == active_high ? "0" : "1";
            CHECK(calls == std::vector<std::string>({"init 18", std::string("put 18 ") + level,
                                                     "out 18", std::string("put 18 ") + next}));
            CHECK(external.read(readback) == 0 && readback == !initially_on);
            mismatch = true;
            CHECK(!external.write(initially_on));
            mismatch = false;
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
    CHECK(disabled.read(readback) != 0);
    std::cout << "Pico indicator adapter: checked onboard writes, both polarities, preload, "
                 "onboard cue routing, disabled and invalid allocation passed\n";
}
