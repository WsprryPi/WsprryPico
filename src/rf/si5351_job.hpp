// SPDX-License-Identifier: MIT
#pragma once
#include "rf/si5351_plan.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::rf::si5351 {
// Complete, bounded and caller-independent local execution data. Event ends
// are rounded from absolute nanoseconds to microseconds, never accumulated.
struct JobPlan {
    static constexpr unsigned maximum_events = 512;
    static constexpr std::uint8_t off = 0xff;
    wtp::PayloadDigest digest{};
    Plan synthesis;
    std::array<std::uint32_t, maximum_events> end_us{};
    std::array<std::uint8_t, maximum_events> tone{};
    unsigned count = 0;
    std::uint64_t requested_duration_ns = 0;
    std::uint64_t minimum_transition_ns = 0;
};
static_assert(sizeof(JobPlan) <= 4096);
struct JobResult {
    std::optional<JobPlan> plan;
    std::string_view error;
};
// The execution adapter declares and must independently qualify its minimum
// transition interval. This pure compiler never programs or enables hardware.
JobResult plan_job(const Configuration&, const wtp::Job&, std::int32_t correction_ppb,
                   std::uint64_t minimum_transition_ns, long double maximum_error_hz);
} // namespace wsprrypico::rf::si5351
