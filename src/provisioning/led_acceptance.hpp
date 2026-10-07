#pragma once

#include "provisioning/field_runtime.hpp"

#include <cstdint>

namespace wsprrypico::provisioning {
// Test-image state only. Faults expire locally; the RF-free lamp check is untimed.
class LedAcceptance {
  public:
    enum class Lamp { Normal, Off, On };
    Lamp lamp() const {
        return lamp_;
    }
    bool lamp_active() const {
        return lamp_ != Lamp::Normal;
    }
    bool poll_lamp(IndicatorController& indicator, std::uint64_t now) const {
        if (!lamp_active())
            return false;
        const bool on = lamp_ == Lamp::On;
        indicator.enabled(on);
        indicator.transmitting(on); // Optical test only, never an RF engine request.
        indicator.poll(now);
        const auto status = indicator.status(now);
        return status.output_known && !status.output_fault && status.output_on == on;
    }
    bool lamp(IndicatorController& indicator, Lamp value, std::uint64_t now) {
        if (value == Lamp::On && (fault_used_ || schedule_used_ || hold_used_))
            return false;
        lamp_ = value == Lamp::Normal ? Lamp::Off : value;
        if (!poll_lamp(indicator, now)) {
            lamp_ = Lamp::Off;
            (void)poll_lamp(indicator, now); // Failed ON must attempt real OFF.
            return false;
        }
        if (value == Lamp::Normal) {
            lamp_ = value;
            indicator.enabled(true);
            indicator.transmitting(false);
            indicator.poll(now);
            const auto status = indicator.status(now);
            return status.output_known && !status.output_fault;
        }
        return true;
    }
    // Cross the held-stop threshold, then release without reset or setup gestures.
    static constexpr std::uint32_t hold_duration_ms = 1'200;
    bool ap(std::uint64_t now) {
        if (lamp_active() || now < ap_until_)
            return false;
        ap_until_ = now + 20'000;
        return true;
    }
    bool fail(std::uint64_t now) {
        if (lamp_active() || fault_used_)
            return false;
        fault_used_ = true;
        fault_until_ = now + 80'000;
        return true;
    }
    bool ap_active(std::uint64_t now) const {
        return now < ap_until_;
    }
    bool reject_on(std::uint64_t now, bool on) {
        if (on && now < fault_until_) {
            ++rejected_;
            return true;
        }
        return false;
    }
    std::uint32_t rejected() const {
        return rejected_;
    }
    bool schedule() {
        if (lamp_active() || schedule_used_)
            return false;
        schedule_used_ = true;
        return true;
    }
    bool hold() {
        if (lamp_active() || hold_used_)
            return false;
        hold_used_ = true;
        return true;
    }

  private:
    Lamp lamp_ = Lamp::Normal;
    std::uint64_t ap_until_ = 0, fault_until_ = 0;
    std::uint32_t rejected_ = 0;
    bool fault_used_ = false, schedule_used_ = false, hold_used_ = false;
};
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
extern LedAcceptance led_acceptance;
#endif
} // namespace wsprrypico::provisioning
