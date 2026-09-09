#pragma once
#include <cstdint>
struct watchdog_hw_t {
    std::uint32_t scratch[8];
};
extern watchdog_hw_t* watchdog_hw;
