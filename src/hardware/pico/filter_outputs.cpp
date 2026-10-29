// SPDX-License-Identifier: MIT
#include "hardware/pico/filter_outputs.hpp"

#include "hardware/gpio.h"
namespace wsprrypico::hardware {
bool PicoFilterOutputs::initialize_inactive() {
    if (!valid_)
        return false;
    if (!initialized_) {
        for (unsigned i = 0; i < settings_.output_count; ++i) {
            const auto& o = settings_.outputs[i];
            gpio_init(o.gp);
            gpio_put(o.gp, !o.active_high);
            gpio_set_dir(o.gp, GPIO_OUT);
        }
        initialized_ = true;
    }
    return inactive();
}
bool PicoFilterOutputs::inactive() {
    if (!valid_ || !initialized_)
        return false;
    bool ok = true;
    // Attempt every output even when one fails readback.
    for (unsigned i = 0; i < settings_.output_count; ++i) {
        const auto& o = settings_.outputs[i];
        gpio_put(o.gp, !o.active_high);
        ok = (gpio_get_function(o.gp) == GPIO_FUNC_SIO && gpio_is_dir_out(o.gp) &&
              gpio_get(o.gp) == !o.active_high) &&
             ok;
    }
    return ok;
}
bool PicoFilterOutputs::verify(unsigned index) const {
    if (!valid_ || !initialized_ || index >= settings_.output_count)
        return false;
    for (unsigned i = 0; i < settings_.output_count; ++i) {
        const auto& o = settings_.outputs[i];
        if (gpio_get_function(o.gp) != GPIO_FUNC_SIO || !gpio_is_dir_out(o.gp) ||
            gpio_get(o.gp) != (i == index ? o.active_high : !o.active_high))
            return false;
    }
    return true;
}
bool PicoFilterOutputs::activate(unsigned index) {
    if (!valid_ || !initialized_ || index >= settings_.output_count)
        return false;
    for (unsigned i = 0; i < settings_.output_count; ++i) {
        const auto& other = settings_.outputs[i];
        if (gpio_get_function(other.gp) != GPIO_FUNC_SIO || !gpio_is_dir_out(other.gp) ||
            gpio_get(other.gp) != !other.active_high)
            return false;
    }
    const auto& o = settings_.outputs[index];
    gpio_put(o.gp, o.active_high);
    return verify(index);
}
} // namespace wsprrypico::hardware
