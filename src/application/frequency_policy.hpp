#pragma once

#include <cstdint>

namespace wsprrypico::application {
// Admission policy, not RF qualification or jurisdiction-specific permission.
// Default amateur bands retain ordinary admission. Unqualified bands require
// explicit opt-in independently of hardware and RF qualification.
enum class FrequencyDisposition { OrdinaryAmateur, UnqualifiedAmateur, NonAmateur };
FrequencyDisposition frequency_disposition(std::uint64_t frequency_nhz);
bool frequency_allowed(std::uint64_t frequency_nhz, bool allow_unqualified_frequency,
                       bool allow_non_amateur_frequency);
} // namespace wsprrypico::application
