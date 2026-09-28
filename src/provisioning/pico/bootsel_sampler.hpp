#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {
struct BootselGesture {
    bool safe = false;
    bool valid_press = false;
    std::uint32_t duration_ms = 0;
    std::uint32_t elapsed_us = 0;
    int result = 0;
};

// One bounded, blocking gesture window. The flash-safe callback keeps core 1
// locked out, core-0 IRQs disabled and all execution in SRAM until BOOTSEL is
// released. The caller must arrange the user prompt before entering this
// window; network and USB servicing pause while it runs. Not an owner grant.
BootselGesture capture_runtime_bootsel_gesture(std::uint32_t window_ms);
} // namespace wsprrypico::provisioning
