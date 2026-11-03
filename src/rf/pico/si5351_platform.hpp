// SPDX-License-Identifier: MIT
#pragma once
#include "rf/pico/reference_capture.hpp"
#include "rf/pico/si5351_bus.hpp"
#include "rf/si5351_engine.hpp"

#include <atomic>

namespace wsprrypico::rf::si5351 {
// Sole worker owner. The cutoff IRQ only clamps an independently wired gate;
// it never performs I2C or claims that register/physical RF shutdown succeeded.
class PicoExecutionPlatform final : public ExecutionPlatform {
  public:
    PicoExecutionPlatform(const hardware::PinPlan&, const hardware::Si5351Settings&,
                          const hardware::FilterSettings&, PicoBus&, Device&,
                          bool pps_calibration = false);
    bool initialize() override;
    std::uint64_t now_ns() const override;
    bool set_gate(bool active) override;
    bool gate_active_or_unknown() const override;
    bool arm_cutoff(std::uint64_t end_ns) override;
    void cancel_cutoff() override;
    bool pause_reference(std::uint64_t deadline_ns) override;
    void service_reference(bool permitted) override;
    void inhibit_reference() override;
    std::optional<ReferenceMeasurement> reference() const {
        return monitor_.current();
    }
    std::string_view reference_diagnostic() const {
        return monitor_.diagnostic();
    }
    time::gps::CycleSnapshot pps_snapshot() const {
        return capture_.pps_snapshot();
    }

  private:
    static void cutoff(unsigned alarm);
    static std::uint64_t raw_now(void*);
    const hardware::PinPlan pins_;
    const hardware::Si5351Settings settings_;
    const hardware::FilterSettings filters_;
    PicoBus& bus_;
    PicoReferenceCapture capture_;
    ReferenceMonitor monitor_;
    int alarm_ = -1;
    bool gate_initialized_ = false, capture_opened_ = false;
    std::atomic<bool> gate_unknown_{true}, gate_active_{false}, cutoff_expired_{false};
    static PicoExecutionPlatform* instance_;
};
} // namespace wsprrypico::rf::si5351
