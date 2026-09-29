#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {

enum class ButtonAction { None, StopOutput, Restart, OpenSetupAp, Fault };

// Portable policy for a debounced runtime button level. The Pico adapter must
// stop physical output before waiting for release and must not infer a safe
// BOOTSEL sampler from this policy alone.
class ButtonControl {
  public:
    static constexpr std::uint64_t minimum_press_ms = 20;
    static constexpr std::uint64_t long_press_ms = 10'000;

    // shutdown_complete includes the scheduler, JobService and physical engine.
    ButtonAction observe(std::uint64_t now_ms, bool pressed, bool shutdown_complete) {
        if (fault_)
            return ButtonAction::Fault;
        if (!held_) {
            if (!pressed)
                return ButtonAction::None;
            held_ = true;
            pressed_at_ms_ = now_ms;
            return ButtonAction::StopOutput;
        }
        if (now_ms < pressed_at_ms_) {
            fault_ = true;
            return ButtonAction::Fault;
        }
        if (pressed)
            return shutdown_complete ? ButtonAction::None : ButtonAction::StopOutput;
        held_ = false;
        const auto duration = now_ms - pressed_at_ms_;
        if (!shutdown_complete) {
            fault_ = true;
            return ButtonAction::Fault;
        }
        if (duration < minimum_press_ms)
            return ButtonAction::None;
        return duration >= long_press_ms ? ButtonAction::OpenSetupAp : ButtonAction::Restart;
    }

    [[nodiscard]] bool held() const {
        return held_;
    }
    [[nodiscard]] bool fault() const {
        return fault_;
    }

  private:
    std::uint64_t pressed_at_ms_ = 0;
    bool held_ = false;
    bool fault_ = false;
};
} // namespace wsprrypico::provisioning
