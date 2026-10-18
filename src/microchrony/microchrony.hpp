// SPDX-License-Identifier: MIT
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

// μChrony: a bounded, hardware-independent NTP client. This is an original
// implementation of documented clock-discipline rules, not Chrony source code.
namespace microchrony {
inline constexpr std::size_t source_capacity = 4, sample_capacity = 64;
inline constexpr std::uint64_t second = 1'000'000'000;

struct Config {
    unsigned min_poll = 6, max_poll = 10, poll_target = 8;
    unsigned min_samples = 6, max_samples = 64, min_sources = 1;
    double max_delay = 3, max_delay_deviation_ratio = 10;
    double max_distance = 3, max_jitter = 1, combine_limit = 3;
    double reselect_distance = 0.0001, stratum_weight = 0.001;
    double max_update_skew_ppm = 1000, max_clock_error_ppm = 1;
    double max_drift_ppm = 100000, max_slew_ppm = 83333.333;
    double correction_time_ratio = 3, precision = 0.000001;
    std::uint64_t era_start_utc_ns = 1'735'689'600 * second;
    bool initial_burst = true;
};
enum class Leap : std::uint8_t { Normal, Insert, Delete, Unsynchronized };
enum class Rejection : std::uint8_t {
    None,
    Correlation,
    Packet,
    ServerUnsynchronized,
    KissRate,
    KissDenied,
    Delay,
    DelayDeviation,
    Distance,
    Jitter,
    Falseticker,
    InsufficientSamples,
    Frequency,
    Offline,
};
const char* name(Rejection reason);

struct Measurement {
    std::uint64_t id = 0, send_raw_ns = 0, receive_raw_ns = 0;
    std::uint64_t raw_ns = 0, utc_ns = 0; // Midpoint of the timestamp exchange.
    std::uint64_t server_reference_ns = 0, server_receive_ns = 0, server_send_ns = 0;
    double delay = 0, root_delay = 0, root_dispersion = 0;
    float precision = 0;
    std::uint32_t root_delay_wire = 0, root_dispersion_wire = 0;
    std::uint8_t stratum = 0;
    Leap leap = Leap::Unsynchronized;
    std::int8_t precision_log = 0;
    Rejection rejection = Rejection::None;
};
// Older originals needed only for testing a new fit's residual runs. Retain
// exact timestamp pairs, without another full wire/diagnostic record.
struct RegressionPoint {
    std::uint64_t raw_ns = 0;
    std::int32_t phase_ns = 0;
    float delay = 0;
};
struct Estimate {
    bool valid = false;
    double rate = 0; // UTC seconds per raw second minus one.
    double skew = 0.002, rate_sd = 0.002, offset_sd = 4, jitter = 4;
    double asymmetry = 0, root_delay = 0, root_dispersion = 0;
    std::uint64_t raw_ns = 0, utc_ns = 0, first_raw_ns = 0;
    unsigned samples = 0, runs = 0;
};
struct SourceStatus {
    std::uint32_t endpoint = 0, queries = 0, replies = 0, rejected = 0;
    std::uint64_t generation = 0, last_receive_ns = 0, last_accepted_ns = 0, next_poll_ns = 0;
    unsigned poll = 6, reach = 0;
    bool online = false, selectable = false, selected = false, combined = false;
    bool replace = false;
    Rejection reason = Rejection::Offline;
    double selection_score = 1;
    Estimate estimate;
};
struct Tracking {
    bool synchronized = false;
    Leap leap = Leap::Unsynchronized;
    unsigned selected = source_capacity, combined_sources = 0;
    std::uint64_t raw_ns = 0, utc_ns = 0, source_raw_ns = 0, generation = 0;
    std::uint64_t uncertainty_ns = UINT64_MAX;
    std::int64_t remaining_correction_ns = 0;
    std::int32_t rate_ppb = 0;          // Actual system-clock mapping, including phase slew.
    std::int32_t utc_frequency_ppb = 0; // Frequency correction alone.
    std::uint32_t skew_ppb = 2'000'000;
    double root_delay = 0, root_dispersion = 0;
};
struct Readiness {
    bool synchronized = false, phase_settled = false, rate_settled = false;
    bool error_within_limit = false;
    bool ready() const {
        return synchronized && phase_settled && rate_settled && error_within_limit;
    }
};
struct ReadinessLimits {
    std::uint64_t remaining_correction_ns = 10'000'000;
    std::uint32_t skew_ppb = 1000;
    std::uint64_t clock_error_ns =
        UINT64_MAX; // waitsync-style checks do not imply an absolute bound.
};
Readiness readiness(const Tracking& tracking, ReadinessLimits limits = {});
// corr_rate has units of seconds squared: duration * absolute correction.
// It comes from the typical historical offset error and update interval.
double correction_rate(double offset_sd, double update_interval, double ratio);
double phase_slew(double correction, double corr_rate, double maximum_rate);
struct FrequencyEstimate {
    double rate = 0, skew = 0;
};
// Weighted old/new estimate with innovation spread. Units are seconds/second.
// Repeated, overlapping fits must not shrink error as independent observations.
FrequencyEstimate combine_frequency(FrequencyEstimate previous, FrequencyEstimate measured);
struct SourceEstimate {
    double offset = 0, offset_sd = 0, rate = 0, rate_sd = 0, skew = 0;
    double distance = 0, age = 0;
};
struct CombinedEstimate {
    double offset = 0, offset_sd = 0, rate = 0, rate_sd = 0, skew = 0, frequency_bound = 0;
};
// All offsets refer to one epoch; age is the distance from each fit's epoch.
// The selected source has offset zero. Controller error and the conservative
// all-source frequency bound are deliberately separate.
CombinedEstimate combine_sources(std::span<const SourceEstimate> sources);

// No allocation, sockets, files, wall clock, SDK or operating-system calls.
// One application thread owns the engine. Raw nanoseconds must be monotonic.
class Engine {
  public:
    explicit Engine(Config config = {});
    bool valid_config() const {
        return config_valid_;
    }
    bool configure(unsigned source, std::uint32_t endpoint, std::uint64_t raw_ns);
    void online(bool enabled, std::uint64_t raw_ns);
    void remove(unsigned source, std::uint64_t raw_ns);
    void cancel(unsigned source) {
        if (source < source_capacity)
            sources_[source].pending = false;
    }
    void reset(std::uint64_t raw_ns);
    void seed(std::int32_t utc_frequency_ppb, std::uint32_t skew_ppb = 2'000'000);
    std::optional<std::array<std::uint8_t, 48>>
    request(unsigned source, std::uint64_t raw_ns, std::uint64_t random_token, bool force = false);
    bool receive(unsigned source, std::span<const std::uint8_t> packet, std::uint64_t raw_ns);
    Tracking tracking(std::uint64_t raw_ns) const;
    SourceStatus status(unsigned source, std::uint64_t raw_ns) const;
    std::span<const Measurement> history(unsigned source) const;
    const Measurement* last_measurement(unsigned source) const;
    const Config& config() const {
        return config_;
    }

  private:
    struct Source {
        SourceStatus status;
        std::array<Measurement, sample_capacity> samples{};
        std::array<RegressionPoint, sample_capacity> predecessors{};
        unsigned count = 0, fit_start = 0, burst_left = 0, burst_attempts = 0, poll_score = 0;
        unsigned predecessor_count = 0, runs_count = 0;
        std::uint64_t predecessor_raw_ns = 0, predecessor_utc_ns = 0;
        std::uint64_t send_ns = 0, token = 0, sequence = 0;
        std::optional<Measurement> last;
        bool pending = false, denied = false, synchronized = false;
        double min_delay = 0, asymmetry = 0;
    };
    void fit(Source& source);
    void clear(Source& source);
    void select(std::uint64_t raw_ns, bool score_update = false);
    void discipline(unsigned selected, std::span<const unsigned> combined, std::uint64_t raw_ns);
    double distance(const Source& source, std::uint64_t raw_ns) const;
    double selection_distance(const Source& source, std::uint64_t raw_ns) const;
    std::uint64_t source_utc(const Source& source, std::uint64_t raw_ns) const;
    void advance(std::uint64_t raw_ns);
    void set_poll(Source& source, std::uint64_t raw_ns, std::uint64_t random_token);
    Config config_;
    bool config_valid_ = false, clock_valid_ = false, online_ = true;
    std::array<Source, source_capacity> sources_{};
    std::array<std::uint64_t, source_capacity> used_generation_{};
    std::uint64_t clock_raw_ns_ = 0, clock_utc_ns_ = 0, last_update_ns_ = 0;
    std::uint64_t last_source_raw_ns_ = 0;
    std::uint64_t generation_ = 1;
    double frequency_ = 0, skew_ = 0.002, slew_ = 0, pending_phase_ = 0;
    double frequency_skew_ = 0.002; // Controller state, distinct from the reported coverage bound.
    double root_delay_ = 0, root_dispersion_ = 0;
    unsigned selected_ = source_capacity, combined_count_ = 0;
    Leap leap_ = Leap::Unsynchronized;
};
} // namespace microchrony
