// SPDX-License-Identifier: MIT
#include "rf/si5351_job.hpp"

#include <cassert>

using namespace wsprrypico;
int main() {
    rf::si5351::Configuration config{25'000'000,
                                     rf::si5351::Reference::Crystal,
                                     8,
                                     rf::si5351::Output::Clk0,
                                     rf::si5351::Output::Clk2,
                                     2};
    wtp::Job job;
    job.job_id = std::string(32, 'a');
    job.mode = "wspr";
    job.allow_frequency_adjustment = true;
    std::uint64_t previous = 0;
    for (unsigned i = 0; i < 162; ++i) {
        const auto end = (i + 1) * 2'048'000'000ULL / 3;
        assert(job.events.push_back({previous, end - previous, true,
                                     14'097'097'802'734'375ULL + (i % 4) * 1'464'843'750ULL}));
        previous = end;
    }
    assert(job.events.push_back({previous, 1, false, {}}));
    job.total_duration_ns = previous + 1;
    for (auto mode : {"wspr", "tone", "qrss", "fskcw", "dfcw"}) {
        job.mode = mode;
        const auto compiled = rf::si5351::plan_job(config, job, 0, 1'000'000, 0.001L);
        assert(compiled.plan && compiled.error.empty());
        const auto& plan = *compiled.plan;
        assert(plan.synthesis.tone_count == 4 && plan.count == 163);
        assert(plan.digest == wtp::job_digest(job));
        assert(plan.requested_duration_ns == job.total_duration_ns);
        assert(plan.tone[162] == rf::si5351::JobPlan::off);
        for (unsigned i = 0; i < 162; ++i) {
            const auto exact = (i + 1) * 2'048'000'000ULL / 3;
            const auto realized = static_cast<std::uint64_t>(plan.end_us[i]) * 1000;
            assert((realized >= exact ? realized - exact : exact - realized) <= 500);
            assert(plan.tone[i] == i % 4);
        }
    }
    auto vhf = job;
    for (auto& event : vhf.events)
        if (event.frequency_nhz)
            *event.frequency_nhz += 130'393'400'000'000'000ULL;
    const auto high = rf::si5351::plan_job(config, vhf, 0, 1'000'000, 0.001L);
    assert(high.plan && high.plan->synthesis.tone_count == 4);
    for (const auto& tone : high.plan->synthesis.tones())
        assert(tone.pll && tone.multisynth.integer == 6);
    auto invalid = job;
    invalid.events[1].offset_ns++;
    assert(!rf::si5351::plan_job(config, invalid, 0, 1'000'000, 0.001L).plan);
    invalid = job;
    invalid.events[0].frequency_nhz = 144'490'500'000'000'000ULL;
    assert(!rf::si5351::plan_job(config, invalid, 0, 1'000'000, 0.001L).plan);
    invalid = job;
    invalid.events[4].frequency_nhz = 14'098'000'000'000'000ULL;
    assert(!rf::si5351::plan_job(config, invalid, 0, 1'000'000, 0.001L).plan);
    assert(!rf::si5351::plan_job(config, job, 0, 1'000'000'000, 0.001L).plan);
    invalid = job;
    invalid.allow_frequency_adjustment = false;
    assert(!rf::si5351::plan_job(config, invalid, 1000, 1'000'000, 0.001L).plan);
    invalid.mode = "unknown";
    assert(!rf::si5351::plan_job(config, invalid, 0, 1'000'000, 0.001L).plan);
}
