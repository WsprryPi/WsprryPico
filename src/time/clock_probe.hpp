// SPDX-License-Identifier: MIT
#pragma once

#include "wtp/job_service.hpp"

#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::time {
// USB-only metrology. This component never observes/sets time or owns RF.
struct ClockProbeRecord {
    wtp::ClockSnapshot rise_before, rise_after;
    std::uint64_t sequence = 0, fall_before_ns = 0, fall_after_ns = 0;
    std::uint64_t ntp_generation = 0, source_epoch = 0, source_raw_ns = 0;
    std::int32_t frequency_ppb = 0;
    std::uint32_t frequency_uncertainty_ppb = 0;
    bool source_sntp = false, disagreement = false;
    bool high_readback = false, low_readback = false, restored = false;
};
struct ClockProbeBinding {
    std::string_view device, boot, firmware, revision;
};
struct ClockProbeGuard {
    bool permitted = false, source_sntp = false, disagreement = false;
    std::uint64_t ntp_generation = 0, source_epoch = 0, source_raw_ns = 0;
    std::int32_t frequency_ppb = 0;
    std::uint32_t frequency_uncertainty_ppb = 0;
};
struct ClockProbeInput {
    bool level = false, output_enabled = false;
    std::uint32_t pad_before = 0, pad_settling = 0, pad_sampling = 0, control_sampling = 0;
    std::uint32_t settle_us = 0;
    std::uint64_t raw_before_ns = 0, raw_after_ns = 0;
};
// Bind a tight physical-edge bracket to an unchanged surrounding UTC model.
// Projection happens outside the GPIO critical section and handles slew ends.
bool bind_probe_edge(ClockProbeRecord&, const wtp::ClockSnapshot& before,
                     const wtp::ClockSnapshot& after, std::uint64_t raw_lower,
                     std::uint64_t raw_upper);
class ClockProbeHardware {
  public:
    virtual ~ClockProbeHardware() = default;
    // Both calls must restore the original pad, mux, latch and direction.
    virtual std::optional<ClockProbeInput> read() = 0;
    virtual void pulse(ClockProbeRecord&) = 0;
};
class ClockProbe {
  public:
    static constexpr unsigned gpio = 22, pulse_us = 1000;
    static constexpr std::uint64_t maximum_pulses = 4096, minimum_interval_ns = 500'000'000;
    static constexpr std::uint64_t maximum_edge_bracket_ns = 50'000;
    static constexpr std::uint64_t raw_resolution_ns = 1000;
    std::string command(std::string_view request, ClockProbeBinding binding,
                        const ClockProbeGuard& guard, std::uint64_t now,
                        ClockProbeHardware& hardware);

  private:
    std::string record_json(ClockProbeBinding) const;
    std::uint64_t sequence_ = 0, last_attempt_ns_ = 0;
    std::optional<ClockProbeRecord> last_;
};
} // namespace wsprrypico::time
