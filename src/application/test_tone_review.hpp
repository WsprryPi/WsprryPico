// SPDX-License-Identifier: MIT
#pragma once
#include "standalone/frequency_policy_engine.hpp"

namespace wsprrypico::application {
// Internal assessment values. Authenticated adapters construct Context from
// authoritative boot/configuration/ownership snapshots, never caller flags.
struct TestToneProposal {
    std::uint64_t carrier_hz = 0, duration_ms = 0;
    unsigned proposed_drive_ma = 0;
    hardware::PinPlan::Engine engine = hardware::PinPlan::Engine::Direct;
};
struct TestToneContext {
    hardware::PinPlan boot_pins;
    unsigned boot_drive_ma = 12;
    bool physical_direct = false;
    bool wspr_enabled = false, message_enabled = false;
    bool owned = false, busy = false, faulted = false, maintenance = false;
    bool restart_required = false, other_hardware_pending = false;
    // Native/physical inhibit independent of the projected drive restart.
    bool recovery_inhibited = false;
    std::uint64_t preparation_lead_ns = 0, start_resolution_ns = 1;
    std::optional<hardware::Si5351Settings> boot_si5351;
    bool physical_si5351 = false;
};
enum class TestToneAdmission { Ready, RequiresRestart, Refused };
struct TestToneReview {
    TestToneAdmission admission = TestToneAdmission::Refused;
    std::array<std::string_view, 16> refusals{};
    std::size_t refusal_count = 0;
    std::uint64_t minimum_duration_ms = 1, maximum_duration_ms = 0;
    std::optional<std::uint64_t> requested_nhz, launch_utc_ns, launch_monotonic_ns;
    standalone::FrequencyPolicyEngine::ToneAssessment frequency;
    execution::ErrorCode clock_error = execution::ErrorCode::None;
    // Direct: half an NCO step plus report rounding. Si5351: synthesis error
    // plus report rounding. Both are relative to the corrected target, not RF.
    std::uint64_t quantization_bound_nhz = 0;
};
inline constexpr std::uint64_t test_tone_maximum_duration_ms = 120'000;

TestToneReview review_test_tone(const TestToneProposal&, const TestToneContext&,
                                const standalone::FrequencyPolicyEngine&, const execution::ServiceConfig&,
                                const execution::ClockSnapshot&);
} // namespace wsprrypico::application
