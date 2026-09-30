#pragma once

#include "provisioning/button_diagnostic.hpp"

#include <cstdint>

namespace wsprrypico::provisioning {

// PIO shifts the oldest of eight 1 ms pin samples into bit 7. DMA stores the
// resulting word. Replaying every bit preserves gestures completed while XIP
// and both CPU interrupt streams are unavailable for a flash write.
class ButtonSampleStream {
  public:
    static constexpr std::uint64_t sample_period_us = 1'000;
    static constexpr bool backlog_valid(std::uint64_t produced, std::uint64_t consumed,
                                        std::uint32_t capacity) {
        return produced >= consumed && produced - consumed <= capacity;
    }

    DiagnosticButtonEvents observe_word(std::uint32_t word, unsigned bit) {
        if (bit > 7 || sample_index_ > UINT64_MAX / sample_period_us) {
            fault_ = true;
            return {};
        }
        const auto events =
            button_.observe(sample_index_ * sample_period_us, (word & (1u << (7u - bit))) == 0);
        ++sample_index_;
        fault_ = fault_ || button_.fault();
        return events;
    }

    [[nodiscard]] bool fault() const {
        return fault_;
    }
    [[nodiscard]] bool held() const {
        return button_.held();
    }
    [[nodiscard]] std::uint64_t samples() const {
        return sample_index_;
    }

  private:
    ButtonDiagnostic button_;
    std::uint64_t sample_index_ = 0;
    bool fault_ = false;
};

} // namespace wsprrypico::provisioning
