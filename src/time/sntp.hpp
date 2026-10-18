#pragma once
// Compatibility include for existing host-side transport adapters. All NTP
// measurement, selection and clock discipline is implemented by μChrony.
#include "time/ntp_client.hpp"
#include "time/utc_discipline.hpp"
namespace wsprrypico::time {
using Sntp = NtpClient;
inline constexpr std::uint64_t standalone_max_uncertainty_ns = 500'000'000ULL;
inline constexpr std::uint64_t sntp_min_utc_ns = 1'735'689'600'000'000'000ULL;
inline constexpr std::uint64_t sntp_max_utc_ns = 4'102'444'800'000'000'000ULL;
}
