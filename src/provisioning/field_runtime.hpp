#pragma once

#include "provisioning/access.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
inline constexpr std::uint64_t softap_fallback_ms = 60'000;
inline constexpr std::uint64_t softap_station_stable_ms = 30'000;
inline constexpr std::uint64_t softap_join_grace_ms = 120'000;

enum class SoftApSurface { BlankReadOnly, ProvisionedPreClock, Normal };

struct SoftApStatus {
    bool requested = false;
    bool ready = false;
    bool no_profile = false;
    bool field_mode = false;
    bool recovery = false;
    bool fallback = false;
    bool join_grace = false;
    std::size_t token_records = 0;
    bool reply_active = false;
};

class SoftApCoordinator {
  public:
    explicit SoftApCoordinator(const AccessStore& access) : access_(access) {}
    void no_profile(bool value) {
        no_profile_ = value;
    }
    void recovery(bool value) {
        recovery_ = value;
    }
    bool request_join_grace(std::uint64_t now_ms);
    void station(bool usable, std::uint64_t now_ms);
    void token_records(std::size_t count) {
        token_records_ = count;
    }
    void reply_active(bool value) {
        reply_active_ = value;
    }
    void ready(bool value) {
        ready_ = value && requested_;
    }
    bool poll(std::uint64_t now_ms);
    SoftApStatus status(std::uint64_t now_ms) const;
    SoftApSurface surface(bool clock_usable) const;

  private:
    bool grace(std::uint64_t now_ms) const;
    const AccessStore& access_;
    bool no_profile_ = false;
    bool recovery_ = false;
    bool station_usable_ = false;
    bool fallback_ = false;
    bool requested_ = false;
    bool ready_ = false;
    bool reply_active_ = false;
    std::size_t token_records_ = 0;
    std::uint64_t station_changed_ms_ = 0;
    std::uint64_t grace_started_ms_ = 0;
    bool station_seen_ = false;
    bool grace_active_ = false;
};

class IndicatorOutput {
  public:
    virtual ~IndicatorOutput() = default;
    virtual bool write(bool on) = 0;
};

enum class IndicatorCode { Ok, Invalid, AuthenticationRequired, Busy, OutputFault };
enum class IndicatorPattern { Off, SoftApReady, Identify };

struct IndicatorStatus {
    IndicatorPattern pattern = IndicatorPattern::Off;
    bool output_on = false;
    bool output_fault = false;
};

class IndicatorController {
  public:
    IndicatorController(IndicatorOutput& output, std::string device_id)
        : output_(output), device_id_(std::move(device_id)) {}
    IndicatorCode identify(std::string_view request_id, std::string_view requested_device,
                           bool authenticated, bool local, std::uint64_t now_ms);
    void softap_ready(bool ready) {
        softap_ready_ = ready;
    }
    void poll(std::uint64_t now_ms);
    IndicatorStatus status(std::uint64_t now_ms) const;

  private:
    bool desired(std::uint64_t now_ms) const;
    IndicatorPattern pattern(std::uint64_t now_ms) const;
    IndicatorOutput& output_;
    std::string device_id_;
    std::string identify_request_;
    std::uint64_t identify_started_ms_ = 0;
    bool identify_active_ = false;
    bool softap_ready_ = false;
    bool output_on_ = false;
    bool output_known_ = false;
    bool output_fault_ = false;
};
} // namespace wsprrypico::provisioning
