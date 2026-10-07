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
        return true;
    }
    return cyw43_gpio_set(&cyw43_state, CYW43_WL_GPIO_LED_PIN, on) == 0;
}
} // namespace wsprrypico::provisioning
