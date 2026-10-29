// SPDX-License-Identifier: MIT
#pragma once
#include "rf/filter_selector.hpp"
namespace wsprrypico::hardware {
class PicoFilterOutputs final : public rf::FilterOutputs {
  public:
    PicoFilterOutputs(const FilterSettings& settings, const PinPlan& pins)
        : settings_(settings), valid_(validate_filters(settings, pins).empty()) {}
    bool initialize_inactive() override;
    bool inactive() override;
    bool activate(unsigned index) override;
    bool verify(unsigned index) const override;

  private:
    const FilterSettings& settings_;
    bool valid_, initialized_ = false;
};
} // namespace wsprrypico::hardware
