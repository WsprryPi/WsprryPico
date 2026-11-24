// SPDX-License-Identifier: MIT
#pragma once
#include "wtp/job_service.hpp"

namespace wsprrypico::wtp {
// Pure native clock/timeline admission shared by ARM and prospective reviews.
// Does not prepare, own, schedule, or observe an RF engine. Callers separately
// validate the job, configuration, ownership, and hardware admission.
ErrorCode assess_arm(std::uint64_t duration_ns, const ArmBody& arm, const ClockSnapshot& now,
                     const ServiceConfig& config, std::uint64_t resolution,
                     std::uint64_t& start_monotonic_ns);
} // namespace wsprrypico::wtp
