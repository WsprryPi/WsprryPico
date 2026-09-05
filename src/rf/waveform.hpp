#pragma once

#include "wtp/job_service.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>

namespace wsprrypico::rf {

inline constexpr std::uint64_t sample_rate = 150'000'000;
inline constexpr std::uint64_t base_nhz = 3'570'100'000'000'000;
inline constexpr std::uint64_t spacing_nhz = 1'464'843'750;
inline constexpr std::size_t max_events = 162;
inline constexpr std::uint64_t max_duration_ns = 110'592'000'000;
inline constexpr std::size_t block_words = 16'384;
inline constexpr std::uint64_t block_samples = block_words * 32;
inline constexpr std::array<std::uint32_t, 4> increments{102223085, 102223127, 102223169,
                                                         102223211};

// WTP's integer nHz representation, rounded from the exact NCO rational.
constexpr std::uint64_t realized_nhz(std::uint32_t increment) {
    const auto product = sample_rate * increment;
    return (product >> 32) * 1'000'000'000 +
           (((product & 0xffffffffULL) * 1'000'000'000 + (1ULL << 31)) >> 32);
}

struct Segment {
    std::uint64_t end_sample = 0;
    std::uint32_t increment = 0; // Zero means RF off; phase is frozen.
    std::uint32_t reciprocal = 0;
};

struct Plan {
    std::array<Segment, max_events> segments{};
    std::size_t count = 0;
    std::uint64_t total_samples = 0;
};

// Rejects outside the initial four-tone, tone/wspr, sample-aligned study slice.
// Does not mutate a previously accepted plan or interact with an output device.
[[nodiscard]] std::optional<Plan> plan_job(const wtp::Job& job);

class Waveform {
  public:
    // The plan must outlive the generator and remain immutable until reset.
    void reset(const Plan& plan);
    // LSB is the earliest sample. Final word is zero-padded; return valid samples.
    [[nodiscard]] std::uint64_t render(std::span<std::uint32_t> output);
    [[nodiscard]] std::uint64_t position() const {
        return position_;
    }
    [[nodiscard]] std::uint32_t phase() const {
        return phase_;
    }

  private:
    const Plan* plan_ = nullptr;
    std::size_t segment_ = 0;
    std::uint64_t position_ = 0;
    std::uint32_t phase_ = 0;
};

} // namespace wsprrypico::rf
