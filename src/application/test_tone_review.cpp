// SPDX-License-Identifier: MIT
#include "application/test_tone_review.hpp"

#include "wtp/arm_admission.hpp"

namespace wsprrypico::application {
TestToneReview review_test_tone(const TestToneProposal& proposal, const TestToneContext& context,
                                const standalone::FrequencyPolicyEngine& policy,
                                const wtp::ServiceConfig& limits, const wtp::ClockSnapshot& clock) {
    constexpr std::uint64_t millisecond = 1'000'000, second = 1'000'000'000;
    TestToneReview result;
    const auto refuse = [&](std::string_view reason) {
        // All callers below are statically bounded to fewer than 16 reasons.
        if (result.refusal_count < result.refusals.size())
            result.refusals[result.refusal_count++] = reason;
    };
    result.maximum_duration_ms =
        std::min({test_tone_maximum_duration_ms, limits.max_job_duration_ns / millisecond,
                  rf::max_duration_ns / millisecond});
    if (!standalone::valid_gpio_drive(proposal.proposed_drive_ma))
        refuse("invalid_gpio_drive");
    if (!standalone::valid_gpio_drive(context.boot_drive_ma))
        refuse("invalid_boot_drive");
    if (!context.physical_direct || context.boot_pins.engine != hardware::PinPlan::Engine::Direct)
        refuse("inactive_direct_engine");
    if (!context.boot_pins.rf || !hardware::operational(context.boot_pins) ||
        !hardware::validate(context.boot_pins).valid())
        refuse("invalid_boot_pins");
    if (context.wspr_enabled || context.message_enabled)
        refuse("native_schedules_enabled");
    if (context.owned || context.busy)
        refuse("owned_or_busy");
    if (context.faulted || context.recovery_inhibited)
        refuse("output_recovery_required");
    if (context.maintenance)
        refuse("maintenance_pending");
    if (context.other_hardware_pending)
        refuse("other_hardware_pending_restart");
    if (std::find(limits.supported_modes.begin(), limits.supported_modes.end(), "tone") ==
        limits.supported_modes.end())
        refuse("tone_not_supported");
    if (proposal.carrier_hz == 0 || proposal.carrier_hz > UINT64_MAX / second)
        refuse("invalid_carrier");
    else {
        result.requested_nhz = proposal.carrier_hz * second;
        result.frequency = policy.assess_direct_tone(*result.requested_nhz);
        if (!result.frequency.refusal.empty())
            refuse(result.frequency.refusal);
        const auto outside_service = [&](std::uint64_t frequency) {
            return frequency < limits.minimum_frequency_nhz ||
                   frequency > limits.maximum_frequency_nhz;
        };
        if (outside_service(*result.requested_nhz) ||
            (result.frequency.programmed_nhz && outside_service(*result.frequency.programmed_nhz)))
            refuse("native_frequency_out_of_range");
        if (result.frequency.programmed_nhz) {
            constexpr auto numerator = rf::sample_rate * second;
            constexpr auto denominator = 2ULL * (1ULL << 32);
            result.quantization_bound_nhz = (numerator + denominator - 1) / denominator + 1;
        }
    }
    if (proposal.duration_ms == 0 || proposal.duration_ms > result.maximum_duration_ms)
        refuse("invalid_duration");
    else {
        // Review a near-term whole-UTC-second native launch, not a client time
        // or a reservation. The real ARM path shares the same clock checker.
        const auto lead = std::max(context.preparation_lead_ns, limits.minimum_arm_lead_ns);
        if (lead > UINT64_MAX - clock.utc_now_ns ||
            clock.utc_now_ns + lead > UINT64_MAX - (second - 1))
            refuse("launch_time_overflow");
        else {
            const auto earliest = clock.utc_now_ns + lead;
            const auto launch = ((earliest + second - 1) / second) * second;
            std::uint64_t monotonic = 0;
            result.clock_error = wtp::assess_arm(
                proposal.duration_ms * millisecond, {"", launch, limits.maximum_arm_uncertainty_ns},
                clock, limits, context.start_resolution_ns, monotonic);
            if (result.clock_error == wtp::ErrorCode::None) {
                result.launch_utc_ns = launch;
                result.launch_monotonic_ns = monotonic;
            } else
                refuse("clock_admission_refused");
        }
    }
    if (result.refusal_count == 0)
        result.admission =
            context.restart_required || proposal.proposed_drive_ma != context.boot_drive_ma
                ? TestToneAdmission::RequiresRestart
                : TestToneAdmission::Ready;
    return result;
}
} // namespace wsprrypico::application
