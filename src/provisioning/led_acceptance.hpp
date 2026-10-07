#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {
// Test-image state only. Expiration is local; USB cannot extend an active fault.
class LedAcceptance {
  public:
    bool ap(std::uint64_t now) {
        if (now < ap_until_)
            return false;
        ap_until_ = now + 20'000;
        return true;
    }
    bool fail(std::uint64_t now) {
        if (fault_used_)
            return false;
        fault_used_ = true;
        fault_until_ = now + 15'000;
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
        if (schedule_used_)
            return false;
        schedule_used_ = true;
        return true;
    }
    bool hold() {
        if (hold_used_)
            return false;
        hold_used_ = true;
        return true;
    }

  private:
    std::uint64_t ap_until_ = 0, fault_until_ = 0;
    std::uint32_t rejected_ = 0;
    bool fault_used_ = false, schedule_used_ = false, hold_used_ = false;
};
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
extern LedAcceptance led_acceptance;
#endif
} // namespace wsprrypico::provisioning
