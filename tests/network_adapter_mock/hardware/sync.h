#pragma once
#include <cstdint>
inline std::uint32_t save_and_disable_interrupts() {
    return 0;
}
inline void restore_interrupts(std::uint32_t) {}
