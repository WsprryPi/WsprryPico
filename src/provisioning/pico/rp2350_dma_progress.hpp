#pragma once

#include <cstdint>
#include <optional>

namespace wsprrypico::provisioning {

// RP2350 TRANS_COUNT reserves bits 31:28 for the mode. 0xffffffff selects
// endless mode and never decrements; normal mode has a 28-bit finite count.
struct Rp2350DmaProgress {
    static constexpr std::uint32_t transfer_words = 0x0fffffffU;

    static constexpr std::optional<std::uint32_t> produced(std::uint32_t transfer_count) {
        if (transfer_count & ~transfer_words)
            return std::nullopt;
        return transfer_words - transfer_count;
    }
};

} // namespace wsprrypico::provisioning
