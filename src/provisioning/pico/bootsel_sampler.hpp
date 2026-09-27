#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {
struct BootselSample {
    bool safe = false;
    bool pressed = false;
    std::uint32_t elapsed_us = 0;
    int result = 0;
};

// Call only on core 0 while output is authoritatively inactive. A failed
// flash-safe zone never returns a usable button value.
BootselSample sample_runtime_bootsel();
} // namespace wsprrypico::provisioning
