#include "rf/waveform.hpp"

#include <algorithm>
#include <numeric>

namespace wsprrypico::rf {
namespace {

std::optional<std::uint64_t> samples_at(std::uint64_t ns) {
    if (ns > max_duration_ns) {
        return std::nullopt;
    }
    // Reduce before multiplication: bounded even for the maximum frame duration.
    constexpr auto common = std::gcd(sample_rate, 1'000'000'000ULL);
    constexpr auto numerator = sample_rate / common;
    constexpr auto denominator = 1'000'000'000ULL / common;
    const auto samples = (ns * numerator + denominator / 2) / denominator;
    if ((samples * denominator + numerator / 2) / numerator != ns) {
        return std::nullopt;
    }
    return samples;
}

// SRAM tables, constructed once before execution. Single serialized owner.
std::array<WordTable, 4> tables;
bool tables_ready = false;
std::uint32_t oracle_word(std::uint32_t phase, std::uint32_t increment) {
    std::uint32_t word = 0;
    for (unsigned bit = 0; bit < 32; ++bit) {
        word |= (phase >> 31) << bit;
        phase += increment;
    }
    return word;
}
inline std::uint32_t lookup(const WordTable& table, std::uint32_t phase) {
    const auto& bucket = table.buckets[phase >> 22];
    auto word = bucket.word;
    for (auto i = bucket.first; i < bucket.last; ++i) {
        if (phase >= table.boundaries[i].phase)
            word ^= table.boundaries[i].toggle;
    }
    return word;
}

} // namespace

void build_tables(std::array<WordTable, 4>& destination,
                  const std::array<std::uint32_t, 4>& values) {
    for (unsigned tone = 0; tone < 4; ++tone) {
        auto& table = destination[tone];
        for (unsigned bit = 0; bit < 32; ++bit) {
            const auto offset = std::uint32_t{0} - bit * values[tone];
            table.boundaries[2 * bit] = {offset, 1U << bit};
            table.boundaries[2 * bit + 1] = {offset + 0x80000000U, 1U << bit};
        }
        std::sort(table.boundaries.begin(), table.boundaries.end(),
                  [](const auto& a, const auto& b) { return a.phase < b.phase; });
        for (unsigned index = 0; index < 1024; ++index) {
            const auto low = std::uint64_t{index} << 22;
            const auto high = low + (1U << 22);
            auto& bucket = table.buckets[index];
            bucket.word = oracle_word(static_cast<std::uint32_t>(low), values[tone]);
            bucket.first = bucket.last = 0;
            while (bucket.first < 64 && table.boundaries[bucket.first].phase <= low)
                ++bucket.first;
            bucket.last = bucket.first;
            while (bucket.last < 64 && table.boundaries[bucket.last].phase < high)
                ++bucket.last;
        }
    }
}

void prepare_word_tables() {
    if (!tables_ready) {
        build_tables(tables, increments);
        tables_ready = true;
    }
}

std::uint32_t packed_word(std::uint32_t phase, unsigned tone_index) {
    return lookup(tables[tone_index], phase);
}

std::optional<Plan> plan_job(const wtp::Job& job, std::int32_t correction_ppb) {
    if (correction_ppb < -max_correction_ppb || correction_ppb > max_correction_ppb ||
        (correction_ppb != 0 && !job.allow_frequency_adjustment))
        return std::nullopt;
    if (job.job_id.size() != 32 ||
        !std::all_of(job.job_id.begin(), job.job_id.end(),
                     [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
        std::all_of(job.job_id.begin(), job.job_id.end(), [](char c) { return c == '0'; }) ||
        job.profile != "rf-events/1" || (job.mode != "tone" && job.mode != "wspr") ||
        job.events.empty() || job.events.size() > max_events || job.total_duration_ns == 0) {
        return std::nullopt;
    }
    const auto total = samples_at(job.total_duration_ns);
    if (!total || *total == 0) {
        return std::nullopt;
    }
    Plan plan;
    for (unsigned i = 0; i < 4; ++i)
        plan.tone_increments[i] = corrected_increment(i, correction_ppb);
    std::uint64_t previous_ns = 0;
    std::uint64_t previous_sample = 0;
    for (const auto& event : job.events) {
        if (event.offset_ns != previous_ns || event.duration_ns == 0 ||
            event.duration_ns > job.total_duration_ns - previous_ns) {
            return std::nullopt;
        }
        previous_ns += event.duration_ns;
        const auto end = samples_at(previous_ns);
        if (!end || *end <= previous_sample) {
            return std::nullopt;
        }
        std::uint32_t increment = 0, tone_index = 0;
        if (event.rf_on) {
            if (!event.frequency_nhz) {
                return std::nullopt;
            }
            bool found = false;
            for (std::size_t tone = 0; tone < increments.size(); ++tone) {
                const auto requested = base_nhz + tone * spacing_nhz;
                const auto realized = realized_nhz(increments[tone]);
                if (*event.frequency_nhz == realized ||
                    (*event.frequency_nhz == requested && job.allow_frequency_adjustment)) {
                    increment = plan.tone_increments[tone];
                    tone_index = static_cast<std::uint32_t>(tone);
                    found = true;
                    break;
                }
            }
            if (!found) {
                return std::nullopt;
            }
        } else if (event.frequency_nhz) {
            return std::nullopt;
        }
        plan.segments[plan.count++] = {*end, increment, tone_index};
        previous_sample = *end;
    }
    if (previous_ns != job.total_duration_ns) {
        return std::nullopt;
    }
    plan.total_samples = *total;
    return plan;
}

void Waveform::reset(const Plan& plan) {
    if (table_increments_ != plan.tone_increments) {
        build_tables(tables_, plan.tone_increments);
        table_increments_ = plan.tone_increments;
    }
    plan_ = &plan;
    segment_ = 0;
    position_ = 0;
    phase_ = 0;
}

std::uint64_t Waveform::render(std::span<std::uint32_t> output) {
    const auto start = position_;
    std::size_t index = 0;
    unsigned used = 0;
    while (plan_ && position_ < plan_->total_samples && index < output.size()) {
        const auto& segment = plan_->segments[segment_];
        const auto words = used == 0
                               ? static_cast<std::size_t>(std::min<std::uint64_t>(
                                     (segment.end_sample - position_) / 32, output.size() - index))
                               : 0;
        if (words) {
            if (segment.increment) {
                const auto& table = tables_[segment.tone_index];
                auto phase = phase_;
                const auto advance = segment.increment * 32;
                for (std::size_t i = 0; i < words; ++i) {
                    output[index + i] = lookup(table, phase);
                    phase += advance;
                }
                phase_ = phase;
            } else {
                std::fill_n(output.begin() + index, words, 0);
            }
            index += words;
            position_ += words * 32;
        } else {
            if (used == 0)
                output[index] = 0;
            if (segment.increment) {
                output[index] |= (phase_ >> 31) << used;
                phase_ += segment.increment;
            }
            ++position_;
            if (++used == 32) {
                used = 0;
                ++index;
            }
        }
        if (position_ == segment.end_sample)
            ++segment_;
    }
    std::fill(output.begin() + index + (used != 0), output.end(), 0);
    return position_ - start;
}

} // namespace wsprrypico::rf
