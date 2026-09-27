#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {
struct BootselSample {
    bool safe = false;
    bool pressed = false;
    std::uint32_t elapsed_us = 0;
    int result = 0;
};

struct BootselGesture {
    bool safe = false;
    bool valid_press = false;
    std::uint32_t duration_ms = 0;
    std::uint32_t elapsed_us = 0;
    int result = 0;
};

// Call only on core 0 in the RF-inhibited, core-1-absent image while output is
// authoritatively inactive. The StandaloneRF worker build refuses sampling.
// A failed flash-safe zone never returns a usable button value.
BootselSample sample_runtime_bootsel();

// One bounded, blocking gesture window. The flash-safe callback keeps core 1
// locked out, core-0 IRQs disabled and all execution in SRAM until BOOTSEL is
// released. The caller must arrange the user prompt before entering this
// window; network and USB servicing pause while it runs. Not an owner grant.
BootselGesture capture_runtime_bootsel_gesture(std::uint32_t window_ms);
} // namespace wsprrypico::provisioning
