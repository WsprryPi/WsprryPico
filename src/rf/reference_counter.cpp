// SPDX-License-Identifier: MIT
#include "rf/reference_counter.hpp"

#include <limits>

namespace wsprrypico::rf {
bool ReferenceCounter::reject(std::string_view reason) {
    error_ = reason;
    active_ = false;
    return false;
}
bool ReferenceCounter::begin(CounterSample sample, std::uint64_t maximum_rate,
                             std::uint64_t generation) {
    active_ = false;
    error_ = "invalid_capture";
    // A finite hardware bound keeps all products below uint64 and ensures
    // service gaps can be checked independently of the observed edge count.
    if (!generation || !maximum_rate || maximum_rate > 1'000'000'000ULL ||
        sample.after_ns < sample.before_ns || sample.after_ns - sample.before_ns > 10'000)
        return false;
    first_ = previous_ = sample;
    maximum_rate_ = maximum_rate;
    generation_ = generation;
    edges_ = 0;
    error_ = {};
    active_ = true;
    return true;
}
bool ReferenceCounter::sample(CounterSample value, std::uint64_t generation) {
    if (!active_)
        return false;
    if (generation != generation_)
        return reject("plan_changed");
    if (value.after_ns < value.before_ns || value.before_ns <= previous_.after_ns ||
        value.after_ns - value.before_ns > 10'000)
        return reject("capture_order");
    const auto longest_gap = value.after_ns - previous_.before_ns;
    // Ceiling edge bound + one boundary edge. >=65536 is ambiguous even if
    // the hardware overflow flag is clear: that flag cannot count lost wraps.
    if (longest_gap > 1'000'000'000ULL)
        return reject("counter_service_gap");
    const auto maximum_edges = (longest_gap * maximum_rate_ + 999'999'999) / 1'000'000'000 + 1;
    if (maximum_edges >= 65'536)
        return reject("counter_service_gap");
    const auto difference = static_cast<std::uint16_t>(value.counter - previous_.counter);
    if (difference > maximum_edges)
        return reject("counter_rate_bound");
    if (edges_ > std::numeric_limits<std::uint64_t>::max() - difference)
        return reject("counter_overflow");
    edges_ += difference;
    previous_ = value;
    return true;
}
ReferenceWindow ReferenceCounter::finish() const {
    if (!active_ || previous_.before_ns <= first_.after_ns)
        return {};
    // Use bracket midpoints, and sum rounded-up half-widths as a conservative
    // endpoint allowance. Counting contributes its independent one-edge bound.
    const auto start_width = first_.after_ns - first_.before_ns;
    const auto end_width = previous_.after_ns - previous_.before_ns;
    return {first_.before_ns + start_width / 2,
            previous_.before_ns + end_width / 2,
            edges_,
            (start_width + 1) / 2 + (end_width + 1) / 2,
            generation_,
            true};
}
} // namespace wsprrypico::rf
