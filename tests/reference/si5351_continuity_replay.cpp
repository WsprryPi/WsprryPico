// SPDX-License-Identifier: MIT
// Offline production-policy replay of independently validated physical captures.
#include "rf/reference_measurement.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/controller_time.hpp"
#include "time/ntp_client.hpp"

#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace wsprrypico;
namespace {
constexpr std::uint64_t second = 1'000'000'000ULL, epoch = 1'800'000'000 * second;
struct Pulse {
    unsigned index;
    std::uint64_t low, high, count_low, count_high;
    std::uint64_t raw() const {
        return low * 1000 + (high - low) * 500;
    }
    std::uint64_t count() const {
        return count_low + (count_high - count_low) / 2;
    }
};
std::uint64_t now(void* p) {
    return *static_cast<std::uint64_t*>(p);
}
std::uint64_t difference(std::uint64_t a, std::uint64_t b) {
    return a > b ? a - b : b - a;
}
void require(bool condition, const char* message) {
    if (!condition)
        throw std::runtime_error(message);
}
std::uint64_t field(const std::string& text, const std::string& name) {
    require(text.starts_with(name + "="), "malformed pulse field");
    const auto value = text.substr(name.size() + 1);
    require(!value.empty() && value.find_first_not_of("0123456789") == std::string::npos,
            "malformed pulse number");
    return std::stoull(value);
}
} // namespace
int main(int argc, char** argv) {
    try {
        require(argc == 3,
                "usage: si5351_continuity_replay validated-transcript reference-allowance-ppb");
        const auto allowance = field(std::string("allowance=") + argv[2], "allowance");
        require(allowance > 0 && allowance <= 100000, "invalid reference allowance");
        std::ifstream input(argv[1]);
        require(bool(input), "capture unavailable");
        std::vector<Pulse> pulses;
        for (std::string line; std::getline(input, line);) {
            if (!line.starts_with("PULSE "))
                continue;
            std::istringstream row(line);
            std::string prefix, i, low, high, count_low, count_high, extra;
            require(bool(row >> prefix >> i >> low >> high >> count_low >> count_high) &&
                        !(row >> extra),
                    "malformed pulse row");
            Pulse p{unsigned(field(i, "i")), field(low, "raw_low"), field(high, "raw_high"),
                    field(count_low, "count_low"), field(count_high, "count_high")};
            require(pulses.size() < 301 && p.index == pulses.size() && p.low <= p.high &&
                        p.high <= UINT64_MAX / 1000 && p.high - p.low <= 100 &&
                        p.count_low <= p.count_high && p.count_high - p.count_low <= 100,
                    "invalid endpoint bounds");
            if (!pulses.empty()) {
                const auto& previous = pulses.back();
                require(p.low > previous.high && p.count_low > previous.count_high &&
                            p.raw() - previous.raw() > 999000000 &&
                            p.raw() - previous.raw() < 1001000000,
                        "invalid PPS sequence");
            }
            pulses.push_back(p);
        }
        require(pulses.size() == 301, "require 301 validated PPS edges");
        std::cout << "{\"reference_allowance_ppb\":" << allowance << ",\"cases\":[";
        bool first = true;
        for (unsigned scenario = 0; scenario < 3; ++scenario) {
            auto raw = pulses.front().raw();
            time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
            time::ControllerTimeArbiter arbiter(clock, now, &raw, "physical-capture");
            time::NtpClient client(arbiter);
            require(arbiter.observe(time::ObservationSource::Browser, epoch, raw,
                                    time::browser_clock_uncertainty_ns, wtp::LeapState::Normal, {},
                                    "fixture-epoch"),
                    "epoch rejected");
            rf::ReferencePolicy policy;
            policy.use = rf::ReferenceUse::TrustedLocal;
            policy.trusted_uncertainty_ppb = std::uint32_t(allowance);
            std::uint64_t maximum_error = 0;
            unsigned observations = 0;
            std::optional<microchrony::FrequencyReference> latest;
            for (unsigned i = 1; i < pulses.size(); ++i) {
                const auto& p = pulses[i];
                raw = p.raw();
                const bool capture =
                    i >= 20 && i % 20 == 0 &&
                    (scenario == 0 || i == 20 || (scenario == 1 && (i == 160 || i == 280)));
                if (capture) {
                    const auto& a = pulses[i - 20];
                    // Both the raw brackets AND count brackets contribute.
                    // Count uncertainty is converted outward at nominal 1 MHz;
                    // two extra ns cover midpoint/numerical rounding.
                    const auto endpoint =
                        (p.high - p.low + a.high - a.low) * 1000 +
                        (p.count_high - p.count_low + a.count_high - a.count_low) * 1000 + 2;
                    const auto measured = rf::measure_reference(
                        {a.raw(), raw, p.count() - a.count(), endpoint, 1, true}, 1000000, 1,
                        policy);
                    // The production measurement-quality filter is unchanged.
                    // Bracketed PPS endpoints are wider than production polls;
                    // use a sufficiently long window rather than relaxing it.
                    require(measured.valid() && measured.local_rate_ppb,
                            "capture rejected by production measurement policy");
                    latest = microchrony::FrequencyReference{
                        raw, raw + 30 * second, 1, *measured.local_rate_ppb,
                        std::uint32_t(std::ceil(measured.uncertainty_ppb)) + 1};
                    require(client.frequency_reference(latest, raw), "rate rejected");
                    ++observations;
                } else {
                    if (latest && latest->valid_until_raw_ns <= raw)
                        latest.reset();
                    (void)client.frequency_reference(latest, raw);
                }
                const auto model = clock.snapshot();
                const auto truth = epoch + i * second;
                const auto error = difference(model.utc_now_ns, truth);
                require(model.sync_age_ns == raw - pulses.front().raw(),
                        "epoch source rejuvenated");
                require(model.state != wtp::ClockState::Unsynchronized &&
                            error <= model.uncertainty_ns,
                        "reported bound does not cover independently measured elapsed error");
                maximum_error = std::max(maximum_error, error);
            }
            const auto model = clock.snapshot();
            const auto error = difference(model.utc_now_ns, epoch + 300 * second);
            const auto unassisted = difference(raw - pulses.front().raw(), 300 * second);
            if (!first)
                std::cout << ',';
            first = false;
            std::cout << "{\"case\":\""
                      << std::array{"continuous_observations", "wspr_shaped_gaps",
                                    "retained_280s"}[scenario]
                      << "\",\"observations\":" << observations
                      << ",\"unassisted_error_ns\":" << unassisted
                      << ",\"assisted_error_ns\":" << error
                      << ",\"maximum_assisted_error_ns\":" << maximum_error
                      << ",\"reported_uncertainty_ns\":" << model.uncertainty_ns
                      << ",\"epoch_age_ns\":" << model.sync_age_ns << '}';
        }
        std::cout << "]}\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
