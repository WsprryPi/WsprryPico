// SPDX-License-Identifier: MIT
#pragma once
#include "rf/reference_measurement.hpp"
#include "rf/si5351_engine.hpp"

namespace wsprrypico::rf::si5351 {
std::string observation_json(const Engine::Observation&, const std::optional<ReferenceMeasurement>&,
                             std::string_view reference_error, std::uint64_t now_raw_ns,
                             std::string_view clock_reference_state = "none",
                             std::uint64_t clock_reference_observed_raw_ns = 0);
}
