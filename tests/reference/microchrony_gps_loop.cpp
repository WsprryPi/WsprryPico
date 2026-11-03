// SPDX-License-Identifier: MIT
// Original physical-event adapter for the production GPS pairer and one Engine.
// No SDK, OS-clock writes, network IO, or fabricated NTP representation of GPS.
#include "microchrony.hpp"
#include "time/gps.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <optional>
namespace {
void put(std::array<std::uint8_t, 48>& p, unsigned start, unsigned size, std::uint64_t value) {
    for (unsigned i = 0; i < size; ++i) {
        p[start + size - i - 1] = std::uint8_t(value);
        value >>= 8;
    }
}
std::uint64_t ntp(std::uint64_t utc) {
    return ((utc / 1'000'000'000 + 2'208'988'800ULL) << 32) |
           ((utc % 1'000'000'000) << 32) / 1'000'000'000;
}
} // namespace
int main(int argc, char** argv) {
    if (argc != 3 || std::string_view(argv[2]) != "gps")
        return 2;
    microchrony::Config config;
    config.min_poll = config.max_poll = 6;
    config.max_drift_ppm = 100;
    config.max_clock_error_ppm = 50;
    microchrony::Engine engine(config);
    engine.seed(std::int32_t(std::llround(std::stod(argv[1]) * 1000)));
    for (unsigned i = 0; i < 4; ++i)
        if (!engine.configure(i, i + 1, 0))
            return 3;
    if (!engine.reference_clock(true, 0))
        return 4;
    wsprrypico::time::gps::PairingPolicy policy;
    policy.qualified = true;
    wsprrypico::time::gps::Pairer pairer(policy);
    std::array<std::optional<std::array<std::uint8_t, 48>>, 4> sent;
    std::uint64_t truth, raw, utc, sequence = 0, gps_sequence = 0;
    unsigned action, slot, stratum;
    std::cout.precision(15);
    while (std::cin >> truth >> raw >> action >> slot >> utc >> stratum) {
        if (slot > 4)
            return 5;
        if (slot == 4 && action == 1) {
            (void)pairer.pulse({raw, 50'000, ++gps_sequence});
        } else if (slot == 4 && action == 4) {
            wsprrypico::time::gps::Message message;
            message.utc_ns = utc;
            message.time_valid = true;
            message.received_raw_ns = raw;
            if (const auto observation = pairer.message(message))
                if (!engine.observe_reference({observation->raw_ns, observation->utc_ns,
                                               observation->uncertainty_ns, observation->sequence,
                                               microchrony::Leap::Normal},
                                              raw))
                    return 6;
        } else if (action == 5) {
            if (!engine.reference_clock(false, raw))
                return 7;
            pairer.lost();
        } else if (action == 6) {
            if (!engine.reference_clock(true, raw))
                return 8;
            pairer.lost();
        } else if (slot < 4 && action == 1) {
            sent[slot] = engine.request(slot, raw, ++sequence, true);
            if (!sent[slot])
                return 9;
        } else if (slot < 4 && action == 2) {
            if (!sent[slot])
                return 10;
            std::array<std::uint8_t, 48> p{};
            p[0] = 0x24;
            p[1] = std::uint8_t(stratum);
            p[3] = std::uint8_t(-20);
            std::copy(sent[slot]->begin() + 40, sent[slot]->end(), p.begin() + 24);
            put(p, 16, 8, ntp(utc - microchrony::second));
            put(p, 32, 8, ntp(utc));
            put(p, 40, 8, ntp(utc));
            if (!engine.receive(slot, p, raw))
                return 11;
            sent[slot].reset();
        } else if (action == 3) {
            if (slot < 4)
                sent[slot].reset();
        } else if (action != 0)
            return 12;
        if (action == 1)
            continue;
        engine.poll(raw);
        const auto t = engine.tracking(raw);
        const auto relative =
            t.utc_ns ? std::int64_t(t.utc_ns - 1'800'000'000ULL * microchrony::second) : INT64_MIN;
        const int selected = t.synchronized ? (t.reference_clock ? 4 : int(t.selected)) : -1;
        const auto samples = t.reference_clock ? engine.reference_status(raw).estimate.samples
                             : t.selected < 4  ? engine.status(t.selected, raw).estimate.samples
                                               : 0;
        std::cout << truth << ' ' << action << ' ' << relative << ' '
                  << t.utc_frequency_ppb / 1000.0 << ' ' << t.rate_ppb / 1000.0 << ' '
                  << t.remaining_correction_ns << ' ' << t.skew_ppb / 1000.0 << ' ' << selected
                  << ' ' << samples << '\n';
    }
}
