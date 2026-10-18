// SPDX-License-Identifier: MIT
// Original deterministic physical-event adapter; all clock control is Engine.
#include "microchrony.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

namespace {
void put(std::array<std::uint8_t, 48>& packet, unsigned start, unsigned count,
         std::uint64_t value) {
    for (unsigned i = 0; i < count; ++i)
        packet[start + count - i - 1] = std::uint8_t(value >> (8 * i));
}
std::uint64_t ntp(std::uint64_t ns) {
    return (((ns / microchrony::second) + 2'208'988'800ULL) << 32) |
           ((ns % microchrony::second) << 32) / microchrony::second;
}
} // namespace
int main(int argc, char** argv) {
    if (argc != 2)
        return 2;
#ifndef MICROCHRONY_LOOP_BASELINE
    if (std::string(argv[1]) == "combination") {
        unsigned count;
        std::cout.precision(15);
        while (std::cin >> count) {
            if (!count || count > microchrony::source_capacity)
                return 8;
            std::array<microchrony::SourceEstimate, microchrony::source_capacity> sources;
            for (unsigned i = 0; i < count; ++i) {
                auto& s = sources[i];
                if (!(std::cin >> s.offset >> s.offset_sd >> s.rate >> s.rate_sd >> s.skew >>
                      s.distance >> s.age))
                    return 9;
            }
            const auto r = microchrony::combine_sources({sources.data(), count});
            std::cout << r.offset << ' ' << r.offset_sd << ' ' << r.rate << ' ' << r.rate_sd << ' '
                      << r.skew << ' ' << r.frequency_bound << '\n';
        }
        return 0;
    }
    if (std::string(argv[1]) == "frequency") {
        double old_skew, new_skew, innovation;
        std::cout.precision(15);
        while (std::cin >> old_skew >> new_skew >> innovation) {
            const auto result =
                microchrony::combine_frequency({0, old_skew}, {innovation, new_skew});
            std::cout << result.rate << ' ' << result.skew << '\n';
        }
        return 0;
    }
#endif
    microchrony::Config c;
    c.min_poll = c.max_poll = 6;
    c.max_drift_ppm = 100;
    c.max_clock_error_ppm = 50;
    microchrony::Engine engine(c);
    engine.seed(std::int32_t(std::llround(std::stod(argv[1]) * 1000)));
    for (unsigned i = 0; i < 4; ++i)
        if (!engine.configure(i, i + 1, 0))
            return 3;
    std::array<std::optional<std::array<std::uint8_t, 48>>, 4> sent;
    std::uint64_t truth, raw, server, sequence = 0;
    unsigned action, slot, stratum;
    std::cout.precision(15);
    while (std::cin >> truth >> raw >> action >> slot >> server >> stratum) {
        if (slot >= 4)
            return 4;
        if (action == 1) {
            sent[slot] = engine.request(slot, raw, ++sequence, true);
            if (!sent[slot])
                return 5;
        } else if (action == 2) {
            if (!sent[slot])
                return 6;
            std::array<std::uint8_t, 48> p{};
            p[0] = 0x24;
            p[1] = std::uint8_t(stratum);
            p[3] = std::uint8_t(-20);
            std::copy(sent[slot]->begin() + 40, sent[slot]->end(), p.begin() + 24);
            put(p, 16, 8, ntp(server - microchrony::second));
            put(p, 32, 8, ntp(server));
            put(p, 40, 8, ntp(server));
            if (!engine.receive(slot, p, raw)) {
                std::cerr << "rejected at " << truth << ": "
                          << microchrony::name(engine.status(slot, raw).reason) << '\n';
                return 7;
            }
            sent[slot].reset();
        } else if (action == 3) {
            // A request already shifted reach; no response must not rejuvenate it.
            sent[slot].reset();
        }
        if (action != 1) {
            const auto t = engine.tracking(raw);
            if (action == 2 && std::getenv("MICROCHRONY_DIAGNOSTICS")) {
                std::cerr.precision(15);
                std::cerr << "D " << truth << ' ' << slot << ' ' << t.remaining_correction_ns / 1e9
                          << " 0 0";
                for (unsigned i = 0; i < 4; ++i) {
                    const auto s = engine.status(i, raw);
                    const auto& e = s.estimate;
                    const double age = raw >= e.raw_ns ? (raw - e.raw_ns) / 1e9 : 0;
                    const double error =
                        e.utc_ns
                            ? (std::int64_t(e.utc_ns - 1'800'000'000ULL * microchrony::second) -
                               std::int64_t(truth)) /
                                      1e9 +
                                  age * (1 + e.rate)
                            : 0;
                    std::cerr << ' ' << e.samples << ' ' << e.runs << ' ' << e.rate * 1e6 << ' '
                              << e.rate_sd * 1e6 << ' ' << e.skew * 1e6 << ' ' << e.offset_sd << ' '
                              << error << ' '
                              << (s.selected   ? '*'
                                  : s.combined ? '+'
                                               : '-')
                              << ' ' << s.selection_score;
                }
                std::cerr << '\n';
            }
            const auto utc = t.utc_ns
                                 ? std::int64_t(t.utc_ns - 1'800'000'000ULL * microchrony::second)
                                 : INT64_MIN;
            std::cout << truth << ' ' << action << ' ' << utc << ' ' << t.utc_frequency_ppb / 1000.0
                      << ' ' << t.rate_ppb / 1000.0 << ' ' << t.remaining_correction_ns << ' '
                      << t.skew_ppb / 1000.0 << ' ' << (t.synchronized ? int(t.selected) : -1)
                      << ' '
                      << (t.selected < 4 ? engine.status(t.selected, raw).estimate.samples : 0)
                      << '\n';
        }
    }
}
