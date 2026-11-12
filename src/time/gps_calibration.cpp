// SPDX-License-Identifier: MIT
#include "time/gps_calibration.hpp"

#include "rf/calibration.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <numbers>

namespace wsprrypico::time::gps {
namespace {
std::optional<Calibration> estimate(long double actual, long double nominal,
                                    long double uncertainty, const Observation& end,
                                    std::uint64_t span, std::uint64_t generation) {
    const auto error = (actual / nominal - 1) * 1e9L;
    if (!std::isfinite(error) || !std::isfinite(uncertainty) || uncertainty <= 0 ||
        uncertainty > 100'000 || std::abs(error) > rf::correction_limit_ppb)
        return {};
    return Calibration{std::int32_t(std::llround(error)), std::uint32_t(std::ceil(uncertainty)) + 1,
                       end.raw_ns, span, generation};
}
} // namespace
bool Calibration::fresh(std::uint64_t now, std::uint64_t maximum_age) const {
    return generation && span_ns >= 10 * second && uncertainty_ppb &&
           uncertainty_at(now) <= 100'001 && now >= observed_raw_ns &&
           now - observed_raw_ns <= maximum_age;
}
std::uint32_t Calibration::uncertainty_at(std::uint64_t now) const {
    if (now < observed_raw_ns)
        return UINT32_MAX;
    const auto age = now - observed_raw_ns;
    // Split the interval before multiplication; both terms fit uint64 even at
    // its maximum timestamp. No backward timestamp grants confidence.
    constexpr auto hour = 3600 * second;
    const auto growth = age / hour * 50'000 + (age % hour * 50'000 + hour - 1) / hour;
    return std::uint32_t(
        std::min<std::uint64_t>(UINT32_MAX, std::uint64_t(uncertainty_ppb) + growth));
}
void PpsCalibration::lost() {
    first_.reset();
    previous_.reset();
    first_cycle_.reset();
    first_cycle_observation_.reset();
    // A gap retires acquisition; retained estimates keep their original ages.
}
bool PpsCalibration::observe(const Observation& o, const std::optional<CycleSnapshot>& cycle,
                             long double nominal) {
    if (!o.sequence || o.sequence <= sequence_watermark_ || !o.raw_ns || !o.utc_ns ||
        !o.uncertainty_ns || o.uncertainty_ns > 200'000'000)
        return false;
    sequence_watermark_ = o.sequence;
    if (previous_ && (o.sequence != previous_->sequence + 1 || o.utc_ns <= previous_->utc_ns ||
                      o.utc_ns - previous_->utc_ns != second || o.raw_ns <= previous_->raw_ns ||
                      o.raw_ns - previous_->raw_ns < second - 1'000'000 ||
                      o.raw_ns - previous_->raw_ns > second + 1'000'000))
        lost();
    previous_ = o;
    const auto captured_raw = o.capture_raw_ns ? o.capture_raw_ns : o.raw_ns;
    const bool coherent = cycle && cycle->coherent && cycle->capture_id && cycle->plan_generation &&
                          cycle->raw_ns >= captured_raw &&
                          cycle->raw_ns - captured_raw <= cycle->uncertainty_ns &&
                          cycle->uncertainty_ns <= 1'000'000;
    if (!first_ || o.utc_ns - first_->utc_ns > 60 * second)
        first_ = o;
    const auto span = o.utc_ns - first_->utc_ns;
    if (span >= 10 * second) {
        const auto timing_error =
            static_cast<long double>(first_->uncertainty_ns) + o.uncertainty_ns;
        ++generation_;
        timer_ = estimate(static_cast<long double>(o.raw_ns - first_->raw_ns),
                          static_cast<long double>(span), timing_error / span * 1e9L, o, span,
                          generation_);
    }
    if (span == 60 * second)
        first_ = o;

    // The RF owner's counter session has its own first endpoint. A restart or
    // pause must neither truncate the Pico timer history nor wait for its fit.
    if (coherent && std::isfinite(nominal) && nominal > 0) {
        if (!first_cycle_ || !first_cycle_observation_ ||
            cycle->plan_generation != first_cycle_->plan_generation ||
            cycle->capture_id != first_cycle_->capture_id || cycle->edges <= first_cycle_->edges ||
            cycle->raw_ns <= first_cycle_->raw_ns || o.utc_ns <= first_cycle_observation_->utc_ns ||
            o.utc_ns - first_cycle_observation_->utc_ns > 60 * second) {
            first_cycle_ = cycle;
            first_cycle_observation_ = o;
        } else {
            const auto utc_span = o.utc_ns - first_cycle_observation_->utc_ns;
            if (utc_span >= 10 * second) {
                const auto count = cycle->edges - first_cycle_->edges;
                const auto pps_raw_span = o.raw_ns - first_cycle_observation_->raw_ns;
                const auto count_raw_span = cycle->raw_ns - first_cycle_->raw_ns;
                // Counts are read near PPS, not latched at the electrical edge.
                // Normalize their actual timestamp interval by the PPS-measured
                // raw timer ratio; variable IRQ delivery cannot become TCXO error.
                const auto actual = static_cast<long double>(count) * pps_raw_span /
                                    count_raw_span * 1e9L / utc_span;
                const auto timing_error =
                    (static_cast<long double>(first_cycle_observation_->uncertainty_ns) +
                     o.uncertainty_ns) *
                    1.001L;
                const auto count_error = (static_cast<long double>(first_cycle_->uncertainty_ns) +
                                          cycle->uncertainty_ns) *
                                         1.001L;
                if (pps_raw_span > timing_error && count_raw_span > count_error) {
                    const auto lower = (count - 1.L) * (pps_raw_span - timing_error) /
                                       (count_raw_span + count_error) * 1e9L / utc_span;
                    const auto upper = (count + 1.L) * (pps_raw_span + timing_error) /
                                       (count_raw_span - count_error) * 1e9L / utc_span;
                    const auto bound = std::max(actual - lower, upper - actual) / nominal * 1e9L;
                    ++generation_;
                    synthesizer_ = estimate(actual, nominal, bound, o, utc_span, generation_);
                }
                if (utc_span == 60 * second) {
                    first_cycle_ = cycle;
                    first_cycle_observation_ = o;
                }
            }
        }
    }
    return true;
}
std::optional<std::int32_t> compose_correction(std::int32_t learned, std::int32_t manual) {
    if (std::abs(std::int64_t(learned)) > rf::correction_limit_ppb ||
        std::abs(std::int64_t(manual)) > rf::correction_limit_ppb)
        return {};
    const auto product = std::int64_t(learned) * manual;
    const auto residual = product >= 0 ? (product + 500'000'000) / 1'000'000'000
                                       : -((-product + 500'000'000) / 1'000'000'000);
    const auto value = std::int64_t(learned) + manual + residual;
    if (std::abs(value) > rf::correction_limit_ppb)
        return {};
    return std::int32_t(value);
}
std::optional<SolarPosition> solar_position(const Position& p, std::uint64_t utc) {
    if (!locator(p) || utc < 1'735'689'600ULL * second || utc >= 4'102'444'800ULL * second)
        return {};
    using namespace std::chrono;
    const sys_days date{days{utc / second / 86400}};
    const year_month_day ymd{date};
    const auto day = (date - sys_days{ymd.year() / January / 1}).count() + 1;
    const auto minute = double(utc / second % 86400) / 60;
    constexpr double rad = std::numbers::pi / 180;
    const double gamma = 2 * std::numbers::pi / (ymd.year().is_leap() ? 366 : 365) *
                         (day - 1 + (minute / 60 - 12) / 24);
    const double equation =
        229.18 * (0.000075 + 0.001868 * std::cos(gamma) - 0.032077 * std::sin(gamma) -
                  0.014615 * std::cos(2 * gamma) - 0.040849 * std::sin(2 * gamma));
    const double declination = 0.006918 - 0.399912 * std::cos(gamma) + 0.070257 * std::sin(gamma) -
                               0.006758 * std::cos(2 * gamma) + 0.000907 * std::sin(2 * gamma) -
                               0.002697 * std::cos(3 * gamma) + 0.00148 * std::sin(3 * gamma);
    const double longitude = p.longitude_e7 / 1e7;
    const double latitude = p.latitude_e7 / 1e7 * rad;
    const double hour_angle = ((minute + equation + 4 * longitude) / 4 - 180) * rad;
    const double elevation_sine = std::sin(latitude) * std::sin(declination) +
                                  std::cos(latitude) * std::cos(declination) * std::cos(hour_angle);
    const auto degrees = [](double sine) { return std::asin(std::clamp(sine, -1.0, 1.0)) / rad; };
    const auto center = std::sin(latitude) * std::sin(declination);
    const auto span = std::abs(std::cos(latitude) * std::cos(declination));
    // Solar hour angle partitions the local solar day at its extrema. At
    // exact noon choose evening, at exact midnight morning, including poles.
    const auto angle = std::remainder(hour_angle, 2 * std::numbers::pi);
    return SolarPosition{degrees(elevation_sine), angle < 0 || std::abs(angle) == std::numbers::pi,
                         degrees(center - span), degrees(center + span)};
}
std::optional<bool> daylight(const Position& p, std::uint64_t utc) {
    const auto solar = solar_position(p, utc);
    return solar ? std::optional<bool>(solar->elevation_degrees >= -0.833) : std::nullopt;
}
} // namespace wsprrypico::time::gps
