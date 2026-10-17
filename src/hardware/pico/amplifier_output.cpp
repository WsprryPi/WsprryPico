#include "hardware/pico/amplifier_output.hpp"

#include "hardware/gpio.h"

namespace wsprrypico::hardware {
bool PicoAmplifierOutput::initialize_inactive() {
    if (!valid_)
        return false;
    if (!pin_)
        return true;
    if (!initialized_) {
        // Pinned SDK gpio_init first disables OE, then selects SIO. Preload
        // inactive while input, before enabling output (including active-low).
        gpio_init(*pin_);
        gpio_put(*pin_, !active_high_);
        gpio_set_dir(*pin_, GPIO_OUT);
        initialized_ = true;
    }
    return write(false);
}
bool PicoAmplifierOutput::write(bool active) {
    if (!valid_)
        return false;
    if (!pin_)
        return true;
    if (!initialized_)
        return false;
    const bool level = active == active_high_;
    gpio_put(*pin_, level);
    return gpio_get_function(*pin_) == GPIO_FUNC_SIO && gpio_is_dir_out(*pin_) &&
           gpio_get(*pin_) == level;
}
} // namespace wsprrypico::hardware
