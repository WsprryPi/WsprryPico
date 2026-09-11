#pragma once

#include <array>
#include <cstdint>
#include <limits>

namespace wsprrypico::rf {
// Owner-core only, IRQ-masked by the caller. Fixed storage; no per-block log.
// IRQ observation is NOT hardware completion time. Remaining words are sampled
// from the predecessor DMA after installing the successor chain; they exclude
// FIFO/OSR reserve and do not measure analog output or oscillator accuracy.
class RefillMetrics {
  public:
    static constexpr std::uint32_t full_words = 16384;
    struct Reserve {
        std::uint64_t observations = 0, epoch = 0, sequence = 0, observed_ns = 0;
        std::uint32_t remaining_words = 0, total_words = 0;
    };
    struct Snapshot {
        std::uint64_t pairs = 0, unpaired = 0, max_irq_to_ready_ns = 0;
        std::uint64_t running_links = 0, exhausted_links = 0, tail_links = 0;
        std::uint32_t min_remaining_words = std::numeric_limits<std::uint32_t>::max();
        std::uint32_t min_data_remaining_words = std::numeric_limits<std::uint32_t>::max();
        std::uint32_t min_tail_remaining_words = std::numeric_limits<std::uint32_t>::max();
        std::uint64_t invalid_reserves = 0;
        Reserve full, short_block;
    };
    void completed(std::uint64_t epoch, std::uint64_t sequence, std::uint64_t irq_ns) {
        completed_[sequence % 2] = {epoch, sequence, irq_ns, true};
    }
    void ready(std::uint64_t epoch, std::uint64_t sequence, std::uint64_t ready_ns, bool running,
               bool tail, std::uint32_t remaining_words, std::uint32_t predecessor_words) {
        if (!running)
            return; // Initial prefill/short prelaunch DMA are separate coverage.
        ++snapshot_.running_links;
        if (tail)
            ++snapshot_.tail_links;
        if (!remaining_words)
            ++snapshot_.exhausted_links;
        if (remaining_words < snapshot_.min_remaining_words)
            snapshot_.min_remaining_words = remaining_words;
        auto& minimum =
            tail ? snapshot_.min_tail_remaining_words : snapshot_.min_data_remaining_words;
        if (remaining_words < minimum)
            minimum = remaining_words;
        if (!predecessor_words || predecessor_words > full_words ||
            remaining_words > predecessor_words) {
            ++snapshot_.invalid_reserves;
        } else {
            auto& reserve =
                predecessor_words == full_words ? snapshot_.full : snapshot_.short_block;
            // Compare exact fractions without division or floating point. Keep
            // the identity and original length of the worst fractional reserve.
            if (!reserve.observations ||
                std::uint64_t{remaining_words} * reserve.total_words <
                    std::uint64_t{reserve.remaining_words} * predecessor_words) {
                reserve.epoch = epoch;
                reserve.sequence = sequence;
                reserve.observed_ns = ready_ns;
                reserve.remaining_words = remaining_words;
                reserve.total_words = predecessor_words;
            }
            ++reserve.observations;
        }
        auto& completion = completed_[sequence % 2];
        if (sequence < 2 || !completion.valid || completion.epoch != epoch ||
            completion.sequence != sequence - 2 || ready_ns < completion.irq_ns) {
            ++snapshot_.unpaired;
        } else {
            ++snapshot_.pairs;
            const auto elapsed = ready_ns - completion.irq_ns;
            if (elapsed > snapshot_.max_irq_to_ready_ns)
                snapshot_.max_irq_to_ready_ns = elapsed;
        }
        completion.valid = false;
    }
    Snapshot snapshot() const {
        return snapshot_;
    }

  private:
    struct Completion {
        std::uint64_t epoch = 0, sequence = 0, irq_ns = 0;
        bool valid = false;
    };
    std::array<Completion, 2> completed_{};
    Snapshot snapshot_{};
};
} // namespace wsprrypico::rf
