#include "provisioning/pico/bootsel_sampler.hpp"

#include "hardware/regs/io_qspi.h"
#include "hardware/regs/sio.h"
#include "hardware/gpio.h"
#include "hardware/structs/io_qspi.h"
#include "hardware/structs/sio.h"
#include "pico/flash.h"
#include "pico/platform.h"
#include "pico/time.h"

namespace wsprrypico::provisioning {
namespace {
struct SampleState {
    bool pressed = false;
};

// The flash-safe zone has already stopped flash-using core 1 and disabled
// core-0 IRQs. Keep this callback and every datum it touches in SRAM/registers.
void __no_inline_not_in_flash_func(sample_chip_select)(void* argument) {
    auto& state = *static_cast<SampleState*>(argument);
    constexpr unsigned chip_select = 1;
    const auto before = io_qspi_hw->io[chip_select].ctrl;
    io_qspi_hw->io[chip_select].ctrl =
        (before & ~IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_BITS) |
        (GPIO_OVERRIDE_LOW << IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_LSB);
    for (unsigned delay = 0; delay < 1000; ++delay)
        __asm volatile("nop");
    state.pressed = !(sio_hw->gpio_hi_in & SIO_GPIO_HI_IN_QSPI_CSN_BITS);
    io_qspi_hw->io[chip_select].ctrl = before;
}
} // namespace

BootselSample sample_runtime_bootsel() {
    SampleState state;
    const auto before = time_us_64();
    const int result = flash_safe_execute(sample_chip_select, &state, 5);
    const auto elapsed = time_us_64() - before;
    // An exit timeout can follow an executed callback; it is still unsafe.
    return {result == PICO_OK, result == PICO_OK && state.pressed,
            static_cast<std::uint32_t>(elapsed > UINT32_MAX ? UINT32_MAX : elapsed), result};
}
} // namespace wsprrypico::provisioning
