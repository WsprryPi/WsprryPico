#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {

// Temporary RF-inhibited runtime test only. No address or length is caller supplied.
struct Gp14FlashProbeResult {
    bool ok = false;
    bool pattern_ok = false;
    bool restore_ok = false;
    bool low_before = false;
    bool low_after_write = false;
    bool low_after = false;
    std::uint64_t begin_us = 0;
    std::uint64_t write_end_us = 0;
    std::uint64_t end_us = 0;
};
Gp14FlashProbeResult run_gp14_flash_probe();

} // namespace wsprrypico::provisioning
