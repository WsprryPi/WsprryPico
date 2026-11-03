// SPDX-License-Identifier: MIT
#pragma once

namespace wsprrypico::time {
// One core-0 capture owner. Register only during peripheral open/close; callers
// bracket operations that can mask interrupts without attributing a late IRQ
// timestamp to the original edge. Nested operations remain one capture gap.
class CaptureGap {
  public:
    using Observer = void (*)(bool);
    static void observer(Observer value) {
        hook_ = value;
    }
    explicit CaptureGap(bool enabled = true) : handler_(enabled ? hook_ : nullptr) {
        if (handler_)
            handler_(true);
    }
    ~CaptureGap() {
        if (handler_)
            handler_(false);
    }
    CaptureGap(const CaptureGap&) = delete;
    CaptureGap& operator=(const CaptureGap&) = delete;

  private:
    inline static Observer hook_ = nullptr;
    Observer handler_;
};
} // namespace wsprrypico::time
