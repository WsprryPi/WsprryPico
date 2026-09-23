#pragma once

#include "time/observation.hpp"
#include "time/sntp.hpp"
#include "time/utc_discipline.hpp"

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::time {
inline constexpr std::uint64_t controller_fixed_uncertainty_ns = 250'000'000ULL;
inline constexpr std::uint64_t controller_challenge_lifetime_ns = 10'000'000'000ULL;
inline constexpr std::uint64_t controller_source_lifetime_ns = 90'000'000'000ULL;
inline constexpr std::uint64_t controller_local_margin_ns = 1'050'999ULL;
inline constexpr std::uint64_t controller_drift_ppb = 50'000ULL;

enum class ControllerTimeCode {
    Ok,
    Invalid,
    WrongDevice,
    AuthenticationRequired,
    Replay,
    Timeout,
    SourceBusy,
    Disagreement,
    Uncertainty,
};
enum class ActiveTimeSource { None, Sntp, Controller, Disagreement };

struct ControllerChallenge {
    ControllerTimeCode code = ControllerTimeCode::Invalid;
    std::string nonce;
    std::uint64_t sampled_monotonic_ns = 0;
    ControllerChallenge() = default;
    ControllerChallenge(ControllerTimeCode value, std::string issued = {},
                        std::uint64_t sampled = 0)
        : code(value), nonce(std::move(issued)), sampled_monotonic_ns(sampled) {}
};
struct ControllerTimeStatus {
    ActiveTimeSource source = ActiveTimeSource::None;
    std::string principal;
    std::uint64_t age_ns = 0;
    std::uint64_t uncertainty_ns = 0;
    bool disagreement = false;
};

class ControllerTimeArbiter final : public ObservationSink {
  public:
    using MonotonicNow = std::uint64_t (*)(void*);
    ControllerTimeArbiter(UtcDiscipline& clock, MonotonicNow now, void* context,
                          std::string device_id)
        : clock_(clock), now_(now), context_(context), device_id_(std::move(device_id)) {}

    ControllerChallenge challenge(std::string_view principal, std::string_view session,
                                  std::string_view requested_device, std::string nonce);
    bool challenge_delivered(std::string_view principal, std::string_view session,
                             std::string_view requested_device, std::string_view nonce);
    void cancel_challenge(std::string_view principal, std::string_view session);
    ControllerTimeCode submit(std::string_view principal, std::string_view session,
                              std::string_view requested_device, std::string_view nonce,
                              std::uint64_t utc_ns);
    bool observe(ObservationSource source, std::uint64_t utc_ns,
                 std::uint64_t sampled_monotonic_ns, std::uint64_t uncertainty_ns,
                 wtp::LeapState leap,
                 std::optional<std::uint64_t> leap_transition_utc_ns = {},
                 std::string_view principal = {}) override;
    void invalidate(ObservationSource source) override;
    ControllerTimeStatus status() const;

  private:
    struct Observation {
        ObservationSource source = ObservationSource::Sntp;
        std::uint64_t utc_ns = 0;
        std::uint64_t monotonic_ns = 0;
        std::uint64_t uncertainty_ns = 0;
        std::string principal;
        bool valid = false;
    };
    struct Pending {
        std::string principal;
        std::string session;
        std::string nonce;
        std::uint64_t started_ns = 0;
        bool live = false;
    };

    bool current_valid(std::uint64_t now) const;
    bool interval(const Observation& observation, std::uint64_t now,
                  std::uint64_t& estimate, std::uint64_t& uncertainty) const;
    bool overlaps(const Observation& left, const Observation& right,
                  std::uint64_t now) const;
    bool accept(const Observation& observation);
    void disagreement(const Observation& observation);
    static ActiveTimeSource label(ObservationSource source);

    UtcDiscipline& clock_;
    MonotonicNow now_;
    void* context_;
    std::string device_id_;
    Pending pending_;
    Observation current_;
    Observation recovery_;
    ActiveTimeSource source_ = ActiveTimeSource::None;
};
} // namespace wsprrypico::time
