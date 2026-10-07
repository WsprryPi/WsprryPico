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
    // Hardware pad readback, independent of the controller's cached write state.
    int read(bool& on) const;
    static int read_onboard(bool& on);

  private:
    hardware::PinPlan pins_;
    Role role_;
    bool initialized_ = false;
};
} // namespace wsprrypico::provisioning
