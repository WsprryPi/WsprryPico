#pragma once

#include "microchrony.hpp"
#include "time/ntp_diagnostics.hpp"
#include "time/observation.hpp"

namespace wsprrypico::time {
class NtpClient {
  public:
    struct ControlModel {
        std::uint64_t utc_ns = 0, raw_ns = 0, uncertainty_ns = 0, phase_lag_ns = 0;
        std::int32_t rate_ppb = 0, frequency_ppb = 0;
        std::uint32_t rate_uncertainty_ppb = 0;
        bool qualified_input = false, learned = false;
        std::uint64_t generation = 0, selected_sample_raw_ns = 0, selected_epoch = 0;
    };
    explicit NtpClient(ObservationSink& clock);
    bool reference_clock(bool enabled, std::uint64_t now) {
        if (!core_.reference_clock(enabled, now))
            return false;
        if (!enabled)
            clock_.invalidate(ObservationSource::Gps);
        (void)apply(now);
        return true;
    }
    bool reference_observation(microchrony::ReferenceObservation value, std::uint64_t now) {
        const bool accepted = core_.observe_reference(value, now);
        (void)apply(now);
        return accepted;
    }
    bool configure(unsigned slot, std::uint32_t endpoint, std::uint64_t now);
    void online(bool enabled, std::uint64_t now) {
        core_.online(enabled, now);
    }
    void reset_peer(bool invalidate_clock = true);
    void remove(unsigned slot, std::uint64_t now);
    void cancel(unsigned slot = 0);
    void seed_rate(std::int32_t rate, std::uint32_t skew = 2'000'000);
    void clear_seed();
    bool frequency_reference(const std::optional<microchrony::FrequencyReference>&,
                             std::uint64_t now_raw_ns);
    void clear_frequency_reference(std::uint64_t now_raw_ns);
    std::string_view frequency_reference_status(std::uint64_t now) const {
        const auto browser = clock_.browser_frequency_reference_status(now);
        if (!browser.empty())
            return browser;
        const auto state = core_.frequency_reference_state(now);
        return state == microchrony::FrequencyReferenceState::Selected && !arbiter_selected_
                   ? "awaiting_utc"
                   : microchrony::name(state);
    }
    std::optional<std::array<std::uint8_t, 48>> scheduled_request(unsigned slot, std::uint64_t now,
                                                                  std::uint64_t token);
    // Explicit exchange hooks also support the existing host transport bridge.
    std::array<std::uint8_t, 48> request(std::uint64_t now, std::uint64_t token);
    bool receive(std::span<const std::uint8_t> packet, std::uint64_t now, bool discipline = true) {
        return receive(0, packet, now, discipline);
    }
    bool receive(unsigned slot, std::span<const std::uint8_t> packet, std::uint64_t now,
                 bool discipline = true, std::size_t wire_length = 0);
    bool apply(std::uint64_t now);
    bool arbiter_accepted() const {
        return arbiter_selected_;
    }
    bool peer_fresh(std::uint64_t now) const;
    bool peer_recent(std::uint64_t now, std::uint64_t maximum_age) const;
    bool denied() const;
    const ControlModel& control_model() const {
        return control_;
    }
    std::optional<NtpSample> last_sample() const;
    std::optional<NtpSample> sample(unsigned slot) const;
    std::uint64_t last_rtt_ns() const;
    std::optional<std::uint64_t> last_uncertainty_ns() const;
    RateEstimate rate(std::uint64_t now) const;
    std::string learning_json(std::uint64_t now) const;
    std::string observations_json() const;
    std::string history_page(NtpDiagnosticBinding binding, std::string_view request,
                             std::uint64_t now) const;
    std::string packet_page(NtpDiagnosticBinding binding, std::string_view cursor,
                            std::uint64_t now) const;
    unsigned selected_slot(std::uint64_t now) const;
    unsigned selected_slot() const {
        return selected_slot(last_now_);
    }
    microchrony::SourceStatus status(unsigned slot, std::uint64_t now) const {
        return core_.status(slot, now);
    }
    const microchrony::Engine& engine() const {
        return core_;
    }

  private:
    NtpSample convert(unsigned slot, const microchrony::Measurement& measurement) const;
    ObservationSink& clock_;
    microchrony::Engine core_;
    std::array<std::uint64_t, microchrony::source_capacity> epochs_{1, 1, 1, 1};
    ControlModel control_;
    std::uint64_t last_now_ = 0;
    bool packet_accepted_ = false, arbiter_selected_ = false;
    struct PacketRecord {
        std::uint64_t id = 0, epoch = 0, send_ns = 0, receive_ns = 0, token = 0;
        std::uint32_t endpoint = 0, length = 0;
        std::array<std::uint8_t, 48> prefix{};
        unsigned slot = 0;
        microchrony::Rejection rejection = microchrony::Rejection::None;
        bool accepted = false;
    };
    // Independent of the 36 KiB estimator; immutable offered-packet evidence.
    std::array<PacketRecord, 32> packets_{};
    std::array<std::uint64_t, 4> request_ns_{}, request_tokens_{};
    std::uint64_t packet_sequence_ = 0;
};
} // namespace wsprrypico::time
