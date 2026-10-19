// SPDX-License-Identifier: MIT
#pragma once
#include "time/clock_probe.hpp"

namespace wsprrypico::time {
class PicoClockProbe final : public ClockProbeHardware {
  public:
    explicit PicoClockProbe(const wtp::Clock& clock) : clock_(clock) {}
    std::optional<ClockProbeInput> read() override;
    void pulse(ClockProbeRecord&) override;

  private:
    const wtp::Clock& clock_;
};
} // namespace wsprrypico::time
