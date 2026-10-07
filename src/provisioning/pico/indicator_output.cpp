#include "provisioning/pico/indicator_output.hpp"

#include "hardware/gpio.h"
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
#include "pico/time.h"
#include "provisioning/led_acceptance.hpp"
#endif
#include "pico/cyw43_arch.h"

namespace wsprrypico::provisioning {
bool PicoIndicatorOutput::write(bool on) {
    if (pins_.indicator == hardware::PinPlan::Indicator::Disabled)
        return true;
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
    if ((pins_.indicator != hardware::PinPlan::Indicator::External || role_ == Role::Selected) &&
        led_acceptance.reject_on(time_us_64() / 1000ULL, on))
        return false;
#endif
    if (!hardware::operational(pins_))
        return false;
    if (pins_.indicator == hardware::PinPlan::Indicator::External && role_ == Role::Selected) {
        const auto gp = *pins_.indicator_gp;
        if (!initialized_) {
            gpio_init(gp);
            gpio_put(gp, on == pins_.indicator_active_high);
            gpio_set_dir(gp, GPIO_OUT);
            initialized_ = true;
        } else {
            gpio_put(gp, on == pins_.indicator_active_high);
        }
        bool actual = false;
        return read(actual) == 0 && actual == on;
    }
    bool actual = false;
    return cyw43_gpio_set(&cyw43_state, CYW43_WL_GPIO_LED_PIN, on) == 0 &&
           read_onboard(actual) == 0 && actual == on;
}

int PicoIndicatorOutput::read(bool& on) const {
    if (!hardware::operational(pins_) || pins_.indicator == hardware::PinPlan::Indicator::Disabled)
        return -1;
    if (pins_.indicator == hardware::PinPlan::Indicator::External && role_ == Role::Selected) {
        if (!initialized_)
            return -1;
        on = gpio_get(*pins_.indicator_gp) == pins_.indicator_active_high;
        return 0;
    }
    return read_onboard(on);
}

int PicoIndicatorOutput::read_onboard(bool& on) {
    return cyw43_gpio_get(&cyw43_state, CYW43_WL_GPIO_LED_PIN, &on);
}
} // namespace wsprrypico::provisioning
