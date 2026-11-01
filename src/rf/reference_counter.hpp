// SPDX-License-Identifier: MIT
#pragma once
#include "rf/reference_measurement.hpp"

namespace wsprrypico::rf {
struct CounterSample {
    std::uint16_t counter = 0;
    // Bracket the peripheral read with raw monotonic timestamps. A sample
    // outside its bracket, a clock jump, or an excessive gap fails closed.
    std::uint64_t before_ns = 0, after_ns = 0;
};
class ReferenceCounter {
  public:
    // The bound must come from the capture hardware, not the configured input
    // frequency. Otherwise an over-frequency signal could hide multiple wraps.
    bool begin(CounterSample, std::uint64_t hardware_maximum_edges_per_second,
               std::uint64_t plan_generation);
    bool sample(CounterSample, std::uint64_t plan_generation);
    ReferenceWindow finish() const;
    std::string_view error() const {
        return error_;
    }

  private:
    bool reject(std::string_view);
    CounterSample first_, previous_;
    std::uint64_t maximum_rate_ = 0, generation_ = 0, edges_ = 0;
    bool active_ = false;
    std::string_view error_ = "not_started";
};
} // namespace wsprrypico::rf
