#include "rf/waveform.hpp"

#include <algorithm>

namespace wsprrypico::rf {
namespace {

std::optional<std::uint64_t> samples_at(std::uint64_t ns) {
    if (ns > max_duration_ns) {
        return std::nullopt;
    }
    // Exact 150 MHz ratio: three samples per 20 ns. Multiplication is bounded.
    const auto samples = (ns * 3 + 10) / 20;
    if ((samples * 20 + 1) / 3 != ns) {
        return std::nullopt;
    }
    return samples;
}

std::uint32_t mask(unsigned bits) {
    return bits == 32 ? 0xffffffffU : (std::uint32_t{1} << bits) - 1;
}

} // namespace

std::optional<Plan> plan_job(const wtp::Job& job) {
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
        std::uint32_t increment = 0;
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
                    increment = increments[tone];
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
        plan.segments[plan.count++] = {
            *end, increment, increment ? static_cast<std::uint32_t>((1ULL << 32) / increment) : 0};
        previous_sample = *end;
    }
    if (previous_ns != job.total_duration_ns) {
        return std::nullopt;
    }
    plan.total_samples = *total;
    return plan;
}

void Waveform::reset(const Plan& plan) {
    plan_ = &plan;
    segment_ = 0;
    position_ = 0;
    phase_ = 0;
}

std::uint64_t Waveform::render(std::span<std::uint32_t> output) {
    const auto start = position_;
    for (auto& word : output) {
        word = 0;
        unsigned used = 0;
        while (plan_ && position_ < plan_->total_samples && used < 32) {
            const auto& segment = plan_->segments[segment_];
            auto run = static_cast<unsigned>(
                std::min<std::uint64_t>(32 - used, segment.end_sample - position_));
            if (segment.increment != 0) {
                // ceil(distance / increment), using reciprocal multiply plus one correction.
                // distance-1 < 2^31; the floor reciprocal underestimates by at most one.
                const auto numerator = 0x7fffffffU - (phase_ & 0x7fffffffU);
                auto quotient = static_cast<std::uint32_t>(
                    (static_cast<std::uint64_t>(numerator) * segment.reciprocal) >> 32);
                quotient += numerator - quotient * segment.increment >= segment.increment;
                run = std::min(run, static_cast<unsigned>(quotient + 1));
                if ((phase_ & 0x80000000U) != 0) {
                    word |= mask(run) << used;
                }
                phase_ += segment.increment * run;
            }
            position_ += run;
            used += run;
            if (position_ == segment.end_sample) {
                ++segment_;
            }
        }
    }
    return position_ - start;
}

} // namespace wsprrypico::rf
