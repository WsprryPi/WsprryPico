#include "time/ntp_filter.hpp"

#include "time/mapping.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <cstdlib>
#include <limits>

namespace wsprrypico::time {
namespace {
constexpr std::uint64_t billion = 1'000'000'000;
// Outward-rounded slope interval; source accuracy and asymmetry stay in it.
bool interval(const NtpSample& a, const NtpSample& b, std::int64_t& low, std::int64_t& high) {
    if (b.raw_ns <= a.raw_ns || b.utc_ns <= a.utc_ns)
        return false;
    const auto dm = b.raw_ns - a.raw_ns, du = b.utc_ns - a.utc_ns;
    if (dm > 7'200 * billion || dm < billion)
        return false;
    const auto magnitude = du > dm ? du - dm : dm - du;
    if (magnitude > 3 * billion || a.uncertainty_ns > 500'000'000 || b.uncertainty_ns > 500'000'000)
        return false;
    const auto difference = du >= dm ? std::int64_t(magnitude) : -std::int64_t(magnitude);
    const auto uncertainty = std::int64_t(a.uncertainty_ns + b.uncertainty_ns);
    const auto divisor = std::int64_t(dm);
    const auto lower = (difference - uncertainty) * std::int64_t(billion);
    const auto upper = (difference + uncertainty) * std::int64_t(billion);
    low = lower / divisor - (lower < 0 && lower % divisor != 0);
    high = upper / divisor + (upper > 0 && upper % divisor != 0);
    return true;
}
} // namespace
void NtpFilter::reset() {
    count_ = next_ = history_count_ = 0;
    ++generation_;
    rate_ = {};
    rate_.generation = generation_;
}
bool NtpFilter::add(const NtpSample& sample) {
    if (!sample.id || !sample.epoch || sample.raw_ns < sample.send_ns ||
        sample.raw_ns - sample.send_ns > billion || sample.rtt_ns > billion ||
        sample.uncertainty_ns > 500'000'000 || sample.utc_ns < 1'735'689'600 * billion ||
        sample.utc_ns >= 4'102'444'800 * billion)
        return false;
    if (history_count_ && sample.epoch != history_[history_count_ - 1].epoch)
        reset();
    if (history_count_) {
        const auto& last = history_[history_count_ - 1];
        if (sample.id <= last.id || sample.raw_ns <= last.raw_ns)
            return false;
        if (sample.epoch != last.epoch || sample.raw_ns - last.raw_ns > ntp_fresh_ns)
            reset();
    }
    if (history_count_ >= 1) {
        const auto& last = history_[history_count_ - 1];
        std::uint64_t elapsed{};
        const auto dm = sample.raw_ns - last.raw_ns;
        if (!elapsed_utc(dm, 0, elapsed) || last.utc_ns > UINT64_MAX - elapsed)
            return false;
        const auto expected = last.utc_ns + elapsed;
        const auto diff =
            sample.utc_ns > expected ? sample.utc_ns - expected : expected - sample.utc_ns;
        std::uint64_t drift{};
        if (!growth(dm, 100'000, drift))
            return false;
        if (diff > sample.uncertainty_ns + last.uncertainty_ns + drift)
            reset(); // A real phase step cannot train or reuse the previous model.
    }
    filter_[next_] = sample;
    next_ = (next_ + 1) % filter_.size();
    count_ = std::min(count_ + 1, unsigned(filter_.size()));
    if (history_count_ == history_.size()) {
        std::move(history_.begin() + 1, history_.end(), history_.begin());
        --history_count_;
    }
    history_[history_count_++] = sample;
    ++generation_;
    fit();
    return true;
}
std::optional<NtpSample> NtpFilter::selected(std::uint64_t now) const {
    std::optional<NtpSample> best;
    std::uint64_t score = UINT64_MAX;
    for (unsigned i = 0; i < count_; ++i) {
        const auto& sample = filter_[i];
        if (now < sample.raw_ns || now - sample.raw_ns > filter_selection_age_ns)
            continue;
        std::uint64_t dispersion{};
        if (!growth(now - sample.raw_ns, 50'000, dispersion))
            continue;
        const auto candidate = sample.rtt_ns + dispersion;
        if (candidate < score || (candidate == score && best && sample.id > best->id)) {
            best = sample;
            score = candidate;
        }
    }
    return best;
}
void NtpFilter::fit() {
    rate_ = {};
    rate_.generation = generation_;
    rate_.samples = history_count_;
    if (!history_count_)
        return;
    rate_.sampled_ns = history_[history_count_ - 1].raw_ns;
    rate_.span_ns = rate_.sampled_ns - history_[0].raw_ns;
    if (history_count_ < history_.size() || rate_.span_ns < 1'800 * billion) {
        rate_.reason = "insufficient_span_or_samples";
        return;
    }
    // Even observations train; odd observations are withheld from the slope fit.
    std::int64_t low = -100'000, high = 100'000;
    for (unsigned i = 0; i < history_.size(); i += 2)
        for (unsigned j = i + 2; j < history_.size(); j += 2) {
            std::int64_t l{}, h{};
            if (!interval(history_[i], history_[j], l, h)) {
                rate_.reason = "invalid_rate_interval";
                return;
            }
            low = std::max(low, l);
            high = std::min(high, h);
        }
    std::int64_t l1{}, h1{}, l2{}, h2{};
    if (low > high || !interval(history_[0], history_[14], l1, h1) ||
        !interval(history_[16], history_[30], l2, h2) || std::max(l1, l2) > std::min(h1, h2) ||
        std::abs((l1 + h1) / 2 - (l2 + h2) / 2) > 2'000) {
        rate_.reason = "unstable_or_out_of_range";
        return;
    }
    rate_.utc_rate_ppb = std::int32_t(low + (high - low) / 2);
    rate_.uncertainty_ppb =
        std::uint32_t(std::max(high - rate_.utc_rate_ppb, rate_.utc_rate_ppb - low) + 1);
    // Never turn an out-of-range source into a qualified fit by clipping.
    std::int64_t endpoint_low{}, endpoint_high{};
    if (!interval(history_[0], history_[30], endpoint_low, endpoint_high) ||
        endpoint_low < -100'000 || endpoint_high > 100'000 || rate_.uncertainty_ppb > 5'000) {
        rate_.reason = "uncertainty_or_range";
        return;
    }
    wtp::ClockSnapshot anchor;
    anchor.utc_now_ns = history_[0].utc_ns;
    anchor.monotonic_now_ns = history_[0].raw_ns;
    anchor.rate_ppb = rate_.utc_rate_ppb;
    for (unsigned i = 1; i < history_.size(); i += 2) {
        std::uint64_t projected{}, drift{};
        const auto& s = history_[i];
        if (!project(anchor, s.raw_ns, projected) ||
            !growth(s.raw_ns - anchor.monotonic_now_ns, rate_.uncertainty_ppb, drift)) {
            rate_.reason = "held_out_arithmetic";
            return;
        }
        const auto error = projected > s.utc_ns ? projected - s.utc_ns : s.utc_ns - projected;
        if (error > s.uncertainty_ns + history_[0].uncertainty_ns + drift + 1) {
            rate_.reason = "held_out_disagreement";
            return;
        }
    }
    rate_.qualified = true;
    rate_.reason = "qualified_software";
}
RateEstimate NtpFilter::rate(std::uint64_t now) const {
    auto result = rate_;
    if (now < result.sampled_ns || now - result.sampled_ns > ntp_fresh_ns) {
        result.qualified = false;
        result.reason = "stale";
    }
    return result;
}
std::optional<std::int32_t> oscillator_correction(const RateEstimate& rate) {
    if (!rate.qualified || rate.utc_rate_ppb < -100'000 || rate.utc_rate_ppb > 100'000)
        return {};
    const auto denominator = 1'000'000'000LL + rate.utc_rate_ppb;
    const auto numerator = -std::int64_t(rate.utc_rate_ppb) * 1'000'000'000LL;
    const auto rounded =
        (numerator + (numerator < 0 ? -denominator / 2 : denominator / 2)) / denominator;
    if (rounded < -100'000 || rounded > 100'000)
        return {};
    return std::int32_t(rounded);
}
std::string rate_json(const RateEstimate& r) {
    return "{\"qualified\":" + std::string(r.qualified ? "true" : "false") +
           ",\"utc_rate_ppb\":" + std::to_string(r.utc_rate_ppb) +
           ",\"uncertainty_ppb\":" + std::to_string(r.uncertainty_ppb) + ",\"generation\":\"" +
           std::to_string(r.generation) + "\",\"sampled_raw_ns\":\"" +
           std::to_string(r.sampled_ns) + "\",\"span_ns\":\"" + std::to_string(r.span_ns) +
           "\",\"samples\":" + std::to_string(r.samples) +
           ",\"reason\":" + wtp::json::quote(r.reason) + "}";
}
std::string sample_json(const NtpSample& s) {
    return "{\"id\":\"" + std::to_string(s.id) + "\",\"clock_epoch\":\"" + std::to_string(s.epoch) +
           "\",\"send_raw_ns\":\"" + std::to_string(s.send_ns) + "\",\"receive_raw_ns\":\"" +
           std::to_string(s.raw_ns) + "\",\"reference_utc_ns\":\"" + std::to_string(s.utc_ns) +
           "\",\"uncertainty_ns\":\"" + std::to_string(s.uncertainty_ns) + "\",\"rtt_ns\":\"" +
           std::to_string(s.rtt_ns) + "\",\"server_reference_ns\":\"" +
           std::to_string(s.reference_ns) + "\",\"server_receive_ns\":\"" +
           std::to_string(s.server_receive_ns) + "\",\"server_send_ns\":\"" +
           std::to_string(s.server_send_ns) +
           "\",\"root_delay_16_16\":" + std::to_string(s.root_delay) +
           ",\"root_dispersion_16_16\":" + std::to_string(s.root_dispersion) +
           ",\"stratum\":" + std::to_string(s.stratum) + ",\"leap\":" + std::to_string(s.leap) +
           ",\"precision\":" + std::to_string(s.precision) + "}";
}
} // namespace wsprrypico::time
