#include "provisioning/pico/indicator_fault_fixture.hpp"

#include "pico/cyw43_arch.h"

#if defined(WSPRRY_PICO_STANDALONE_RF) || WSPRRY_PICO_RF_OUTPUT_DISABLED != 1
#error "The indicator fault fixture requires the inhibited target"
#endif

namespace {
std::uint32_t calls = 0, injected = 0, successful_writes = 0;
}

extern "C" int __real_cyw43_gpio_set(cyw43_t* self, int gpio, bool value);
extern "C" int __wrap_cyw43_gpio_set(cyw43_t* self, int gpio, bool value) {
    ++calls;
    // Exactly one driver error; subsequent writes use the real checked driver.
    if (gpio == CYW43_WL_GPIO_LED_PIN && !injected) {
        ++injected;
        return -1;
    }
    const auto result = __real_cyw43_gpio_set(self, gpio, value);
    if (gpio == CYW43_WL_GPIO_LED_PIN && result == 0)
        ++successful_writes;
    return result;
}

namespace wsprrypico::provisioning {
std::uint32_t indicator_fault_fixture_calls() {
    return calls;
}
std::uint32_t indicator_fault_fixture_injected() {
    return injected;
}
std::uint32_t indicator_fault_fixture_successful_writes() {
    return successful_writes;
}
} // namespace wsprrypico::provisioning
