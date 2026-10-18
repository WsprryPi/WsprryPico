// SPDX-License-Identifier: MIT
#include "microchrony.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <sstream>

using namespace microchrony;
namespace {
constexpr std::uint64_t epoch = 1'800'000'000 * second;
#define CHECK(value)                                                                               \
    do {                                                                                           \
        if (!(value)) {                                                                            \
            std::cerr << __LINE__ << ": " #value "\n";                                             \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
void stamp(std::array<std::uint8_t, 48>& packet, unsigned offset, std::uint64_t utc) {
    const auto seconds = utc / second + 2'208'988'800ULL;
    const auto fraction = ((utc % second) << 32) / second;
    for (unsigned i = 0; i < 4; ++i) {
        packet[offset + i] = std::uint8_t(seconds >> ((3 - i) * 8));
        packet[offset + 4 + i] = std::uint8_t(fraction >> ((3 - i) * 8));
    }
}
std::array<std::uint8_t, 48> reply(const std::array<std::uint8_t, 48>& request,
                                   std::uint64_t server, double dispersion = 0) {
    std::array<std::uint8_t, 48> packet{};
    packet[0] = 0x24;
    packet[1] = 1;
    packet[3] = std::uint8_t(std::int8_t(-26));
    std::copy(request.begin() + 40, request.end(), packet.begin() + 24);
    stamp(packet, 16, server - second);
    stamp(packet, 32, server);
    stamp(packet, 40, server);
    const auto d = std::uint32_t(std::ceil(dispersion * 65536));
    for (unsigned i = 0; i < 4; ++i)
        packet[8 + i] = std::uint8_t(d >> ((3 - i) * 8));
    return packet;
}
bool measurement(Engine& engine, unsigned slot, std::uint64_t midpoint, double offset,
                 std::uint64_t delay = 2'000'000, double dispersion = 0) {
    const auto send = midpoint - delay / 2;
    const auto request = engine.request(slot, send, midpoint + slot + 1, true);
    CHECK(request);
    const auto utc =
        std::uint64_t(std::int64_t(epoch + midpoint) + std::int64_t(std::llround(offset * 1e9)));
    return engine.receive(slot, reply(*request, utc, dispersion), send + delay);
}
void learning() {
    for (double rate : {-20e-6, 0.0, 20e-6}) {
        Engine engine;
        CHECK(engine.configure(0, 1, 0));
        CHECK(!engine.tracking(0).synchronized);
        for (unsigned i = 1; i <= 24; ++i) {
            const auto midpoint = i * 64 * second;
            CHECK(measurement(engine, 0, midpoint, rate * double(midpoint) / 1e9));
            const auto status = engine.status(0, midpoint + 1'000'000);
            if (i < 3)
                CHECK(!engine.tracking(midpoint + 1'000'000).synchronized);
            else {
                CHECK(status.estimate.valid);
                CHECK(std::abs(status.estimate.rate - rate) < 1e-9);
                CHECK(status.estimate.skew < 1e-8);
                const auto tracking = engine.tracking(midpoint + 1'000'000);
                CHECK(tracking.synchronized && tracking.uncertainty_ns < 3'000'000);
                CHECK(std::abs(tracking.utc_frequency_ppb - rate * 1e9) < 2);
            }
        }
        const auto before = engine.tracking(24 * 64 * second + 1'000'000);
        const auto after = engine.tracking(24 * 64 * second + 32 * second);
        CHECK(before.generation == after.generation);
        CHECK(before.source_raw_ns == after.source_raw_ns);
        CHECK(before.skew_ppb == after.skew_ppb);
        CHECK(after.uncertainty_ns > before.uncertainty_ns);
        CHECK(readiness(after).ready());
        CHECK(!readiness(after, {1, 1, 1}).ready());
    }
}
void delay_and_loss() {
    Engine engine;
    CHECK(engine.configure(0, 1, 0));
    for (unsigned i = 1; i <= 12; ++i)
        CHECK(measurement(engine, 0, i * 64 * second, -double(i) * 64 * 20e-6));
    const auto old = engine.tracking(12 * 64 * second + 1'000'000);
    CHECK(!measurement(engine, 0, 13 * 64 * second, -13 * 64 * 20e-6 + 0.12, 242'000'000));
    const auto bad = engine.status(0, 13 * 64 * second + 121'000'000);
    CHECK(bad.reason == Rejection::DelayDeviation);
    CHECK(engine.last_measurement(0)->rejection == Rejection::DelayDeviation);
    const auto current = engine.tracking(13 * 64 * second + 121'000'000);
    CHECK(current.source_raw_ns == old.source_raw_ns && current.generation == old.generation);
    CHECK(current.synchronized && current.uncertainty_ns > old.uncertainty_ns);
    CHECK(measurement(engine, 0, 14 * 64 * second, -14 * 64 * 20e-6));
    CHECK(engine.tracking(14 * 64 * second + 1'000'000).source_raw_ns > old.source_raw_ns);
    engine.online(false, 15 * 64 * second);
    CHECK(!engine.request(0, 15 * 64 * second, 1));
    CHECK(!engine.tracking(15 * 64 * second).synchronized); // Source withdrawn; UTC still projects.
    CHECK(engine.tracking(15 * 64 * second).utc_ns > 0);
    CHECK(!engine.tracking(4'000'000 * second).synchronized);
    engine.online(true, 16 * 64 * second);
    CHECK(engine.request(0, 16 * 64 * second, 2));
}
void source_agreement() {
    Engine engine;
    for (unsigned slot = 0; slot < 3; ++slot)
        CHECK(engine.configure(slot, slot + 1, 0));
    CHECK(!engine.configure(3, 1, 0));
    for (unsigned i = 1; i <= 12; ++i)
        for (unsigned slot = 0; slot < 3; ++slot) {
            const auto midpoint = (i * 64 + slot) * second;
            const double offset = slot == 2 ? 0.25 : slot * 0.0001;
            CHECK(measurement(engine, slot, midpoint, offset));
        }
    const auto t = engine.tracking(12 * 64 * second + 3 * second);
    CHECK(t.synchronized && t.selected != 2 && t.combined_sources == 2);
    CHECK(engine.status(2, t.raw_ns).reason == Rejection::Falseticker);
    CHECK(engine.status(2, t.raw_ns).replace);
    engine.remove(0, t.raw_ns);
    CHECK(!engine.tracking(t.raw_ns).synchronized); // Two disagreeing sources lack a majority.
}
void packets_and_polling() {
    Engine engine;
    CHECK(engine.configure(0, 1, 0));
    auto request = engine.request(0, 0, 123);
    CHECK(request && !engine.request(0, 1, 124));
    auto packet = reply(*request, epoch);
    auto wrong = packet;
    wrong[24] ^= 1;
    CHECK(!engine.receive(0, wrong, 1'000'000));
    CHECK(engine.receive(0, packet, 2'000'000));
    CHECK(!engine.receive(0, packet, 3'000'000));
    auto when = engine.status(0, 0).next_poll_ns;
    request = engine.request(0, when, 125);
    CHECK(request);
    packet = reply(*request, epoch + when);
    packet[1] = 0;
    std::copy_n("RATE", 4, packet.begin() + 12);
    CHECK(!engine.receive(0, packet, when + 1'000'000));
    CHECK(engine.status(0, when).reason == Rejection::KissRate);
    CHECK(engine.status(0, when).online);
    CHECK(engine.status(0, when).next_poll_ns >= when + 128 * second);
    Engine lost;
    CHECK(lost.configure(0, 1, 0));
    when = 0;
    for (unsigned i = 0; i < 12; ++i) {
        CHECK(lost.request(0, when, i + 1));
        const auto next = lost.status(0, when).next_poll_ns;
        CHECK(next > when);
        if (i >= 7)
            CHECK(next - when >= 64 * second);
        when = next;
    }
    CHECK(lost.status(0, when).replace);
}
void restoration() {
    Engine engine;
    engine.seed(-20000, 10);
    CHECK(!engine.tracking(0).synchronized);
    CHECK(engine.configure(0, 1, 0));
    for (unsigned i = 1; i <= 3; ++i)
        CHECK(measurement(engine, 0, i * 2 * second, -double(i) * 2 * 20e-6));
    const auto t = engine.tracking(6 * second + 1'000'000);
    CHECK(t.synchronized && std::abs(t.utc_frequency_ppb + 20000) < 2);
    engine.reset(t.raw_ns);
    CHECK(!engine.tracking(t.raw_ns).synchronized);
    CHECK(engine.tracking(t.raw_ns).source_raw_ns == t.source_raw_ns);
}
void withdrawals() {
    for (unsigned fault = 0; fault < 3; ++fault) {
        Engine e;
        CHECK(e.configure(0, 1, 0));
        for (unsigned i = 1; i <= 6; ++i)
            CHECK(measurement(e, 0, i * 64 * second, 0));
        auto when = 7 * 64 * second;
        auto request = e.request(0, when, 123, true);
        CHECK(request);
        auto packet = reply(*request, epoch + when);
        if (fault == 0)
            packet[0] |= 0xc0;
        if (fault == 1)
            packet[1] = 16;
        if (fault == 2) {
            packet[1] = 0;
            std::copy_n("DENY", 4, packet.begin() + 12);
        }
        CHECK(!e.receive(0, packet, when + 2'000'000));
        CHECK(!e.tracking(when + 2'000'000).synchronized);
        if (fault < 2)
            CHECK(!measurement(e, 0, 8 * 64 * second, 0, 3'100'000'000));
        CHECK(e.configure(1, 2, when));
        for (unsigned i = 9; i <= 12; ++i)
            CHECK(measurement(e, 1, i * 64 * second, 0));
        CHECK(e.tracking(12 * 64 * second + 1'000'000).selected == 1);
        CHECK(!e.status(0, 12 * 64 * second).selectable);
    }
    Engine e;
    CHECK(e.configure(0, 1, 0));
    for (unsigned i = 1; i <= 6; ++i)
        CHECK(measurement(e, 0, i * 64 * second, 0));
    for (unsigned i = 7; i <= 14; ++i)
        CHECK(e.request(0, i * 64 * second, i, true));
    CHECK(!e.tracking(14 * 64 * second).synchronized);
}
void combined_bound() {
    Config c;
    c.max_delay_deviation_ratio = 0;
    Engine e(c);
    CHECK(e.configure(0, 1, 0) && e.configure(1, 2, 0));
    for (unsigned i = 1; i <= 12; ++i) {
        const auto raw = i * 64 * second;
        CHECK(measurement(e, 0, raw, i % 2 ? .0003 : -.0003));
        CHECK(measurement(e, 1, raw + second, .0035, 5'800'000));
    }
    const auto raw = 12 * 64 * second + 2 * second;
    const auto t = e.tracking(raw);
    CHECK(t.synchronized && t.combined_sources == 2);
    const auto error = std::abs(double(std::int64_t(t.utc_ns - (epoch + raw))));
    CHECK(error <= t.uncertainty_ns); // Weighted center retains all source error intervals.
}
void correlated_delay() {
    Config c;
    c.max_delay_deviation_ratio = 0;
    Engine e(c);
    CHECK(e.configure(0, 1, 0));
    for (unsigned i = 1; i <= 32; ++i) {
        const double delay = .01 + .00015 * i + (i % 2 ? .0005 : -.0005);
        const double noise = ((i * 7) % 5 - 2.0) * .00004;
        CHECK(measurement(e, 0, i * 64 * second, -.000020 * i * 64 + .4 * delay + noise,
                          std::uint64_t(delay * 1e9)));
    }
    const auto estimate = e.status(0, 32 * 64 * second).estimate;
    CHECK(estimate.valid && estimate.samples >= 13);
    // Inverting this fixture's full time/delay covariance gives ~0.188 ppm;
    // treating its fitted delay coefficient as known understates that bound.
    CHECK(estimate.skew > 0.15e-6);
    CHECK(std::abs(estimate.rate + .000020) <= estimate.skew);
}
void replay_driver() {
    Config full_config;
    full_config.max_drift_ppm = 100;
    full_config.max_clock_error_ppm = 50;
    full_config.min_poll = full_config.max_poll = 6;
    auto phase_config = full_config;
    phase_config.max_update_skew_ppm = 1e-12; // Phase damping, with no learned rate applied.
    Engine full(full_config), phase(phase_config);
    std::uint32_t previous = 0;
    std::uint64_t id, raw, utc, delay, probe, truth;
    unsigned endpoint, received;
    double dispersion;
    std::uint64_t baseline_raw = 0, baseline_utc = 0, baseline_error = UINT64_MAX;
    while (std::cin >> id >> endpoint >> raw >> utc >> delay >> dispersion >> received >> probe >>
           truth) {
        if (endpoint != previous) {
            full.configure(0, endpoint, raw);
            phase.configure(0, endpoint, raw);
            baseline_raw = 0;
            previous = endpoint;
        }
        const auto send = raw - delay / 2;
        const auto fr = full.request(0, send, id, true);
        const auto pr = phase.request(0, send, id, true);
        if (received) {
            CHECK(fr && pr);
            (void)full.receive(0, reply(*fr, utc, dispersion), raw + delay / 2);
            (void)phase.receive(0, reply(*pr, utc, dispersion), raw + delay / 2);
            baseline_raw = raw;
            baseline_utc = utc;
            baseline_error = delay / 2 + std::uint64_t(std::ceil(dispersion * 1e9)) + 2000;
        }
        auto emit = [&](unsigned mode, std::uint64_t estimate, std::uint64_t error,
                        std::uint64_t age, bool synchronized, std::int32_t rate) {
            const bool usable = synchronized && age <= 90 * second && error <= 500'000'000;
            const auto offset = estimate >= truth ? std::int64_t(estimate - truth)
                                                  : -std::int64_t(truth - estimate);
            std::cout << mode << ' ' << id << ' ' << offset << ' ' << error << ' ' << age << ' '
                      << usable << ' ' << rate << '\n';
        };
        emit(0, baseline_utc + probe - baseline_raw,
             baseline_error + std::uint64_t((probe - baseline_raw) * 0.0001), probe - baseline_raw,
             baseline_raw != 0, 0);
        for (auto pair : {std::pair{1U, &phase}, std::pair{2U, &full}}) {
            const auto t = pair.second->tracking(probe);
            emit(pair.first, t.utc_ns, t.uncertainty_ns, probe - t.source_raw_ns, t.synchronized,
                 t.utc_frequency_ppb);
        }
    }
}
void slew_driver() {
    double offset, sd, interval;
    while (std::cin >> offset >> sd >> interval) {
        const auto rate = correction_rate(sd, interval, 3);
        const auto slew = phase_slew(-offset, rate, Config{}.max_slew_ppm * 1e-6);
        std::cout.precision(15);
        std::cout << rate << ' ' << slew << '\n';
    }
}
void selection_driver() {
    Config config;
    config.max_delay_deviation_ratio = 0; // Reference receives post-admission observations.
    Engine engine(config);
    unsigned configured = 0;
    unsigned slot, stratum, leap, reachable;
    double when, offset, delay, dispersion;
    unsigned id = 0;
    while (std::cin >> slot >> when >> offset >> delay >> dispersion >> stratum >> leap >>
           reachable) {
        CHECK(slot < source_capacity);
        if (!(configured & (1U << slot))) {
            CHECK(engine.configure(slot, slot + 1, 0));
            configured |= 1U << slot;
        }
        const auto mid = std::uint64_t(std::llround((when - 1800000000) * 1e9));
        const auto half = std::uint64_t(std::llround(delay * 5e8));
        const auto request = engine.request(slot, mid - half, ++id, true);
        CHECK(request);
        if (reachable) {
            const auto utc =
                std::uint64_t(std::int64_t(epoch + mid) - std::int64_t(std::llround(offset * 1e9)));
            auto packet = reply(*request, utc, dispersion);
            packet[0] = std::uint8_t(0x24 | leap << 6);
            packet[1] = std::uint8_t(stratum);
            (void)engine.receive(slot, packet, mid + half);
        }
        std::cout << id;
        for (unsigned i = 0; i < source_capacity; ++i) {
            const auto s = engine.status(i, mid + half);
            const char symbol = s.selected                           ? '*'
                                : s.combined                         ? '+'
                                : s.reason == Rejection::Falseticker ? 'x'
                                                                     : '?';
            std::cout.precision(12);
            std::cout << ' ' << symbol << ' ' << s.selection_score;
        }
        std::cout << '\n';
    }
}
void selection_hysteresis() {
    Config config;
    config.max_delay_deviation_ratio = 0;
    Engine e(config);
    CHECK(e.configure(0, 1, 0) && e.configure(1, 2, 0));
    for (unsigned i = 1; i <= 10; ++i) {
        CHECK(measurement(e, 0, i * 64 * second, 0, 6'000'000));
        CHECK(measurement(e, 1, (i * 64 + 1) * second, 0, i < 8 ? 8'000'000 : 2'000'000));
        if (i >= 3 && i <= 8)
            CHECK(e.tracking((i * 64 + 1) * second + 1'000'000).selected == 0);
        if (i == 8) {
            const auto score = e.status(1, (i * 64 + 1) * second).selection_score;
            CHECK(score > 2 && score < 3);
            for (unsigned read = 0; read < 20; ++read)
                CHECK(e.status(1, (i * 64 + 1) * second + read).selection_score == score);
        }
    }
    CHECK(e.tracking(642 * second).selected == 1);
}
void control_rules() {
    for (double correction : {-.1, -.002, -.0002, .0002, .002, .1}) {
        const auto small = phase_slew(correction, correction_rate(.001, 64, 3), .083333333);
        const auto large = phase_slew(correction * 10, correction_rate(.001, 64, 3), .083333333);
        CHECK(std::signbit(small) == std::signbit(correction));
        CHECK(std::abs(large) >= std::abs(small));
        CHECK(std::abs(large) <= .083333333);
    }
    Config config;
    config.max_drift_ppm = 100;
    Engine noisy(config);
    CHECK(noisy.configure(0, 1, 0));
    CHECK(measurement(noisy, 0, 2 * second, .001));
    CHECK(measurement(noisy, 0, 4 * second, -.002));
    CHECK(measurement(noisy, 0, 6 * second, .002));
    CHECK(noisy.tracking(6 * second + 1'000'000).synchronized);
    CHECK(std::abs(noisy.tracking(6 * second + 1'000'000).utc_frequency_ppb) <= 100000);
    Engine saturated(config);
    CHECK(saturated.configure(0, 1, 0));
    for (unsigned i = 1; i < 10; ++i)
        CHECK(measurement(saturated, 0, i * 64 * second, .0002 * i * 64));
    const auto t = saturated.tracking(9 * 64 * second + 1'000'000);
    CHECK(t.synchronized && t.utc_frequency_ppb == 100000 && t.skew_ppb >= 100000);
}
void frequency_innovation() {
    // Overlapping, equal fits do not independently manufacture confidence.
    FrequencyEstimate repeated{20e-6, 3e-6};
    for (unsigned i = 0; i < 100; ++i)
        repeated = combine_frequency(repeated, {20e-6, 3e-6});
    CHECK(std::abs(repeated.rate - 20e-6) < 1e-15);
    CHECK(std::abs(repeated.skew - 3e-6) < 1e-15);
    const auto innovation = combine_frequency({0, 1e-6}, {20e-6, 1e-6});
    CHECK(innovation.rate > 14.99e-6 && innovation.rate < 15.01e-6);
    CHECK(innovation.skew > 9e-6); // A real disagreement expands tracking error.
    const auto untrusted = combine_frequency({0, 1e-6}, {20e-6, 1000e-6});
    CHECK(std::abs(untrusted.rate) < 1e-9); // No whipsaw from a much noisier fit.
}
void source_combination() {
    // Equal path quality can have unequal frequency precision. A noisier
    // frequency must not gain authority merely from a precise current offset.
    std::array<SourceEstimate, 2> s{
        {{0, 1e-6, 0, 1e-6, 3e-6, .01, 0}, {.002, 1e-9, 20e-6, 10e-6, 30e-6, .01, 64}}};
    const auto r = combine_sources(s);
    CHECK(std::abs(r.offset - .001) < 1e-12);
    CHECK(r.rate < 0.2e-6);
    CHECK(r.offset_sd > .0014); // Source disagreement and aged error survive.
    for (const auto& source : s)
        CHECK(r.frequency_bound >= source.skew + std::abs(source.rate - r.rate));
    CHECK(r.skew < r.frequency_bound);
    Config config;
    config.min_poll = config.max_poll = 6;
    config.max_clock_error_ppm = 50;
    Engine engine(config);
    CHECK(engine.configure(0, 1, 0) && engine.configure(1, 2, 0));
    for (unsigned i = 1; i <= 20; ++i) {
        CHECK(measurement(engine, 0, i * 64 * second, 0));
        CHECK(measurement(engine, 1, i * 64 * second + second / 5, .00003));
    }
    CHECK(measurement(engine, 0, 21 * 64 * second, 0));
    // A healthy peer one poll old is eligible under the same combine limit,
    // even on a short path with the Pico's conservative holdover allowance.
    CHECK(engine.tracking(21 * 64 * second + 1'000'000).combined_sources == 2);
}
void phase_change_preserves_frequency() {
    Config config;
    config.max_drift_ppm = 100;
    Engine e(config);
    CHECK(e.configure(0, 1, 0));
    for (unsigned i = 1; i <= 80; ++i) {
        CHECK(measurement(e, 0, i * 64 * second, i <= 64 ? 0 : .05));
        const auto t = e.tracking(i * 64 * second + 1'000'000);
        CHECK(t.synchronized == (i >= 3));
        CHECK(std::abs(t.utc_frequency_ppb) < 100); // Phase change, unchanged oscillator.
    }
    CHECK(e.history(0).size() == sample_capacity); // Pruning keeps original evidence.
    CHECK(e.history(0).front().id == 17 && e.history(0).back().id == 80);
    CHECK(e.status(0, 80 * 64 * second).estimate.samples < sample_capacity);
    // Reset/reconfiguration after pruning must clear both active and preceding
    // indices. Reusing a stale start would underflow a new source's window.
    e.reset(81 * 64 * second);
    for (unsigned i = 82; i <= 84; ++i)
        CHECK(measurement(e, 0, i * 64 * second, 0));
    CHECK(e.tracking(84 * 64 * second + 1'000'000).synchronized);
    CHECK(e.status(0, 84 * 64 * second).estimate.samples == 3);
    e.remove(0, 85 * 64 * second);
    CHECK(e.configure(0, 5, 85 * 64 * second));
    for (unsigned i = 86; i <= 88; ++i)
        CHECK(measurement(e, 0, i * 64 * second, 0));
    CHECK(e.tracking(88 * 64 * second + 1'000'000).synchronized);
}
void variable_delay_retention() {
    Config c;
    c.max_delay_deviation_ratio = 0; // Exercise statistics after packet admission.
    Engine e(c);
    CHECK(e.configure(0, 1, 0));
    for (unsigned i = 1; i <= 64; ++i) {
        const double queue = (i * 17 % 11) * .003;
        CHECK(measurement(e, 0, i * 64 * second, -20e-6 * i * 64 + queue / 2,
                          std::uint64_t(std::llround((.002 + queue) * 1e9))));
        if (i >= 13)
            CHECK(std::abs(e.status(0, i * 64 * second).estimate.rate + 20e-6) < 5e-9);
    }
    CHECK(e.history(0).size() == sample_capacity);
}
void predecessor_phase_rebase() {
    Config config;
    config.max_drift_ppm = 100;
    Engine e(config);
    CHECK(e.configure(0, 1, 0));
    // The deliberately out-of-range oscillator makes the compact phase cross
    // its signed 32-bit span. Rebase it without wrapping or raising authority.
    for (unsigned i = 1; i <= 200; ++i)
        CHECK(measurement(e, 0, i * 64 * second, i * 64 * .001));
    const auto now = 200 * 64 * second + 1'000'000;
    CHECK(e.history(0).size() == sample_capacity);
    CHECK(std::abs(e.status(0, now).estimate.rate - .001) < 1e-9);
    CHECK(e.tracking(now).utc_frequency_ppb == 100000);
    CHECK(e.tracking(now).skew_ppb >= 900000);
}
void stats_driver() {
    Engine engine;
    Config config;
    config.max_delay_deviation_ratio = 0; // Statistics-only comparison, same as SST input API.
    engine = Engine(config);
    CHECK(engine.configure(0, 1, 0));
    double when, offset, delay, dispersion;
    unsigned id = 0;
    while (std::cin >> when >> offset >> delay >> dispersion) {
        const auto midpoint = std::uint64_t(std::llround((when - 1'800'000'000.0) * 1e9));
        CHECK(measurement(engine, 0, midpoint, offset, std::uint64_t(std::llround(delay * 1e9)),
                          dispersion));
        const auto e = engine.status(0, midpoint).estimate;
        std::cout.precision(15);
        std::cout << ++id << ' ' << e.samples << ' ' << e.runs << ' ' << -e.rate << ' ' << e.rate_sd
                  << ' ' << e.skew << ' ' << e.offset_sd << ' ' << e.jitter << '\n';
    }
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "slew") {
        slew_driver();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "selection") {
        selection_driver();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "replay") {
        replay_driver();
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "stats") {
        stats_driver();
        return 0;
    }
    selection_hysteresis();
    control_rules();
    frequency_innovation();
    source_combination();
    phase_change_preserves_frequency();
    variable_delay_retention();
    predecessor_phase_rebase();
    learning();
    delay_and_loss();
    source_agreement();
    packets_and_polling();
    restoration();
    withdrawals();
    combined_bound();
    correlated_delay();
    std::cout << "microchrony deterministic checks passed; Engine bytes=" << sizeof(Engine) << '\n';
}
