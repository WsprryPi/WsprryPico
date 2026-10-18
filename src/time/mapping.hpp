#pragma once
#include "time/observation.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::time {
// Software UTC frequency/slew support is independent of the RF carrier's
// ±100 ppm correction range. Chrony permits finite phase slews up to 100000 ppm.
inline constexpr std::int32_t utc_max_rate_ppb = 100'000'000;
inline constexpr std::uint32_t utc_max_rate_uncertainty_ppb = 200'000'000;
// Integer rational arithmetic shared by forward projection and alarm inversion.
// No epoch-sized floating point or target-dependent 128-bit arithmetic.
inline bool scale(std::uint64_t value, std::uint64_t numerator, std::uint64_t denominator,
                  std::uint64_t& result, bool ceil = false) {
    constexpr auto limit = std::numeric_limits<std::uint64_t>::max();
    if (!denominator || numerator > 2'000'000'000ULL || denominator > 2'000'000'000ULL)
        return false;
    const auto q = value / denominator, r = value % denominator;
    if (numerator && q > limit / numerator)
        return false;
    const auto product = r * numerator;
    const auto fraction = product / denominator + (ceil && product % denominator != 0);
    const auto whole = q * numerator;
    if (whole > limit - fraction)
        return false;
    result = whole + fraction;
    return true;
}
inline bool elapsed_utc(std::uint64_t raw, std::int32_t rate_ppb, std::uint64_t& utc,
                        bool ceil = false) {
    if (rate_ppb < -utc_max_rate_ppb || rate_ppb > utc_max_rate_ppb)
        return false;
    return scale(raw, std::uint64_t(1'000'000'000LL + rate_ppb), 1'000'000'000, utc, ceil);
}
inline bool project(const wtp::ClockSnapshot& anchor, std::uint64_t raw, std::uint64_t& utc) {
    if (anchor.rate_until_monotonic_ns != UINT64_MAX &&
        anchor.rate_until_monotonic_ns >= anchor.monotonic_now_ns &&
        raw > anchor.rate_until_monotonic_ns) {
        auto boundary = anchor;
        boundary.rate_until_monotonic_ns = UINT64_MAX;
        if (!project(boundary, anchor.rate_until_monotonic_ns, boundary.utc_now_ns))
            return false;
        boundary.monotonic_now_ns = anchor.rate_until_monotonic_ns;
        boundary.rate_ppb = anchor.subsequent_rate_ppb;
        return project(boundary, raw, utc);
    }
    const bool future = raw >= anchor.monotonic_now_ns;
    const auto delta = future ? raw - anchor.monotonic_now_ns : anchor.monotonic_now_ns - raw;
    std::uint64_t elapsed{};
    if (!elapsed_utc(delta, anchor.rate_ppb, elapsed, !future))
        return false;
    if (future) {
        if (elapsed > std::numeric_limits<std::uint64_t>::max() - anchor.utc_now_ns)
            return false;
        utc = anchor.utc_now_ns + elapsed;
    } else {
        if (elapsed > anchor.utc_now_ns)
            return false;
        utc = anchor.utc_now_ns - elapsed;
    }
    return true;
}
inline bool inverse(const wtp::ClockSnapshot& anchor, std::uint64_t utc, std::uint64_t& raw) {
    if (anchor.rate_ppb < -utc_max_rate_ppb || anchor.rate_ppb > utc_max_rate_ppb)
        return false;
    if (anchor.rate_until_monotonic_ns != UINT64_MAX &&
        anchor.rate_until_monotonic_ns >= anchor.monotonic_now_ns) {
        auto boundary = anchor;
        boundary.rate_until_monotonic_ns = UINT64_MAX;
        if (!project(boundary, anchor.rate_until_monotonic_ns, boundary.utc_now_ns))
            return false;
        if (utc > boundary.utc_now_ns) {
            boundary.monotonic_now_ns = anchor.rate_until_monotonic_ns;
            boundary.rate_ppb = anchor.subsequent_rate_ppb;
            return inverse(boundary, utc, raw);
        }
    }
    const bool future = utc >= anchor.utc_now_ns;
    const auto delta = future ? utc - anchor.utc_now_ns : anchor.utc_now_ns - utc;
    std::uint64_t elapsed{};
    // Ceiling for future and floor for past both choose the first raw ns at/after UTC.
    if (!scale(delta, 1'000'000'000, std::uint64_t(1'000'000'000LL + anchor.rate_ppb), elapsed,
               future))
        return false;
    if (future) {
        if (elapsed > std::numeric_limits<std::uint64_t>::max() - anchor.monotonic_now_ns)
            return false;
        raw = anchor.monotonic_now_ns + elapsed;
    } else {
        if (elapsed > anchor.monotonic_now_ns)
            return false;
        raw = anchor.monotonic_now_ns - elapsed;
    }
    return true;
}
inline bool consistent_import(const RateObservation& source, const wtp::ClockSnapshot& model) {
    if (model.sync_age_ns > model.monotonic_now_ns ||
        source.raw_ns != model.monotonic_now_ns - model.sync_age_ns ||
        source.generation != model.model_generation || source.uncertainty_ns > model.uncertainty_ns)
        return false;
    wtp::ClockSnapshot anchor;
    anchor.monotonic_now_ns = source.raw_ns;
    anchor.utc_now_ns = source.utc_ns;
    anchor.rate_ppb = source.rate_ppb;
    std::uint64_t estimate{};
    if (!project(anchor, model.monotonic_now_ns, estimate))
        return false;
    const auto difference =
        estimate >= model.utc_now_ns ? estimate - model.utc_now_ns : model.utc_now_ns - estimate;
    return difference <= model.uncertainty_ns - source.uncertainty_ns;
}
inline bool duration_utc_bound(std::uint64_t raw, const wtp::ClockSnapshot& clock,
                               std::uint64_t& duration) {
    if (clock.rate_ppb < -utc_max_rate_ppb || clock.rate_ppb > utc_max_rate_ppb ||
        clock.subsequent_rate_ppb < -utc_max_rate_ppb ||
        clock.subsequent_rate_ppb > utc_max_rate_ppb ||
        clock.rate_uncertainty_ppb > utc_max_rate_uncertainty_ppb)
        return false;
    const auto upper = std::max<std::int64_t>(
        0, std::int64_t(std::max(clock.rate_ppb, clock.subsequent_rate_ppb)) +
               clock.rate_uncertainty_ppb);
    return scale(raw, 1'000'000'000 + upper, 1'000'000'000, duration, true);
}
inline bool growth(std::uint64_t age, std::uint64_t ppb, std::uint64_t& uncertainty) {
    return scale(age, ppb, 1'000'000'000, uncertainty, true);
}
} // namespace wsprrypico::time
