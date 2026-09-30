#include "provisioning/pico/gp14_flash_probe.hpp"

#include "hardware/flash.h"
#include "hardware/structs/sio.h"
#include "hardware/structs/timer.h"
#include "pico/flash.h"
#include "pico/time.h"
#include "standalone/pico/flash_layout.hpp"

#include <array>
#include <cstring>

#if !defined(WSPRRY_PICO_GP14_FLASH_PROBE) || !defined(WSPRRY_PICO_GP14_RUNTIME_BUTTON)
#error "Flash probe requires the explicit GP14 runtime test variant"
#endif
#if defined(WSPRRY_PICO_STANDALONE_RF) || WSPRRY_PICO_RF_OUTPUT_DISABLED != 1
#error "Flash probe must never be linked with physical RF"
#endif

namespace wsprrypico::provisioning {
namespace {
constexpr std::uint32_t scratch_offset = 0x3f2000;
static_assert(scratch_offset + FLASH_SECTOR_SIZE == standalone::flash_layout::access_base);
alignas(4) std::array<std::uint8_t, FLASH_SECTOR_SIZE> saved, pattern;
struct Operation {
    const std::uint8_t* bytes;
    bool capture;
    Gp14FlashProbeResult* result;
};

__force_inline std::uint64_t probe_time() {
    std::uint32_t high, low;
    do {
        high = timer_hw->timerawh;
        low = timer_hw->timerawl;
    } while (high != timer_hw->timerawh);
    return (static_cast<std::uint64_t>(high) << 32) | low;
}

void __no_inline_not_in_flash_func(gp14_probe_flash_write)(void* context) {
    const auto& operation = *static_cast<Operation*>(context);
    auto& result = *operation.result;
    const auto start = timer_hw->timerawl;
    if (operation.capture) {
        result.begin_us = probe_time();
        result.low_before = (sio_hw->gpio_in & (1u << 14)) == 0;
    }
    flash_range_erase(scratch_offset, FLASH_SECTOR_SIZE);
    flash_range_program(scratch_offset, operation.bytes, FLASH_SECTOR_SIZE);
    if (operation.capture) {
        result.write_end_us = probe_time();
        result.low_after_write = (sio_hw->gpio_in & (1u << 14)) == 0;
        // Extend the same interrupt-masked safe zone to two seconds so a
        // manually applied jumper can overlap it. PIO/DMA continue sampling.
        // The eight-second watchdog remains active and is never fed here.
        while (static_cast<std::uint32_t>(timer_hw->timerawl - start) < 2'000'000)
            __asm volatile("nop");
        result.low_after = (sio_hw->gpio_in & (1u << 14)) == 0;
        result.end_us = probe_time();
    }
}
} // namespace

Gp14FlashProbeResult run_gp14_flash_probe() {
    Gp14FlashProbeResult result;
    const auto* sector = reinterpret_cast<const std::uint8_t*>(XIP_BASE + scratch_offset);
    std::memcpy(saved.data(), sector, saved.size());
    for (unsigned i = 0; i < pattern.size(); ++i)
        pattern[i] = static_cast<std::uint8_t>(i ^ 0xa5u);
    Operation operation{pattern.data(), true, &result};
    const int write = flash_safe_execute(gp14_probe_flash_write, &operation, 100);
    result.pattern_ok =
        write == PICO_OK && std::memcmp(sector, pattern.data(), pattern.size()) == 0;
    operation = {saved.data(), false, &result};
    const int restore = flash_safe_execute(gp14_probe_flash_write, &operation, 100);
    result.restore_ok = restore == PICO_OK && std::memcmp(sector, saved.data(), saved.size()) == 0;
    result.ok = result.pattern_ok && result.restore_ok;
    return result;
}
} // namespace wsprrypico::provisioning
