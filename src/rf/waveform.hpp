#pragma once

#include "wtp/job_service.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>

namespace wsprrypico::rf {

#ifndef WSPRRY_PICO_RF_SAMPLE_RATE_HZ
#define WSPRRY_PICO_RF_SAMPLE_RATE_HZ 138000000
#endif
inline constexpr std::uint64_t sample_rate = WSPRRY_PICO_RF_SAMPLE_RATE_HZ;
static_assert(sample_rate == 132'000'000 || sample_rate == 138'000'000 ||
              sample_rate == 150'000'000);
inline constexpr std::uint64_t base_nhz = 3'570'100'000'000'000;
inline constexpr std::uint64_t spacing_nhz = 1'464'843'750;
inline constexpr std::size_t max_events = 162;
inline constexpr std::uint64_t max_duration_ns = 110'592'000'000;
inline constexpr std::size_t block_words = 16'384;
inline constexpr std::uint64_t block_samples = block_words * 32;
inline constexpr auto increments = [] {
    std::array<std::uint32_t, 4> result{};
    for (std::size_t i = 0; i < result.size(); ++i)
        result[i] = ((3'570'100ULL << 32) + i * (375ULL << 24) + sample_rate / 2) / sample_rate;
    return result;
}();

// WTP's integer nHz representation, rounded from the exact NCO rational.
constexpr std::uint64_t realized_nhz(std::uint32_t increment) {
    const auto product = sample_rate * increment;
    return (product >> 32) * 1'000'000'000 +
           (((product & 0xffffffffULL) * 1'000'000'000 + (1ULL << 31)) >> 32);
}

struct Segment {
    std::uint64_t end_sample = 0;
    std::uint32_t increment = 0; // Zero means RF off; phase is frozen.
    std::uint32_t tone_index = 0;
};

struct Boundary {
    std::uint32_t phase, toggle;
};
struct Bucket {
    std::uint32_t word;
    std::uint16_t first, last;
};
struct WordTable {
    std::array<Boundary, 64> boundaries{};
    std::array<Bucket, 1024> buckets{};
};
constexpr std::int32_t max_correction_ppb = 100000;
// Positive error means the source clock runs fast; reduce the NCO increment.
constexpr std::uint32_t corrected_increment(unsigned tone, std::int32_t ppb) {
    if (tone >= increments.size() || ppb < -max_correction_ppb || ppb > max_correction_ppb)
        return 0;
    const auto divisor = static_cast<std::uint64_t>(1000000000LL + ppb);
    return static_cast<std::uint32_t>((std::uint64_t{increments[tone]} * 1000000000 + divisor / 2) /
                                      divisor);
}

struct Plan {
    std::array<std::uint32_t, 4> tone_increments = increments;
    std::array<Segment, max_events> segments{};
    std::size_t count = 0;
    std::uint64_t total_samples = 0;
};

// Rejects outside the initial four-tone, tone/wspr, sample-aligned study slice.
// Does not mutate a previously accepted plan or interact with an output device.
[[nodiscard]] std::optional<Plan> plan_job(const wtp::Job& job, std::int32_t correction_ppb = 0);

// Diagnostic default-increment packer for tone indexes 0..3.
// Call prepare_word_tables before packed_word; independent of Waveform tables.
void prepare_word_tables();
std::uint32_t packed_word(std::uint32_t phase, unsigned tone_index);

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
    std::array<WordTable, 4> tables_{};
    std::array<std::uint32_t, 4> table_increments_{};
    const Plan* plan_ = nullptr;
    std::size_t segment_ = 0;
    std::uint64_t position_ = 0;
    std::uint32_t phase_ = 0;
};

} // namespace wsprrypico::rf
