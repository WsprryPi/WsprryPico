#include "provisioning/pico/bootsel_sampler.hpp"

#include "hardware/gpio.h"
#include "hardware/regs/io_qspi.h"
#include "hardware/regs/sio.h"
#include "hardware/structs/io_qspi.h"
#include "hardware/structs/sio.h"
#include "hardware/structs/timer.h"
#include "hardware/structs/watchdog.h"
#include "pico/error.h"
#include "pico/flash.h"
#include "pico/platform.h"
#include "pico/time.h"

namespace wsprrypico::provisioning {
namespace {
#ifndef WSPRRY_PICO_STANDALONE_RF
struct SampleState {
    bool pressed = false;
};

// The flash-safe zone has already stopped flash-using core 1 and disabled
// core-0 IRQs. Keep this callback and every datum it touches in SRAM/registers.
void __no_inline_not_in_flash_func(sample_chip_select)(void* argument) {
    auto& state = *static_cast<SampleState*>(argument);
    constexpr unsigned chip_select = 1;
    const auto before = io_qspi_hw->io[chip_select].ctrl;
    io_qspi_hw->io[chip_select].ctrl = (before & ~IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_BITS) |
                                       (GPIO_OVERRIDE_LOW << IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_LSB);
    for (unsigned delay = 0; delay < 1000; ++delay)
        __asm volatile("nop");
    state.pressed = !(sio_hw->gpio_hi_in & SIO_GPIO_HI_IN_QSPI_CSN_BITS);
    io_qspi_hw->io[chip_select].ctrl = before;
}
#endif

struct GestureState {
    std::uint32_t window_us = 0;
    std::uint32_t duration_us = 0;
    bool valid_press = false;
};

// No calls, constants in flash, division or 64-bit runtime arithmetic may be
// added here. The linked callback must be disassembled before target use.
void __no_inline_not_in_flash_func(capture_chip_select_gesture)(void* argument) {
    auto& state = *static_cast<GestureState*>(argument);
    constexpr unsigned chip_select = 1;
    const auto before = io_qspi_hw->io[chip_select].ctrl;
    io_qspi_hw->io[chip_select].ctrl = (before & ~IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_BITS) |
                                       (GPIO_OVERRIDE_LOW << IO_QSPI_GPIO_QSPI_SS_CTRL_OEOVER_LSB);
    for (unsigned delay = 0; delay < 1000; ++delay)
        __asm volatile("nop");

    const auto start = timer0_hw->timerawl;
    auto last_feed = start;
    auto edge_at = start;
    auto press_at = start;
    bool raw_pressed = !(sio_hw->gpio_hi_in & SIO_GPIO_HI_IN_QSPI_CSN_BITS);
    bool stable_pressed = raw_pressed;
    const bool stale_press = raw_pressed;
    bool finished = stale_press;
    bool window_elapsed = false;
    while (true) {
        const auto now = timer0_hw->timerawl;
        if (now - start >= state.window_us)
            window_elapsed = true;
        // watchdog_enable(8000) is installed by main. This register write is
        // SRAM/register-only. A button held past the window plus two seconds
        // stops feeding; watchdog recovery is safer than returning to XIP
        // with CS still grounded or hanging forever in the safe zone.
        if (now - last_feed >= 1'000'000u && now - start < state.window_us + 2'000'000u) {
            watchdog_hw->load = 8'000'000u;
            last_feed = now;
        }
        const bool pressed = !(sio_hw->gpio_hi_in & SIO_GPIO_HI_IN_QSPI_CSN_BITS);
        if (pressed != raw_pressed) {
            raw_pressed = pressed;
            edge_at = now;
            if (finished && pressed)
                state.valid_press = false;
        }
        if (raw_pressed != stable_pressed && now - edge_at >= 10'000u) {
            stable_pressed = raw_pressed;
            if (stable_pressed) {
                press_at = edge_at;
            } else if (!finished) {
                state.duration_us = edge_at - press_at;
                // Filter mechanical bounce, then accept an ordinary press
                // and release. The user must never time a button hold.
                state.valid_press = state.duration_us >= 20'000u && !window_elapsed;
                finished = true;
            }
        }
        // A late or overlong press is rejected, but the callback must remain
        // in SRAM until release. Returning while CS is grounded is unsafe.
        if ((finished || window_elapsed) && !raw_pressed && !stable_pressed &&
            now - edge_at >= 50'000u)
            break;
    }
    io_qspi_hw->io[chip_select].ctrl = before;
}
} // namespace

BootselSample sample_runtime_bootsel() {
#ifdef WSPRRY_PICO_STANDALONE_RF
    // A held physical BOOTSEL press faulted a target with a flash-reading
    // core 1. The StandaloneRF worker must not sample it at runtime.
    return {false, false, 0, PICO_ERROR_NOT_PERMITTED};
#else
    SampleState state;
    const auto before = time_us_64();
    const int result = flash_safe_execute(sample_chip_select, &state, 5);
    const auto elapsed = time_us_64() - before;
    // An exit timeout can follow an executed callback; it is still unsafe.
    return {result == PICO_OK, result == PICO_OK && state.pressed,
            static_cast<std::uint32_t>(elapsed > UINT32_MAX ? UINT32_MAX : elapsed), result};
#endif
}

BootselGesture capture_runtime_bootsel_gesture(std::uint32_t window_ms) {
    if (window_ms < 1000 || window_ms > 60'000)
        return {false, false, 0, 0, PICO_ERROR_INVALID_ARG};
    GestureState state;
    state.window_us = window_ms * 1000u;
    const auto before = time_us_64();
    const int result = flash_safe_execute(capture_chip_select_gesture, &state, 5);
    const auto elapsed = time_us_64() - before;
    return {result == PICO_OK, result == PICO_OK && state.valid_press, state.duration_us / 1000u,
            static_cast<std::uint32_t>(elapsed > UINT32_MAX ? UINT32_MAX : elapsed), result};
}
} // namespace wsprrypico::provisioning
