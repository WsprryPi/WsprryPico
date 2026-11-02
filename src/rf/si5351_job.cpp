// SPDX-License-Identifier: MIT
#include "rf/si5351_job.hpp"

#include <algorithm>
#include <cmath>

namespace wsprrypico::rf::si5351 {
JobResult plan_job(const Configuration& configuration, const wtp::Job& job, std::int32_t correction,
                   std::uint64_t minimum_transition, long double maximum_error) {
    if (job.job_id.size() != 32 ||
        !std::all_of(job.job_id.begin(), job.job_id.end(),
                     [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
        std::all_of(job.job_id.begin(), job.job_id.end(), [](char c) { return c == '0'; }) ||
        job.profile != "rf-events/1" ||
        (job.mode != "tone" && job.mode != "wspr" && job.mode != "qrss" && job.mode != "fskcw" &&
         job.mode != "dfcw") ||
        !job.events.valid() || job.events.empty() || job.events.size() > JobPlan::maximum_events ||
        !job.total_duration_ns || job.total_duration_ns > 3'600'000'000'000ULL ||
        minimum_transition < 1000 || minimum_transition > 1'000'000'000 ||
        (correction && !job.allow_frequency_adjustment))
        return {{}, "invalid_job_or_transition_policy"};
    JobPlan result;
    result.requested_duration_ns = job.total_duration_ns;
    result.minimum_transition_ns = minimum_transition;
    std::array<std::uint64_t, Plan::maximum_tones> frequencies{};
    unsigned tones = 0;
    std::uint64_t previous = 0;
    std::uint32_t previous_us = 0;
    for (const auto& event : job.events) {
        if (event.offset_ns != previous || !event.duration_ns ||
            event.duration_ns > job.total_duration_ns - previous ||
            (event.rf_on != event.frequency_nhz.has_value()))
            return {{}, "invalid_event"};
        const bool terminal_off = &event == &job.events.back() && !event.rf_on;
        if (event.duration_ns < minimum_transition && !terminal_off)
            return {{}, "transition_interval"};
        previous += event.duration_ns;
        const auto end = static_cast<std::uint32_t>((previous + (terminal_off ? 999 : 500)) / 1000);
        if (end <= previous_us && !terminal_off)
            return {{}, "collapsed_event"};
        auto selected = JobPlan::off;
        if (event.rf_on) {
            auto found =
                std::find(frequencies.begin(), frequencies.begin() + tones, *event.frequency_nhz);
            if (found == frequencies.begin() + tones) {
                if (tones == frequencies.size())
                    return {{}, "tone_limit"};
                frequencies[tones++] = *event.frequency_nhz;
            }
            selected = static_cast<std::uint8_t>(found - frequencies.begin());
        }
        // A sub-us terminal off marker may collapse after an already-off tail.
        // The engine still closes its gate at the preceding RF event boundary.
        if (end > previous_us) {
            result.end_us[result.count] = end;
            result.tone[result.count++] = selected;
        }
        previous_us = end;
    }
    if (previous != job.total_duration_ns || !tones || !result.count)
        return {{}, "incomplete_job"};
    auto synthesis =
        plan(configuration, std::span(frequencies).first(tones), correction, maximum_error);
    if (!synthesis.plan)
        return {{}, synthesis.error};
    if (!job.allow_frequency_adjustment)
        for (const auto& tone : synthesis.plan->tones())
            if (std::fabs(tone.achieved_hz - tone.requested_nhz / 1'000'000'000.L) >= 0.5e-9L)
                return {{}, "frequency_adjustment_required"};
    result.synthesis = *synthesis.plan;
    result.digest = wtp::job_digest(job);
    return {std::move(result), {}};
}
} // namespace wsprrypico::rf::si5351
