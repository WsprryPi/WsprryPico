#pragma once

#include "hardware/pins.hpp"
#include "provisioning/field_runtime.hpp"

namespace wsprrypico::provisioning {
class PicoIndicatorOutput final : public IndicatorOutput {
  public:
    enum class Role { Selected, Operational };
    explicit PicoIndicatorOutput(const hardware::PinPlan& pins = {}, Role role = Role::Selected)
        : pins_(pins), role_(role) {}
    bool write(bool on) override;

  private:
    hardware::PinPlan pins_;
    Role role_;
    bool initialized_ = false;
};
} // namespace wsprrypico::provisioning
