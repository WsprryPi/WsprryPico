// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/filter_settings.hpp"
#include "rf/waveform.hpp"

namespace wsprrypico::rf {
// Incremental intersection of the paths covering every nominal/programmed point.
// Programmed NCO values carry a conservative 1 nHz rounding guard.
class FilterCoverage {
  public:
    explicit FilterCoverage(const hardware::FilterSettings& settings) : settings_(settings) {}
    void include(std::uint64_t nominal, std::uint64_t programmed);
    int selection() const;

  private:
    const hardware::FilterSettings& settings_;
    unsigned mask_ = 31;
    bool seen_ = false;
};
class FilterOutputs {
  public:
    virtual ~FilterOutputs() = default;
    virtual bool initialize_inactive() = 0;
    virtual bool inactive() = 0;
    virtual bool activate(unsigned index) = 0;
    virtual bool verify(unsigned index) const = 0;
};
class FilterSelector {
  public:
    FilterSelector(const hardware::FilterSettings& settings, FilterOutputs* outputs)
        : settings_(settings), outputs_(outputs) {}
    bool initialize();
    bool prepare(const wtp::Job&, const Plan&);
    bool deactivate();
    bool activate();
    bool verify() const;
    bool required() const {
        return settings_.required;
    }
    const hardware::FilterSettings& settings() const {
        return settings_;
    }
    std::uint64_t preparation_ns() const {
        return settings_.preparation_ns();
    }
    std::uint64_t release_ns() const {
        return std::uint64_t(settings_.release_ms) * 1'000'000;
    }
    std::uint64_t settle_ns() const {
        return std::uint64_t(settings_.settle_ms) * 1'000'000;
    }
    bool output_active_or_unknown() const {
        return !inactive_;
    }
    int observation() const {
        return inactive_                     ? -1
               : verified_ && selected_ >= 0 ? int(settings_.outputs[selected_].id)
                                             : -2;
    }

  private:
    const hardware::FilterSettings& settings_;
    FilterOutputs* outputs_;
    int selected_ = -1;
    bool initialized_ = false, inactive_ = false, verified_ = false;
};
} // namespace wsprrypico::rf
