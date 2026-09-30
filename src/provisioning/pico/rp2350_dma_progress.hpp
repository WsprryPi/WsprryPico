#pragma once

#include <cstdint>
#include <optional>

namespace wsprrypico::provisioning {

// RP2350 TRIGGER_SELF reloads COUNT in hardware and continues WRITE_ADDR.
// ENDLESS does not decrement COUNT and cannot be used with this accounting.
class Rp2350DmaProgress {
  public:
    static constexpr std::uint32_t count_mask = 0x0fffffffU;
    static constexpr std::uint32_t self_trigger = 0x10000000U;
    static constexpr std::uint32_t transfer_words = 4096; // 32.768 s at 125 words/s.
    static constexpr std::uint64_t word_period_us = 8'000;
    // Less than one block and the ring lifetime; an unobserved wrap is fatal.
    static constexpr std::uint64_t maximum_gap_us = 8'000'000;

    explicit Rp2350DmaProgress(std::uint64_t start_us = 0) : last_us_(start_us) {}

    std::optional<std::uint64_t> observe(std::uint32_t count, std::uint64_t now_us) {
        const auto remaining = count & count_mask;
        if (fault_ || (count & ~count_mask) != self_trigger || remaining > transfer_words ||
            now_us < last_us_ || now_us - last_us_ > maximum_gap_us) {
            fault_ = true;
            return std::nullopt;
        }
        const auto position = (transfer_words - remaining) % transfer_words;
        const auto delta = (position + transfer_words - position_) % transfer_words;
        // One partial word plus RX FIFO (8) and an in-flight DMA write. This
        // permits a FIFO drain, but rejects a counter reset/backwards jump.
        const auto possible = (now_us - last_us_) / word_period_us + 10;
        if (delta > possible || UINT64_MAX - total_ < delta) {
            fault_ = true;
            return std::nullopt;
        }
        total_ += delta;
        position_ = position;
        last_us_ = now_us;
        return total_;
    }

    [[nodiscard]] std::uint64_t blocks() const {
        return total_ / transfer_words;
    }

  private:
    std::uint64_t total_ = 0;
    std::uint64_t last_us_ = 0;
    std::uint32_t position_ = 0;
    bool fault_ = false;
};

} // namespace wsprrypico::provisioning
