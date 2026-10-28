#pragma once

#include "hardware/pins.hpp"
#include "rf/amplifier_enable.hpp"

namespace wsprrypico::hardware {
class PicoAmplifierOutput final : public rf::EnableOutput {
  public:
    explicit PicoAmplifierOutput(const PinPlan& pins)
        : pin_(pins.amplifier), active_high_(pins.amplifier_active_high),
          valid_(operational(pins)) {}
    bool initialize_inactive() override;
    bool write(bool active) override;
    bool verify_active() const override;

  private:
    std::optional<unsigned> pin_;
    const bool active_high_, valid_;
    bool initialized_ = false;
};
} // namespace wsprrypico::hardware
