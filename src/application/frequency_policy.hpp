#pragma once

#include <cstdint>

namespace wsprrypico::application {
// Admission policy, not RF qualification or jurisdiction-specific permission.
// The default amateur bands retain ordinary operation while Phase 14's final
// release gates remain open. Failed and untested bands require explicit opt-in.
enum class FrequencyDisposition { OrdinaryAmateur, UnqualifiedAmateur, NonAmateur };
FrequencyDisposition frequency_disposition(std::uint64_t frequency_nhz);
bool frequency_allowed(std::uint64_t frequency_nhz, bool allow_unqualified_frequency,
                       bool allow_non_amateur_frequency);
} // namespace wsprrypico::application
