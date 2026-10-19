// SPDX-License-Identifier: MIT
#include "time/clock_probe.hpp"
#include "wtp/json.hpp"

#include <cassert>
#include <iostream>

using namespace wsprrypico;
struct Hardware : time::ClockProbeHardware {
    unsigned reads = 0, pulses = 0;
    bool fault = false, bad_clock = false;
    bool slew_boundary = false;
    std::uint64_t bracket_ns = 2000;
    std::optional<time::ClockProbeInput> read() override {
        ++reads;
        if (fault)
            return {};
        return time::ClockProbeInput{false, false, 0x116, 0x02, 0x42, 5, 20'000, 1000, 20'001'000};
    }
    void pulse(time::ClockProbeRecord& r) override {
        ++pulses;
        r.rise_before = {wtp::ClockState::Synchronized,
                         1'000'000'000,
                         10'000'000,
                         1000,
                         1000,
                         wtp::LeapState::Normal,
                         {},
                         1500,
                         500,
                         7};
        r.rise_after = r.rise_before;
        r.rise_after.monotonic_now_ns += bracket_ns;
        r.rise_after.utc_now_ns += bracket_ns;
        if (slew_boundary) {
            r.rise_before.rate_ppb = r.rise_after.rate_ppb = 100'000'000;
            r.rise_before.rate_until_monotonic_ns = r.rise_after.rate_until_monotonic_ns =
                10'002'500;
            r.rise_before.subsequent_rate_ppb = r.rise_after.subsequent_rate_ppb = 1'000'000;
            r.rise_after.utc_now_ns = 1'000'002'200;
        }
        if (bad_clock)
            ++r.rise_after.model_generation;
        r.fall_before_ns = 11'002'000;
        r.fall_after_ns = 11'003'000;
        r.high_readback = !fault;
        r.low_readback = r.restored = true;
    }
};
int main() {
    // A physical edge can cross a finite slew end while expensive model
    // snapshots surround it. Exact projection must retain the narrow raw
    // bracket rather than charging snapshot computation time to that bracket.
    {
        wtp::ClockSnapshot before;
        before.state = wtp::ClockState::Synchronized;
        before.leap = wtp::LeapState::Normal;
        before.monotonic_now_ns = 10'000'000;
        before.utc_now_ns = 1'000'000'000;
        before.sync_age_ns = 1000;
        before.uncertainty_ns = 500;
        before.model_generation = 7;
        before.rate_ppb = 100'000'000;
        before.rate_until_monotonic_ns = 10'002'500;
        before.subsequent_rate_ppb = 1'000'000;
        auto after = before;
        after.monotonic_now_ns = 10'004'000;
        after.utc_now_ns = 1'000'004'251;
        after.rate_ppb = 1'000'000;
        after.rate_until_monotonic_ns = UINT64_MAX;
        after.uncertainty_ns = 900;
        time::ClockProbeRecord edge;
        assert(time::bind_probe_edge(edge, before, after, 10'002'000, 10'003'000));
        assert(edge.rise_before.monotonic_now_ns == 10'002'000);
        assert(edge.rise_after.monotonic_now_ns == 10'003'000);
        assert(edge.rise_before.utc_now_ns == 1'000'002'200);
        assert(edge.rise_after.utc_now_ns == 1'000'003'250);
        assert(edge.rise_before.rate_ppb == 100'000'000);
        assert(edge.rise_after.rate_ppb == 1'000'000);
        assert(edge.rise_after.rate_until_monotonic_ns == UINT64_MAX);
        assert(edge.rise_before.uncertainty_ns == 900 && edge.rise_after.sync_age_ns == 4000);
        ++after.model_generation;
        assert(!time::bind_probe_edge(edge, before, after, 10'002'000, 10'003'000));
        assert(edge.rise_before.state == wtp::ClockState::Unsynchronized);
        assert(edge.rise_after.monotonic_now_ns == 10'003'000 && edge.rise_after.utc_now_ns == 0);
        after.model_generation = before.model_generation;
        assert(!time::bind_probe_edge(edge, before, after, 9'999'000, 10'003'000));
        assert(!time::bind_probe_edge(edge, before, after, 10'002'000, 10'005'000));
    }
    time::ClockProbe p;
    Hardware hw;
    const time::ClockProbeBinding id{"device", "boot", "firmware", "revision"};
    time::ClockProbeGuard g;
    g.permitted = g.source_sntp = true;
    g.frequency_ppb = 700;
    const auto command = [&](std::string_view s, std::uint64_t now = 1'000'000'000) {
        auto result = p.command(s, id, g, now, hw);
        assert(wtp::json::parse(result));
        return result;
    };
    for (const auto* s : {"wrong boot READ", "device wrong READ", "device boot PULSE 0",
                          "device boot PULSE 01", "device boot PULSE +1", "device boot PULSE 1x",
                          "device boot PULSE 18446744073709551616", "device boot PULSE 1 extra",
                          "device  boot READ", "device boot READ ", "device boot READ extra"})
        assert(command(s).find("\"ok\":false") != std::string::npos);
    assert(hw.reads == 0 && hw.pulses == 0);
    g.permitted = false;
    assert(command("device boot READ").find("busy") != std::string::npos);
    assert(command("device boot PULSE 1").find("busy") != std::string::npos);
    assert(hw.reads == 0 && hw.pulses == 0);
    g.permitted = true;
    const auto input_reply = command("device boot READ");
    assert(input_reply.find("\"level\":false") != std::string::npos);
    const auto input = wtp::json::parse(input_reply);
    assert(input->get("output_enabled")->boolean() == false);
    assert(input->get("pad_sampling")->integer() == 0x42);
    assert(input->get("pad_settling")->integer() == 0x02);
    assert(input->get("control_sampling")->integer() == 5);
    assert(input->get("raw_after_ns")->string() == "20001000");
    hw.fault = true;
    assert(command("device boot READ").find("pin_fault") != std::string::npos);
    hw.fault = false;
    const auto original = command("device boot PULSE 1");
    assert(original.find("\"clock_valid\":true") != std::string::npos && hw.pulses == 1);
    const auto value = wtp::json::parse(original);
    assert(value->get("rise_raw_lower_ns")->string() == "10000000");
    assert(value->get("rise_raw_upper_ns")->string() == "10003000");
    assert(value->get("raw_resolution_ns")->integer() == 1000);
    // The physical upper bound crosses a finite slew boundary: 500 ns at
    // +10%, then 500 ns at +0.1%. It cannot be UTC-after plus a raw quantum.
    {
        time::ClockProbe boundary;
        Hardware hardware;
        hardware.slew_boundary = true;
        const auto reply = boundary.command("device boot PULSE 1", id, g, 0, hardware);
        const auto record = wtp::json::parse(reply);
        assert(record && record->get("clock_valid")->boolean());
        assert(record->get("rise_utc_upper_ns")->string() == "1000003250");
    }
    // The 50 us gate includes the timer's final microsecond, so a 50 us
    // sampled bracket is too wide even though its raw timestamp delta fits.
    for (const auto bracket : {49'000ULL, 50'000ULL}) {
        time::ClockProbe bounded;
        Hardware hardware;
        hardware.bracket_ns = bracket;
        const auto reply = bounded.command("device boot PULSE 1", id, g, 0, hardware);
        const auto record = wtp::json::parse(reply);
        assert(record && record->get("clock_valid")->boolean() == (bracket == 49'000));
    }
    // An ambiguous lost reply can be recovered, even if RF became busy, without
    // another physical edge or refreshed clock/frequency metadata.
    g.frequency_ppb = 12345;
    g.permitted = false;
    assert(command("device boot PULSE 1") == original && hw.pulses == 1);
    assert(command("device boot STATUS").find(original.substr(0, original.size() - 1)) !=
           std::string::npos);
    g.permitted = true;
    assert(command("device boot PULSE 2", 1'100'000'000).find("rate_limited") != std::string::npos);
    assert(command("device boot PULSE 2", 1).find("rate_limited") != std::string::npos);
    assert(command("device boot PULSE 3", 2'000'000'000).find("sequence") != std::string::npos);
    hw.fault = true;
    const auto failed = command("device boot PULSE 2", 2'000'000'000);
    assert(failed.find("pulse_hardware_fault") != std::string::npos && hw.pulses == 2);
    hw.fault = false;
    assert(command("device boot PULSE 2", 3'000'000'000) == failed && hw.pulses == 2);
    hw.bad_clock = true;
    assert(command("device boot PULSE 3", 3'000'000'000).find("\"clock_valid\":false") !=
           std::string::npos);
    hw.bad_clock = false;
    g.source_sntp = false;
    assert(command("device boot PULSE 4", 4'000'000'000).find("\"clock_valid\":false") !=
           std::string::npos);
    g.source_sntp = true;
    g.disagreement = true;
    assert(command("device boot PULSE 5", 5'000'000'000).find("\"clock_valid\":false") !=
           std::string::npos);
    for (std::uint64_t seq = 6; seq <= time::ClockProbe::maximum_pulses; ++seq)
        (void)command("device boot PULSE " + std::to_string(seq), seq * 1'000'000'000);
    assert(hw.pulses == time::ClockProbe::maximum_pulses);
    assert(command("device boot PULSE 4097", 5000ULL * 1'000'000'000).find("sequence") !=
           std::string::npos);
    assert(hw.pulses == time::ClockProbe::maximum_pulses);
    std::cout << "Clock probe identity, inactivity, bounded output, replay recovery and "
                 "invalid-clock checks passed\n";
}
