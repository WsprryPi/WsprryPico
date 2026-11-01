// SPDX-License-Identifier: MIT
#include "rf/filter_selector.hpp"
namespace wsprrypico::rf {
void FilterCoverage::include(std::uint64_t nominal, std::uint64_t programmed) {
    if (!settings_.required)
        return;
    unsigned paths = 0;
    for (unsigned i = 0; i < settings_.output_count; ++i) {
        bool requested = false, realized = false;
        for (unsigned j = 0; j < settings_.range_count; ++j) {
            const auto& r = settings_.ranges[j];
            if (r.selector != settings_.outputs[i].id)
                continue;
            const auto low = std::uint64_t(r.low_hz) * 1'000'000'000;
            const auto high = std::uint64_t(r.high_hz) * 1'000'000'000;
            requested = requested || (nominal >= low && nominal <= high);
            realized = realized || (programmed > low && programmed < high);
        }
        if (requested && realized)
            paths |= 1U << i;
    }
    mask_ &= paths;
    seen_ = true;
}
int FilterCoverage::selection() const {
    if (!settings_.required)
        return -1;
    if (!seen_ || !mask_ || (mask_ & (mask_ - 1)))
        return -2;
    for (unsigned i = 0; i < settings_.output_count; ++i)
        if (mask_ == (1U << i))
            return int(i);
    return -2;
}
bool FilterSelector::initialize() {
    inactive_ = !outputs_ || outputs_->initialize_inactive();
    initialized_ = inactive_;
    return inactive_;
}
bool FilterSelector::prepare(const wtp::Job& job, const Plan& plan) {
    if (!initialized_ || !inactive_ || job.events.size() != plan.count)
        return false;
    FilterCoverage coverage(settings_);
    for (std::size_t i = 0; i < job.events.size(); ++i)
        if (job.events[i].rf_on && job.events[i].frequency_nhz)
            coverage.include(*job.events[i].frequency_nhz,
                             realized_nhz(plan.segments[i].increment));
    const auto candidate = coverage.selection();
    if (candidate == -2)
        return false;
    selected_ = candidate;
    return true;
}
bool FilterSelector::deactivate() {
    verified_ = false;
    inactive_ =
        outputs_ ? (initialized_ ? outputs_->inactive() : outputs_->initialize_inactive()) : true;
    initialized_ = initialized_ || inactive_;
    return inactive_;
}
bool FilterSelector::activate() {
    if (!required())
        return true;
    if (!initialized_ || !inactive_ || !outputs_ || selected_ < 0)
        return false;
    inactive_ = false;
    verified_ = outputs_->activate(unsigned(selected_));
    return verified_;
}
bool FilterSelector::verify() const {
    return !required() ||
           (outputs_ && verified_ && selected_ >= 0 && outputs_->verify(unsigned(selected_)));
}
} // namespace wsprrypico::rf
