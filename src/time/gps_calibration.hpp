// SPDX-License-Identifier: MIT
#pragma once
#include "time/gps.hpp"

namespace wsprrypico::time::gps {
struct CycleSnapshot {
    std::uint64_t edges = 0, raw_ns = 0, uncertainty_ns = 0;
    std::uint64_t plan_generation = 0, capture_id = 0;
    bool coherent = false;
};
struct Calibration {
    // Positive means the measured source is fast. Neither value is UTC's
    // mapping rate; converting between those rates requires the reciprocal.
    std::int32_t oscillator_error_ppb = 0;
    std::uint32_t uncertainty_ppb = 0;
    std::uint64_t observed_raw_ns = 0, span_ns = 0, generation = 0;
    // Engineering holdover allowance: 50 ppm of additional frequency error
    // per hour without a new measurement. This is not an oscillator guarantee.
    std::uint32_t uncertainty_at(std::uint64_t now) const;
    bool fresh(std::uint64_t now, std::uint64_t maximum_age_ns) const;
};
class PpsCalibration {
  public:
    // All observations must already have valid PPS-to-UTC association. Count
    // snapshots are the independently owned, uncorrected loopback output.
    bool observe(const Observation&, const std::optional<CycleSnapshot>&,
                 long double loopback_nominal_hz);
    const std::optional<Calibration>& timer() const {
        return timer_;
    }
    const std::optional<Calibration>& synthesizer() const {
        return synthesizer_;
    }
    void lost();

  private:
    std::optional<Observation> first_, previous_, first_cycle_observation_;
    std::optional<CycleSnapshot> first_cycle_;
    std::optional<Calibration> timer_, synthesizer_;
    std::uint64_t sequence_watermark_ = 0, generation_ = 0;
};
// Manual correction is an independent residual trim when automatic learning
// is enabled. Compose the scale factors, then round once; never apply twice.
std::optional<std::int32_t> compose_correction(std::int32_t learned, std::int32_t manual);
// Approximate apparent horizon (solar center -0.833 degrees), using NOAA's
// published solar equations. UTC only; handles polar day/night without a
// fictitious sunrise or sunset event. No terrain or weather correction.
std::optional<bool> daylight(const Position&, std::uint64_t utc_ns);
} // namespace wsprrypico::time::gps
