#pragma once
#include "encoding/wspr.hpp"
#include "standalone/storage.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::standalone {
class Scheduler {
  public:
    Scheduler(Store& store, wtp::JobService& service);
    void poll();
    bool idle() const;
    std::uint64_t message_lead_ns() const;
    std::optional<std::uint64_t> next_message_start() const;
    std::string message_status() const;
    std::optional<std::uint64_t> next_wspr_start() const;
    bool pause_message();
    bool message_pause_pending() const {
        return message_pause_pending_;
    }
    bool message_recovery_required() const {
        return message_recovery_required_ || (store_.message_in_flight() && !message_job_);
    }
    void message_saved(bool resume = false) {
        message_pause_pending_ = false;
        message_recovery_required_ = false;
        message_error_ = wtp::ErrorCode::None;
        if (resume)
            suspended_ = false;
    }

    bool reset_permitted() const;
    bool suspended() const {
        return suspended_;
    }
    std::size_t last_load_free_before() const {
        return last_load_free_before_;
    }
    std::size_t last_load_free_after() const {
        return last_load_free_after_;
    }
    unsigned last_load_stage() const {
        return last_load_stage_;
    }
    const hardware::PinPlan& active_pins() const {
        return active_pins_;
    }
    rf::AmplifierTiming active_amplifier_timing() const {
        return active_amplifier_timing_;
    }
    const hardware::FilterSettings& active_filters() const {
        return active_filters_;
    }
    std::string save_filters(const hardware::FilterSettings&);
    unsigned active_gpio_drive_ma() const {
        return active_gpio_drive_ma_;
    }
    unsigned active_ntp_timeout_s() const {
        return active_ntp_timeout_s_;
    }
    bool reboot_required() const {
        return reboot_required_;
    }
    // An independently committed network profile is a boot snapshot. Keep its
    // restart latch through subsequent Config saves, preserving STOP and pins.
    void require_network_restart() {
        external_network_restart_required_ = true;
        reboot_required_ = true;
    }
    bool hardware_restart_required() const {
        return pin_restart_required_;
    }
    bool boot_configured() const {
        return boot_configured_;
    }
    bool hardware_application_failed() const {
        return hardware_application_failed_;
    }
    std::string command(std::string_view line);
    std::string status(const wtp::ServiceStatus* observation = nullptr) const;

  private:
    bool poll_message();
    bool finish_message_pause();
    bool prepare_frame(const encoding::WsprFrame& frame, std::uint64_t slot,
                       const std::array<std::uint64_t, 4>& tones);
    void cancel_pair(wtp::ErrorCode reason);
    void poll_pair();
    struct Pair {
        encoding::WsprPlan plan;
        std::uint64_t second_slot, config_sequence, renew_at, anchor_utc, anchor_monotonic,
            anchor_uncertainty;
        wtp::ClockSnapshot mapping;
        std::array<std::uint64_t, 4> tones;
        unsigned frame = 0;
    };
    std::optional<Pair> pair_;
    unsigned last_frame_ = 0, last_frame_count_ = 0;
    std::size_t last_load_free_before_ = 0, last_load_free_after_ = 0;
    unsigned last_load_stage_ = 0;
    wtp::Response request(std::string_view operation, wtp::RequestBody body = {});
    Store& store_;
    wtp::JobService& service_;
    std::uint64_t sequence_ = 0;
    wtp::ErrorCode last_error_ = wtp::ErrorCode::None;
    std::string last_job_;
    std::optional<std::string> message_job_;
    std::string last_message_job_, last_message_result_;
    bool message_pause_pending_ = false, message_recovery_required_ = false;
    wtp::ErrorCode message_error_ = wtp::ErrorCode::None;
    bool reboot_required_ = false, suspended_ = false, pin_restart_required_ = false;
    bool external_network_restart_required_ = false;
    bool boot_configured_ = false;
    bool hardware_application_failed_ = false;
    std::optional<wtp::PayloadDigest> active_network_;
    hardware::PinPlan active_pins_;
    rf::AmplifierTiming active_amplifier_timing_;
    hardware::FilterSettings active_filters_;
    unsigned active_gpio_drive_ma_ = 4;
    unsigned active_ntp_timeout_s_ = default_ntp_timeout_s;
};
} // namespace wsprrypico::standalone
