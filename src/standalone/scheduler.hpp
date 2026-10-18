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
    bool reset_permitted() const;
    bool suspended() const { return suspended_; }
    const hardware::PinPlan& active_pins() const {
        return active_pins_;
    }
    unsigned active_gpio_drive_ma() const {
        return active_gpio_drive_ma_;
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
    std::string status() const;

  private:
    bool prepare_frame(const encoding::WsprFrame& frame, std::uint64_t slot,
                       std::uint32_t base_frequency_hz);
    void cancel_pair(wtp::ErrorCode reason);
    void poll_pair();
    struct Pair {
        encoding::WsprPlan plan;
        std::uint64_t second_slot, config_sequence, renew_at, anchor_utc, anchor_monotonic,
            anchor_uncertainty;
        wtp::ClockSnapshot mapping;
        std::uint32_t base_frequency_hz;
        unsigned frame = 0;
    };
    std::optional<Pair> pair_;
    unsigned last_frame_ = 0, last_frame_count_ = 0;
    wtp::Response request(std::string_view operation, wtp::RequestBody body = {});
    Store& store_;
    wtp::JobService& service_;
    std::uint64_t sequence_ = 0;
    wtp::ErrorCode last_error_ = wtp::ErrorCode::None;
    std::string last_job_;
    bool reboot_required_ = false, suspended_ = false, pin_restart_required_ = false;
    bool external_network_restart_required_ = false;
    bool boot_configured_ = false;
    bool hardware_application_failed_ = false;
    std::optional<wtp::PayloadDigest> active_network_;
    hardware::PinPlan active_pins_;
    unsigned active_gpio_drive_ma_ = 4;
};
} // namespace wsprrypico::standalone
