// SPDX-License-Identifier: MIT
// Original deterministic physical-event adapter; all clock control is Engine.
#include "microchrony.hpp"

#include <charconv>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

namespace microchrony {
struct ClockLoopTestAccess {
    static void rtc(Engine& engine) {
        engine.clock_valid_ = true;
        engine.clock_raw_ns_ = 0;
        engine.clock_utc_ns_ = 1'800'000'000ULL * second;
    }
};
} // namespace microchrony

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
int packet_driver() {
    microchrony::Config config;
    config.min_poll = config.max_poll = 6;
    config.max_clock_error_ppm = 50;
    config.max_drift_ppm = 100;
    config.max_update_skew_ppm = 1e-12; // Isolate admission with the same fixed raw clock.
    microchrony::Engine engine(config);
    if (!engine.configure(0, 1, 0))
        return 21;
    std::string line;
    std::uint64_t previous_send = UINT64_MAX;
    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        unsigned id;
        std::uint64_t send, receive, token;
        std::string nonce, hex;
        if (!(input >> id >> send >> receive >> nonce >> hex) || nonce.size() != 16 ||
            (hex != "-" && hex.size() % 2) || hex.size() > 2048 || receive < send)
            return 22;
        auto parsed = std::from_chars(nonce.data(), nonce.data() + nonce.size(), token, 16);
        if (parsed.ec != std::errc{} || parsed.ptr != nonce.data() + nonce.size() || !token)
            return 23;
        std::array<std::uint8_t, 1024> packet{};
        for (unsigned i = 0; hex != "-" && i < hex.size() / 2; ++i) {
            unsigned value;
            const char* begin = hex.data() + 2 * i;
            auto p = std::from_chars(begin, begin + 2, value, 16);
            if (p.ec != std::errc{} || p.ptr != begin + 2)
                return 24;
            packet[i] = std::uint8_t(value);
        }
        if (send != previous_send) {
            if (!engine.request(0, send, token, true))
                return 25;
            previous_send = send;
        }
        const bool accepted =
            hex != "-" && engine.receive(0, {packet.data(), hex.size() / 2}, receive);
        const auto status = engine.status(0, receive);
        std::cout << id << ' ' << accepted << ' ' << microchrony::name(status.reason) << ' '
                  << status.estimate.samples << ' ' << status.rejected << '\n';
    }
    return 0;
}
int raw_stats_driver() {
    microchrony::Config config;
    config.max_delay_deviation_ratio = 0; // SST entry boundary, not a packet-admission test.
    config.max_update_skew_ppm = 1e-12;
    config.max_clock_error_ppm = 50;
    microchrony::Engine engine(config);
    if (!engine.configure(0, 1, 0))
        return 30;
    std::uint64_t send, receive, utc, id = 0;
    std::cout.precision(15);
    while (std::cin >> send >> receive >> utc) {
        const auto request = engine.request(0, send, ++id, true);
        if (!request)
            return 31;
        std::array<std::uint8_t, 48> packet{};
        packet[0] = 0x24;
        packet[1] = 1;
        packet[3] = std::uint8_t(-20);
        std::copy(request->begin() + 40, request->end(), packet.begin() + 24);
        put(packet, 16, 8, ntp(utc - microchrony::second));
        put(packet, 32, 8, ntp(utc));
        put(packet, 40, 8, ntp(utc));
        if (!engine.receive(0, packet, receive))
            return 32;
        const auto e = engine.status(0, receive).estimate;
        std::cout << id << ' ' << e.samples << ' ' << e.runs << ' ' << -e.rate << ' ' << e.rate_sd
                  << ' ' << e.skew << ' ' << e.offset_sd << ' ' << e.jitter << ' ' << e.asymmetry
                  << '\n';
    }
    return 0;
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "packet")
        return packet_driver();
    if (argc == 2 && std::string(argv[1]) == "raw")
        return raw_stats_driver();
    if (argc != 2 && argc != 3)
        return 2;
    const bool captured_phase = argc == 3 && std::string(argv[2]) == "captured-phase";
    const bool phase_only = captured_phase || (argc == 3 && std::string(argv[2]) == "phase");
    const bool rtc = argc == 3 && std::string(argv[2]) == "captured-rtc";
    const bool captured =
        argc == 3 && (std::string(argv[2]) == "captured" || captured_phase || rtc);
    if (argc == 3 && !captured && !phase_only)
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
    if (captured)
        c.max_delay_deviation_ratio = 0; // Both captured adapters enter after packet admission.
    if (phase_only)
        c.max_update_skew_ppm = 1e-12; // Offline counterfactual; production gates are unchanged.
    microchrony::Engine engine(c);
    engine.seed(std::int32_t(std::llround(std::stod(argv[1]) * 1000)));
    for (unsigned i = 0; i < 4; ++i)
        if (!engine.configure(i, i + 1, 0))
            return 3;
    if (rtc)
        microchrony::ClockLoopTestAccess::rtc(engine);
    std::array<std::optional<std::array<std::uint8_t, 48>>, 4> sent;
    std::uint64_t truth, raw, server, sequence = 0;
    unsigned action, slot, stratum;
    std::cout.precision(15);
    while (std::cin >> truth >> raw >> action >> slot >> server >> stratum) {
        if (slot >= 4)
            return 4;
        auto server_receive = server, server_reference = server ? server - microchrony::second : 0;
        std::uint32_t root_delay = 0, root_dispersion = 0;
        int precision = -20, leap = 0;
        if (captured && !(std::cin >> server_receive >> server_reference >> root_delay >>
                          root_dispersion >> precision >> leap))
            return 10;
        if (precision < -40 || precision > 0 || leap < 0 || leap > 3)
            return 10;
        if (action == 1) {
            sent[slot] = engine.request(slot, raw, ++sequence, true);
            if (!sent[slot])
                return 5;
        } else if (action == 2) {
            if (!sent[slot])
                return 6;
            std::array<std::uint8_t, 48> p{};
            p[0] = std::uint8_t(0x24 | (leap << 6));
            p[1] = std::uint8_t(stratum);
            p[3] = std::uint8_t(precision);
            put(p, 4, 4, root_delay);
            put(p, 8, 4, root_dispersion);
            std::copy(sent[slot]->begin() + 40, sent[slot]->end(), p.begin() + 24);
            put(p, 16, 8, ntp(server_reference));
            put(p, 32, 8, ntp(server_receive));
            put(p, 40, 8, ntp(server));
            if (!engine.receive(slot, p, raw)) {
                std::cerr << "rejected at " << truth << ": "
                          << microchrony::name(engine.status(slot, raw).reason) << '\n';
                if (!captured)
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
                              << ' ' << s.selection_score << ' ' << e.asymmetry;
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
                      << (t.selected < 4 ? engine.status(t.selected, raw).estimate.samples : 0);
            if (captured)
                std::cout << ' ' << t.uncertainty_ns << ' '
                          << (raw >= t.source_raw_ns ? raw - t.source_raw_ns : UINT64_MAX);
            std::cout << '\n';
        }
    }
}
