// SPDX-License-Identifier: MIT
#include "microchrony.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace microchrony {
namespace {
constexpr double billion = 1e9;
std::uint64_t read(std::span<const std::uint8_t> bytes) {
    std::uint64_t result = 0;
    for (auto byte : bytes)
        result = result * 256 + byte;
    return result;
}
std::uint64_t rounded_ns(double seconds) {
    if (!(seconds >= 0) || seconds >= double(UINT64_MAX) / billion)
        return UINT64_MAX;
    return std::uint64_t(std::ceil(seconds * billion));
}
std::uint64_t add_time(std::uint64_t base, double delta) {
    if (!std::isfinite(delta) || std::abs(delta) >= double(INT64_MAX) / billion)
        return 0;
    const auto change = std::int64_t(std::llround(delta * billion));
    if (change < 0)
        return std::uint64_t(-change) <= base ? base - std::uint64_t(-change) : 0;
    return std::uint64_t(change) <= UINT64_MAX - base ? base + change : 0;
}
double difference(std::uint64_t a, std::uint64_t b) {
    return a >= b ? double(a - b) / billion : -double(b - a) / billion;
}
std::uint64_t timestamp(std::span<const std::uint8_t> bytes, std::uint64_t earliest) {
    constexpr std::uint64_t ntp_epoch = 2'208'988'800ULL;
    auto seconds = read(bytes.first(4));
    const auto floor = earliest / second + ntp_epoch;
    seconds += floor & ~0xffffffffULL;
    if (seconds < floor)
        seconds += 1ULL << 32;
    if (seconds < ntp_epoch || seconds - ntp_epoch > UINT64_MAX / second)
        return 0;
    return (seconds - ntp_epoch) * second + ((read(bytes.last(4)) * second) >> 32);
}
// Mathematical 99.9% Student t quantiles, calculated by integrating
// cos^(v-1)(theta), t=sqrt(v)*tan(theta), and rounding to four significant
// digits. Numerical observations from the external reference confirmed its
// four-digit convention and 3.5 tail. No upstream implementation is included.
double t_coefficient(unsigned freedom) {
    constexpr std::array<float, 40> quantiles{
        636.6f, 31.6f,  12.92f, 8.61f,  6.869f, 5.959f, 5.408f, 5.041f, 4.781f, 4.587f,
        4.437f, 4.318f, 4.221f, 4.14f,  4.073f, 4.015f, 3.965f, 3.922f, 3.883f, 3.85f,
        3.819f, 3.792f, 3.768f, 3.745f, 3.725f, 3.707f, 3.69f,  3.674f, 3.659f, 3.646f,
        3.633f, 3.622f, 3.611f, 3.601f, 3.591f, 3.582f, 3.574f, 3.566f, 3.558f, 3.551f};
    return freedom > quantiles.size() ? 3.5 : double(quantiles[freedom - 1]);
}
struct Line {
    double x = 0, y = 0, slope = 0, rate_sd = 0, offset_sd = 0, sd = 0;
    double delay_coefficient = 0;
    unsigned runs = 0, positive = 0, negative = 0;
    unsigned freedom = 1;
};
// Centered weighted least squares. x is raw seconds; y is the change of
// receive-UTC minus raw seconds. No floating-point Unix epoch is fitted.
Line regress(std::span<const Measurement> samples, double precision, double asymmetry) {
    Line result;
    const auto& origin = samples.front();
    const auto& last = samples.back();
    double min_delay = samples.front().delay;
    for (const auto& s : samples)
        min_delay = std::min(min_delay, s.delay);
    auto xy = [&](const Measurement& s) {
        const double x = difference(s.raw_ns, origin.raw_ns);
        return std::pair{x, difference(s.utc_ns, origin.utc_ns) - x};
    };
    auto weight = [&](const Measurement& s) {
        const auto distance = std::max(precision, s.root_delay / 2 + s.root_dispersion);
        return 1 / (distance * distance);
    };
    double sw = 0, sx = 0, sy = 0, sz = 0;
    for (const auto& s : samples) {
        const auto [x, y] = xy(s);
        const auto w = weight(s);
        sw += w;
        sx += w * x;
        sy += w * (y - asymmetry * (s.delay - min_delay));
        sz += w * (s.delay - min_delay);
    }
    result.x = sx / sw;
    result.y = sy / sw;
    const auto mz = sz / sw;
    double xx = 0, xy_sum = 0, zz = 0, xz = 0, yz = 0;
    for (const auto& s : samples) {
        const auto [x, y] = xy(s);
        const auto w = weight(s), dx = x - result.x;
        const auto dy = y - asymmetry * (s.delay - min_delay) - result.y;
        const auto dz = s.delay - min_delay - mz;
        xx += w * dx * dx;
        xy_sum += w * dx * dy;
        zz += w * dz * dz;
        xz += w * dx * dz;
        yz += w * dy * dz;
    }
    result.slope = xx > 0 ? xy_sum / xx : 0;
    const auto determinant = xx * zz - xz * xz;
    // Estimate jitter asymmetry only with independent time/delay excitation.
    // A delay trend indistinguishable from clock drift cannot identify it.
    result.delay_coefficient = asymmetry;
    const bool joint =
        samples.size() >= 13 && determinant > xx * zz * 0.01 && zz > sw * precision * precision;
    if (joint) {
        result.delay_coefficient =
            std::clamp(asymmetry + (yz * xx - xy_sum * xz) / determinant, -0.5, 0.5);
        const auto correction = result.delay_coefficient - asymmetry;
        result.slope = (xy_sum - correction * xz) / xx;
        result.y -= correction * mz;
    }
    double residual_sum = 0, variance_sum = 0;
    int previous = 0;
    for (const auto& s : samples) {
        const auto [x, y] = xy(s);
        const auto residual = y - result.y - result.slope * (x - result.x) -
                              result.delay_coefficient * (s.delay - min_delay);
        residual_sum += weight(s) * residual * residual;
        variance_sum += residual * residual;
        const int sign = residual > 1e-12 ? 1 : residual < -1e-12 ? -1 : 0;
        if (sign) {
            result.positive += sign > 0;
            result.negative += sign < 0;
            result.runs += sign != previous;
            previous = sign;
        }
    }
    const auto freedom = std::max(1U, unsigned(samples.size()) - (joint ? 3 : 2));
    result.freedom = freedom;
    const double variance = residual_sum / freedom;
    result.rate_sd = xx > 0 ? std::sqrt(variance * (joint ? zz / determinant : 1 / xx)) : 1;
    const auto end_x = difference(last.raw_ns, origin.raw_ns);
    const auto dx = end_x - result.x;
    // Prediction is for minimum delay (z=0). Include covariance with the
    // learned delay coefficient; it is not an independent known constant.
    const auto leverage =
        joint ? (zz * dx * dx + 2 * xz * dx * mz + xx * mz * mz) / determinant : dx * dx / xx;
    result.offset_sd = std::sqrt(variance * (1 / sw + leverage));
    result.sd = std::sqrt(variance_sum / freedom);
    return result;
}
} // namespace

const char* name(Rejection reason) {
    switch (reason) {
    case Rejection::None:
        return "accepted";
    case Rejection::Correlation:
        return "correlation";
    case Rejection::Packet:
        return "packet";
    case Rejection::ServerUnsynchronized:
        return "server_unsynchronized";
    case Rejection::KissRate:
        return "rate_limited";
    case Rejection::KissDenied:
        return "server_denied";
    case Rejection::Delay:
        return "delay";
    case Rejection::DelayDeviation:
        return "delay_deviation";
    case Rejection::Distance:
        return "root_distance";
    case Rejection::Jitter:
        return "jitter";
    case Rejection::Falseticker:
        return "falseticker";
    case Rejection::InsufficientSamples:
        return "insufficient_samples";
    case Rejection::Frequency:
        return "frequency";
    case Rejection::Offline:
        return "offline";
    }
    return "unknown";
}
Readiness readiness(const Tracking& t, ReadinessLimits limits) {
    const auto phase = t.remaining_correction_ns >= 0
                           ? std::uint64_t(t.remaining_correction_ns)
                           : std::uint64_t(-(t.remaining_correction_ns + 1)) + 1;
    return {t.synchronized, phase <= limits.remaining_correction_ns, t.skew_ppb <= limits.skew_ppb,
            t.uncertainty_ns <= limits.clock_error_ns};
}
double correction_rate(double offset_sd, double update_interval, double ratio) {
    if (!std::isfinite(offset_sd) || !std::isfinite(update_interval) || !std::isfinite(ratio) ||
        offset_sd < 0 || update_interval < 0 || ratio <= 0)
        return 0;
    return 0.5 * offset_sd * update_interval * ratio;
}
double phase_slew(double correction, double corr_rate, double maximum_rate) {
    if (!std::isfinite(correction) || !std::isfinite(corr_rate) || !std::isfinite(maximum_rate) ||
        corr_rate < 0 || maximum_rate <= 0 || !correction)
        return 0;
    // The generic clock driver also imposes a one-second minimum duration.
    const auto limit = std::min(maximum_rate, std::abs(correction));
    const auto speed = corr_rate ? std::min(limit, correction * correction / corr_rate) : limit;
    return std::copysign(speed, correction);
}
Engine::Engine(Config config) : config_(config) {
    config_valid_ =
        config.min_poll <= config.max_poll && config.max_poll <= 17 && config.poll_target >= 3 &&
        config.min_samples >= 3 && config.min_samples <= config.max_samples &&
        config.max_samples <= sample_capacity && config.min_sources >= 1 &&
        config.min_sources <= source_capacity && config.max_delay > 0 && config.max_delay <= 1000 &&
        config.max_delay_deviation_ratio >= 0 && config.max_distance > 0 && config.max_jitter > 0 &&
        config.precision >= 1e-9 && config.precision <= 1 && config.max_clock_error_ppm >= 0 &&
        config.max_clock_error_ppm <= 1'000'000 && config.max_update_skew_ppm > 0 &&
        config.max_drift_ppm >= 0 && config.max_drift_ppm <= 100000 && config.max_slew_ppm > 0 &&
        config.max_slew_ppm <= 100000 && config.correction_time_ratio > 0 &&
        config.combine_limit >= 0 && config.reselect_distance >= 0 && config.stratum_weight >= 0 &&
        std::isfinite(config.max_delay) && std::isfinite(config.max_distance) &&
        std::isfinite(config.max_jitter) && std::isfinite(config.max_update_skew_ppm) &&
        std::isfinite(config.max_delay_deviation_ratio) &&
        std::isfinite(config.correction_time_ratio) && std::isfinite(config.combine_limit) &&
        std::isfinite(config.reselect_distance) && std::isfinite(config.stratum_weight);
    for (auto& s : sources_)
        s.status.poll = config_.min_poll;
}
void Engine::seed(std::int32_t frequency_ppb, std::uint32_t skew_ppb) {
    if (std::abs(double(frequency_ppb)) <= config_.max_drift_ppm * 1000 &&
        skew_ppb <= 1'000'000'000U) {
        frequency_ = frequency_ppb / billion;
        // Restart age/temperature are unknown. Fresh data must re-establish
        // precision; restoring a drift never restores UTC or synchronization.
        skew_ = std::max(0.002, skew_ppb / billion);
    }
}
bool Engine::configure(unsigned slot, std::uint32_t endpoint, std::uint64_t now) {
    if (!config_valid_ || slot >= source_capacity || !endpoint)
        return false;
    for (unsigned i = 0; i < source_capacity; ++i)
        if (i != slot && sources_[i].status.endpoint == endpoint)
            return false;
    if (sources_[slot].status.endpoint == endpoint)
        return true;
    remove(slot, now);
    auto& s = sources_[slot];
    s.status.endpoint = endpoint;
    s.status.online = online_;
    s.status.reason = Rejection::InsufficientSamples;
    s.status.next_poll_ns = now;
    s.status.poll = config_.min_poll;
    s.burst_left = config_.initial_burst ? 4 : 0;
    s.burst_attempts = config_.initial_burst ? 8 : 0;
    return true;
}
void Engine::remove(unsigned slot, std::uint64_t now) {
    if (slot >= source_capacity)
        return;
    clear(sources_[slot]);
    used_generation_[slot] = 0;
    sources_[slot].status.poll = config_.min_poll;
    ++generation_;
    select(now);
}
void Engine::clear(Source& s) {
    // Samples become inaccessible through count=0. Avoid constructing or
    // copying a complete multi-kilobyte Source on the MCU stack.
    s.status = {};
    s.count = s.burst_left = s.burst_attempts = s.poll_score = 0;
    s.send_ns = s.token = s.sequence = 0;
    s.last.reset();
    s.pending = s.denied = s.synchronized = false;
    s.min_delay = s.asymmetry = 0;
}
void Engine::reset(std::uint64_t now) {
    for (auto& s : sources_) {
        const auto endpoint = s.status.endpoint;
        clear(s);
        s.status.endpoint = endpoint;
        s.status.online = online_ && endpoint;
        s.status.poll = config_.min_poll;
        s.status.next_poll_ns = now;
        s.burst_left = config_.initial_burst ? 4 : 0;
        s.burst_attempts = config_.initial_burst ? 8 : 0;
    }
    selected_ = source_capacity;
    combined_count_ = 0;
    leap_ = Leap::Unsynchronized;
    used_generation_.fill(0);
    ++generation_;
}
void Engine::online(bool enabled, std::uint64_t now) {
    if (online_ == enabled)
        return;
    online_ = enabled;
    for (auto& s : sources_) {
        s.status.online = enabled && s.status.endpoint && !s.denied;
        s.pending = false;
        if (enabled) {
            s.status.next_poll_ns = now;
            s.burst_left = config_.initial_burst ? 4 : 0;
            s.burst_attempts = config_.initial_burst ? 8 : 0;
        }
    }
    select(now);
}
void Engine::set_poll(Source& s, std::uint64_t now, std::uint64_t random) {
    const double interval = s.burst_left ? 2.0 : double(std::uint64_t(1) << s.status.poll);
    const auto delay = rounded_ns(interval + (random % 1'000'000) / 1'000'000.0);
    s.status.next_poll_ns = now <= UINT64_MAX - delay ? now + delay : UINT64_MAX;
}
std::optional<std::array<std::uint8_t, 48>> Engine::request(unsigned slot, std::uint64_t now,
                                                            std::uint64_t random, bool force) {
    if (!config_valid_ || slot >= source_capacity)
        return {};
    auto& s = sources_[slot];
    if (!s.status.online || s.denied || (!force && now < s.status.next_poll_ns) ||
        (s.status.queries && now < s.send_ns))
        return {};
    if (s.pending && !s.status.reach)
        s.status.replace = s.status.queries >= 8;
    s.status.reach = (s.status.reach << 1) & 255;
    if (!s.status.reach) {
        s.status.reason = Rejection::Offline;
        select(now);
    }
    s.send_ns = now;
    s.token = random ? random : 1;
    s.pending = true;
    ++s.status.queries;
    if (s.burst_attempts && !--s.burst_attempts)
        s.burst_left = 0;
    set_poll(s, now, random);
    std::array<std::uint8_t, 48> packet{};
    packet[0] = 0x23;
    packet[2] = std::uint8_t(s.status.poll);
    packet[3] = std::uint8_t(std::int8_t(std::floor(std::log2(config_.precision))));
    for (unsigned i = 0; i < 8; ++i)
        packet[40 + i] = std::uint8_t(s.token >> ((7 - i) * 8));
    return packet;
}

bool Engine::receive(unsigned slot, std::span<const std::uint8_t> packet, std::uint64_t now) {
    if (!config_valid_ || slot >= source_capacity)
        return false;
    auto& s = sources_[slot];
    auto reject = [&](Rejection reason) {
        ++s.status.rejected;
        s.status.reason = reason;
        if (s.last)
            s.last->rejection = reason;
        return false;
    };
    if (packet.size() != 48 || !s.pending || now < s.send_ns || (packet[0] & 7) != 4 ||
        ((packet[0] >> 3) & 7) < 3 || ((packet[0] >> 3) & 7) > 4 ||
        read(packet.subspan(24, 8)) != s.token)
        return reject(Rejection::Correlation);
    s.pending = false;
    if (!packet[1]) {
        const auto code = read(packet.subspan(12, 4));
        if (code == 0x52415445) { // RATE asks for a slower poll, not permanent denial.
            s.status.poll = std::min(config_.max_poll, s.status.poll + 1);
            s.burst_left = 0;
            set_poll(s, now, s.token);
            return reject(Rejection::KissRate);
        }
        s.denied = true;
        s.status.online = false;
        s.status.replace = true;
        s.synchronized = false;
        select(now);
        return reject(Rejection::KissDenied);
    }
    const auto leap = Leap(packet[0] >> 6);
    if (leap == Leap::Unsynchronized || packet[1] > 15) {
        s.status.selectable = false;
        s.status.replace = true;
        s.synchronized = false;
        select(now);
        return reject(Rejection::ServerUnsynchronized);
    }
    const auto precision = std::int8_t(packet[3]);
    const auto receive_utc = timestamp(packet.subspan(32, 8), config_.era_start_utc_ns);
    const auto send_utc = timestamp(packet.subspan(40, 8), config_.era_start_utc_ns);
    const auto reference_utc = timestamp(packet.subspan(16, 8), config_.era_start_utc_ns);
    const auto elapsed = difference(now, s.send_ns);
    if (!read(packet.subspan(32, 8)) || !read(packet.subspan(40, 8)) || send_utc < receive_utc ||
        reference_utc > send_utc || precision < -40 || precision > 0 ||
        difference(send_utc, receive_utc) > elapsed * 1.1)
        return reject(Rejection::Packet);
    const auto wire_delay = std::uint32_t(read(packet.subspan(4, 4)));
    const auto wire_dispersion = std::uint32_t(read(packet.subspan(8, 4)));
    const double upstream_delay = double(std::int32_t(wire_delay)) / 65536;
    const auto delay =
        std::max(config_.precision, elapsed * (1 + frequency_) - difference(send_utc, receive_utc));
    Measurement measurement;
    measurement.id = ++s.sequence;
    measurement.send_raw_ns = s.send_ns;
    measurement.receive_raw_ns = now;
    measurement.raw_ns = s.send_ns + (now - s.send_ns) / 2;
    measurement.utc_ns = receive_utc + (send_utc - receive_utc) / 2;
    measurement.server_reference_ns = reference_utc;
    measurement.server_receive_ns = receive_utc;
    measurement.server_send_ns = send_utc;
    measurement.delay = delay;
    measurement.root_delay = std::max(0.0, upstream_delay) + delay;
    measurement.precision = std::max(config_.precision, std::exp2(precision));
    measurement.root_dispersion = wire_dispersion / 65536.0 + measurement.precision +
                                  elapsed * config_.max_clock_error_ppm * 1e-6;
    measurement.root_delay_wire = wire_delay;
    measurement.root_dispersion_wire = wire_dispersion;
    measurement.stratum = packet[1];
    measurement.leap = leap;
    measurement.precision_log = precision;
    s.last = measurement;
    ++s.status.replies;
    s.status.last_receive_ns = now;
    s.status.reach |= 1;
    if (delay > config_.max_delay)
        return reject(Rejection::Delay);
    if (s.count && measurement.raw_ns <= s.samples[s.count - 1].raw_ns)
        return reject(Rejection::Packet);
    if (measurement.root_delay / 2 + measurement.root_dispersion > config_.max_distance)
        return reject(Rejection::Distance);
    // Excess-delay testing uses the preceding model. A new measurement cannot
    // first alter its own baseline, variance or prediction to pass this test.
    if (s.count >= 3 && config_.max_delay_deviation_ratio > 0) {
        const auto& e = s.status.estimate;
        const double delay_increase = delay - s.min_delay;
        const double noise = std::max(config_.precision, e.jitter);
        const double expected = difference(source_utc(s, measurement.raw_ns), measurement.utc_ns);
        const double growth = difference(now, e.raw_ns) * e.skew;
        if (delay_increase > config_.max_delay_deviation_ratio * noise + 2 * growth &&
            std::abs(expected) > config_.max_delay_deviation_ratio * noise + growth)
            return reject(Rejection::DelayDeviation);
    }
    if (s.count == config_.max_samples) {
        std::move(s.samples.begin() + 1, s.samples.begin() + s.count, s.samples.begin());
        --s.count;
    }
    s.samples[s.count++] = measurement;
    s.synchronized = true;
    s.status.last_accepted_ns = now;
    s.status.replace = false;
    s.min_delay = measurement.delay;
    for (unsigned i = 0; i < s.count; ++i)
        s.min_delay = std::min(s.min_delay, s.samples[i].delay);
    ++s.status.generation;
    fit(s);
    s.status.reason = s.status.estimate.valid ? Rejection::None : Rejection::InsufficientSamples;
    if (s.burst_left)
        --s.burst_left;
    if (!s.burst_left) {
        if (s.count > config_.poll_target && ++s.poll_score >= config_.poll_target) {
            s.status.poll = std::min(config_.max_poll, s.status.poll + 1);
            s.poll_score = 0;
        } else if (s.count < config_.poll_target && s.status.poll > config_.min_poll) {
            --s.status.poll;
            s.poll_score = 0;
        }
    }
    set_poll(s, now, s.token);
    select(now, true);
    return true;
}

void Engine::fit(Source& source) {
    auto& e = source.status.estimate;
    e = {};
    e.samples = source.count;
    if (!source.count)
        return;
    while (source.count >= 3) {
        const auto points = std::span{source.samples.data(), source.count};
        const auto line = regress(points, config_.precision, 0);
        source.asymmetry = line.delay_coefficient;
        const auto signs = line.positive + line.negative;
        // Wald-Wolfowitz residual runs test. A persistent trend means the old
        // straight line no longer describes the clock/path. Shorten history.
        if (source.count > config_.min_samples && line.positive && line.negative && signs >= 4) {
            const double pairs = 2.0 * line.positive * line.negative;
            const double expected = 1 + pairs / signs;
            const double variance = pairs * (pairs - signs) / (double(signs) * signs * (signs - 1));
            if (line.runs < expected - 1.645 * std::sqrt(std::max(0.0, variance))) {
                std::move(source.samples.begin() + 1, source.samples.begin() + source.count,
                          source.samples.begin());
                --source.count;
                continue;
            }
        }
        const auto& first = points.front();
        const auto& last = points.back();
        e.samples = source.count;
        e.raw_ns = last.raw_ns;
        e.first_raw_ns = first.raw_ns;
        e.rate = line.slope;
        e.rate_sd = std::max(1e-12, line.rate_sd);
        e.skew = std::max(1e-12, line.rate_sd * t_coefficient(line.freedom));
        e.offset_sd = line.offset_sd;
        e.jitter = std::max(1e-9, line.sd);
        e.asymmetry = line.delay_coefficient;
        const auto elapsed = difference(last.raw_ns, first.raw_ns);
        e.utc_ns = add_time(first.utc_ns, elapsed + line.y + line.slope * (elapsed - line.x));
        e.root_delay = last.root_delay;
        e.root_dispersion = last.root_dispersion + line.offset_sd;
        e.runs = line.runs;
        e.valid = std::isfinite(e.skew) && std::isfinite(e.rate) && e.utc_ns;
        return;
    }
    const auto& last = source.samples[source.count - 1];
    e.raw_ns = last.raw_ns;
    e.first_raw_ns = source.samples[0].raw_ns;
    e.utc_ns = last.utc_ns;
    e.root_delay = last.root_delay;
    e.root_dispersion = last.root_dispersion + 4;
}
std::uint64_t Engine::source_utc(const Source& s, std::uint64_t raw) const {
    return add_time(s.status.estimate.utc_ns,
                    difference(raw, s.status.estimate.raw_ns) * (1 + s.status.estimate.rate));
}
double Engine::distance(const Source& s, std::uint64_t raw) const {
    const auto& e = s.status.estimate;
    if (!e.valid || raw < e.raw_ns)
        return std::numeric_limits<double>::infinity();
    return e.root_delay / 2 + e.root_dispersion +
           difference(raw, e.raw_ns) * std::max(e.skew, config_.max_clock_error_ppm * 1e-6);
}
void Engine::select(std::uint64_t now, bool score_update) {
    std::array<unsigned, source_capacity> candidates{};
    unsigned count = 0;
    for (unsigned i = 0; i < source_capacity; ++i) {
        auto& s = sources_[i];
        s.status.selectable = s.status.selected = s.status.combined = false;
        if (!s.status.endpoint || !s.status.online || !s.status.reach || s.denied ||
            !s.synchronized || !s.status.estimate.valid)
            continue;
        if (distance(s, now) > config_.max_distance) {
            s.status.reason = Rejection::Distance;
            s.status.replace = true;
            continue;
        }
        if (s.status.estimate.jitter > config_.max_jitter) {
            s.status.reason = Rejection::Jitter;
            continue;
        }
        candidates[count++] = i;
    }
    if (count < config_.min_sources) {
        selected_ = source_capacity;
        combined_count_ = 0;
        leap_ = Leap::Unsynchronized;
        return;
    }
    // Find the largest agreement set of source error intervals. A minority of
    // incompatible sources cannot pull the clock to a false majority.
    unsigned best_count = 0, best_mask = 0;
    for (unsigned mask = 1; mask < (1U << count); ++mask) {
        double low = -std::numeric_limits<double>::infinity();
        double high = std::numeric_limits<double>::infinity();
        unsigned members = 0;
        const auto origin = source_utc(sources_[candidates[0]], now);
        for (unsigned k = 0; k < count; ++k)
            if (mask & (1U << k)) {
                const auto& s = sources_[candidates[k]];
                const double center = difference(source_utc(s, now), origin);
                const double radius = distance(s, now);
                low = std::max(low, center - radius);
                high = std::min(high, center + radius);
                ++members;
            }
        if (low <= high && members > best_count) {
            best_count = members;
            best_mask = mask;
        }
    }
    if (best_count * 2 <= count || best_count < config_.min_sources) {
        selected_ = source_capacity;
        combined_count_ = 0;
        leap_ = Leap::Unsynchronized;
        return;
    }
    unsigned best = source_capacity;
    unsigned minimum_stratum = 16;
    for (unsigned k = 0; k < count; ++k)
        if (best_mask & (1U << k))
            minimum_stratum = std::min<unsigned>(
                minimum_stratum,
                sources_[candidates[k]].samples[sources_[candidates[k]].count - 1].stratum);
    double minimum_distance = std::numeric_limits<double>::infinity();
    std::array<double, source_capacity> selection_distance{};
    for (unsigned k = 0; k < count; ++k) {
        auto& s = sources_[candidates[k]];
        if (!(best_mask & (1U << k))) {
            s.status.reason = Rejection::Falseticker;
            s.status.replace = true;
            s.status.selection_score = 1;
            continue;
        }
        s.status.selectable = true;
        s.status.reason = Rejection::None;
        const auto stratum = s.samples[s.count - 1].stratum;
        double path_distance = std::numeric_limits<double>::infinity();
        for (unsigned j = 0; j < s.count; ++j)
            path_distance =
                std::min(path_distance, s.samples[j].root_delay / 2 + s.samples[j].root_dispersion);
        // Rank the path by the best retained exchange, as a later queue spike
        // does not erase that measured path quality. Agreement and reported
        // clock error still use the conservative full model interval above.
        const double candidate =
            path_distance + s.status.estimate.offset_sd +
            difference(now, s.status.estimate.raw_ns) * s.status.estimate.skew +
            (stratum - minimum_stratum) * config_.stratum_weight;
        selection_distance[candidates[k]] = candidate;
        if (candidate < minimum_distance) {
            minimum_distance = candidate;
            best = candidates[k];
        }
    }
    // Accumulate evidence for a better source rather than switching on one
    // favorable packet. Scores are relative distances, with reselectdist added
    // only to challengers, and reset when the reference changes.
    const bool current_usable =
        selected_ < source_capacity && sources_[selected_].status.selectable;
    if (current_usable) {
        unsigned challenger = selected_;
        double highest = 10;
        for (unsigned k = 0; k < count; ++k) {
            const auto index = candidates[k];
            auto& s = sources_[index];
            if (!s.status.selectable || index == selected_)
                continue;
            if (score_update) {
                const auto ratio = selection_distance[selected_] /
                                   std::max(config_.precision,
                                            selection_distance[index] + config_.reselect_distance);
                s.status.selection_score = std::clamp(s.status.selection_score * ratio, 1.0, 1e12);
            }
            if (s.status.selection_score >= highest) {
                highest = s.status.selection_score;
                challenger = index;
            }
        }
        best = challenger;
    }
    if (best != selected_)
        for (auto& s : sources_)
            s.status.selection_score = 1;
    std::array<unsigned, source_capacity> combined{};
    unsigned combined_count = 0;
    for (unsigned k = 0; k < count; ++k) {
        auto& s = sources_[candidates[k]];
        if (!s.status.selectable)
            continue;
        const auto& reference = sources_[best];
        if (candidates[k] == best ||
            (distance(s, now) <= config_.combine_limit * distance(reference, now) &&
             std::abs(s.status.estimate.rate - reference.status.estimate.rate) <=
                 s.status.estimate.skew + reference.status.estimate.skew)) {
            s.status.combined = true;
            combined[combined_count++] = candidates[k];
        }
    }
    sources_[best].status.selected = true;
    discipline(best, {combined.data(), combined_count}, now);
}

void Engine::advance(std::uint64_t now) {
    if (!clock_valid_ || now < clock_raw_ns_)
        return;
    const auto elapsed = difference(now, clock_raw_ns_);
    double phase = slew_ * elapsed;
    if (std::abs(phase) > std::abs(pending_phase_))
        phase = pending_phase_;
    clock_utc_ns_ = add_time(clock_utc_ns_, elapsed * (1 + frequency_) + phase);
    pending_phase_ -= phase;
    if (std::abs(pending_phase_) < 1e-9)
        pending_phase_ = slew_ = 0;
    clock_raw_ns_ = now;
}
void Engine::discipline(unsigned selected, std::span<const unsigned> combined, std::uint64_t now) {
    // A combined peer can update selection statistics without repeatedly
    // steering the system clock between updates from the chosen reference.
    const bool changed =
        selected != selected_ || used_generation_[selected] != sources_[selected].status.generation;
    if (!changed)
        return;
    auto& source = sources_[selected];
    const auto origin = source_utc(source, now);
    double weights = 0, offset = 0, frequency = 0, variance = 0;
    for (auto i : combined) {
        const auto& s = sources_[i];
        const auto& e = s.status.estimate;
        const double error = std::max(1e-9, e.offset_sd);
        const double weight = 1 / (error * error);
        weights += weight;
        offset += weight * difference(source_utc(s, now), origin);
        frequency += weight * e.rate;
        variance += weight * e.skew * e.skew;
        used_generation_[i] = s.status.generation;
    }
    const auto reference = add_time(origin, offset / weights);
    const auto next_frequency = frequency / weights;
    double next_skew = std::sqrt(variance / weights);
    double reference_distance = 0;
    for (auto i : combined) {
        const auto& s = sources_[i];
        reference_distance =
            std::max(reference_distance,
                     distance(s, now) + std::abs(difference(source_utc(s, now), reference)));
        next_skew = std::max(next_skew, s.status.estimate.skew +
                                            std::abs(s.status.estimate.rate - next_frequency));
    }
    if (!clock_valid_) {
        // A microcontroller without an RTC must initialize its UTC epoch once.
        clock_valid_ = true;
        clock_raw_ns_ = now;
        clock_utc_ns_ = reference;
    } else
        advance(now);
    if (next_skew <= config_.max_update_skew_ppm * 1e-6) {
        const double old_variance = skew_ * skew_;
        const double new_variance = std::max(1e-24, next_skew * next_skew);
        const double gain = old_variance / (old_variance + new_variance);
        frequency_ = std::clamp(frequency_ + gain * (next_frequency - frequency_),
                                -config_.max_drift_ppm * 1e-6, config_.max_drift_ppm * 1e-6);
        // Fits overlap. Blending their centers does not create additional
        // independent measurements or reduce the new fit's own uncertainty.
        skew_ = next_skew + std::abs(next_frequency - frequency_);
    }
    pending_phase_ = difference(reference, clock_utc_ns_);
    const auto interval =
        last_update_ns_ && now > last_update_ns_ ? difference(now, last_update_ns_) : 1.0;
    const auto typical_error = std::max(config_.precision, std::sqrt(1 / weights));
    const auto corr_rate = correction_rate(typical_error, last_update_ns_ ? interval : 0,
                                           config_.correction_time_ratio);
    slew_ = phase_slew(pending_phase_, corr_rate, config_.max_slew_ppm * 1e-6);
    slew_ = std::clamp(slew_, -0.1 - frequency_, 0.1 - frequency_);
    root_delay_ = source.status.estimate.root_delay;
    root_dispersion_ = std::max(0.0, reference_distance - root_delay_ / 2);
    selected_ = selected;
    combined_count_ = unsigned(combined.size());
    leap_ = source.samples[source.count - 1].leap;
    last_update_ns_ = now;
    last_source_raw_ns_ = 0;
    for (auto i : combined)
        last_source_raw_ns_ = std::max(last_source_raw_ns_,
                                       sources_[i].samples[sources_[i].count - 1].receive_raw_ns);
    ++generation_;
}
Tracking Engine::tracking(std::uint64_t now) const {
    Tracking result;
    result.raw_ns = now;
    result.generation = generation_;
    result.selected = selected_;
    result.combined_sources = combined_count_;
    result.source_raw_ns = last_source_raw_ns_;
    result.leap = leap_;
    if (!clock_valid_ || now < clock_raw_ns_)
        return result;
    const double elapsed = difference(now, clock_raw_ns_);
    double phase = slew_ * elapsed;
    if (std::abs(phase) > std::abs(pending_phase_))
        phase = pending_phase_;
    result.utc_ns = add_time(clock_utc_ns_, elapsed * (1 + frequency_) + phase);
    const double remaining = pending_phase_ - phase;
    result.remaining_correction_ns = std::int64_t(std::llround(remaining * billion));
    const double rate = frequency_ + (std::abs(remaining) >= 1e-9 ? slew_ : 0);
    result.rate_ppb = std::int32_t(std::llround(std::clamp(rate, -0.1, 0.1) * billion));
    result.utc_frequency_ppb = std::int32_t(std::llround(frequency_ * billion));
    result.skew_ppb = std::uint32_t(std::ceil(std::min(1.0, skew_) * billion));
    result.root_delay = root_delay_;
    result.root_dispersion =
        root_dispersion_ +
        difference(now, last_update_ns_) * std::max(skew_, config_.max_clock_error_ppm * 1e-6);
    const auto root_distance = result.root_delay / 2 + result.root_dispersion;
    result.synchronized = selected_ < source_capacity && leap_ != Leap::Unsynchronized &&
                          root_distance <= config_.max_distance;
    result.uncertainty_ns = rounded_ns(std::abs(remaining) + root_distance);
    return result;
}
SourceStatus Engine::status(unsigned slot, std::uint64_t now) const {
    if (slot >= source_capacity)
        return {};
    auto status = sources_[slot].status;
    if (status.selectable && distance(sources_[slot], now) > config_.max_distance) {
        status.selectable = status.selected = status.combined = false;
        status.reason = Rejection::Distance;
        status.replace = true;
    }
    return status;
}
std::span<const Measurement> Engine::history(unsigned slot) const {
    if (slot >= source_capacity)
        return {};
    return {sources_[slot].samples.data(), sources_[slot].count};
}
const Measurement* Engine::last_measurement(unsigned slot) const {
    return slot < source_capacity && sources_[slot].last ? &*sources_[slot].last : nullptr;
}
} // namespace microchrony
