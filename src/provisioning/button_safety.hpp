#pragma once

#include "provisioning/button_diagnostic.hpp"

namespace wsprrypico::provisioning {

// Owned by the RF worker. GPIO observation only; no output/reset/AP callback.
// The worker uses this sticky request to quiesce its engine independently of
// foreground dispatch. PIO/DMA replay remains the core-0 gesture authority.
class ButtonSafety {
  public:
    bool observe(std::uint64_t now_us, bool pressed) {
        const auto event = policy_.observe(now_us, pressed);
        if (!inhibited_ && (event.request_stop || event.request_reset || policy_.fault())) {
            inhibited_ = true;
            requested_at_us_ = now_us;
            duration_us_ = event.duration_us;
            reset_ = event.request_reset;
            fault_ = policy_.fault();
        }
        return inhibited_;
    }
    [[nodiscard]] bool inhibited() const {
        return inhibited_;
    }
    [[nodiscard]] std::uint64_t requested_at_us() const {
        return requested_at_us_;
    }
    [[nodiscard]] std::uint64_t duration_us() const {
        return duration_us_;
    }
    [[nodiscard]] bool reset() const {
        return reset_;
    }
    [[nodiscard]] bool fault() const {
        return fault_;
    }

  private:
    ButtonDiagnostic policy_;
    std::uint64_t requested_at_us_ = 0, duration_us_ = 0;
    bool inhibited_ = false, reset_ = false, fault_ = false;
};

} // namespace wsprrypico::provisioning
