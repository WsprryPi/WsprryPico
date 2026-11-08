// SPDX-License-Identifier: MIT
#include "hardware/gps_settings.hpp"
#include "microchrony.hpp"
#include "time/controller_time.hpp"
#include "time/gps.hpp"
#include "time/gps_calibration.hpp"
#include "time/gps_pairing_diagnostic.hpp"
#include "time/ntp_client.hpp"
#include "time/utc_discipline.hpp"

#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>

using namespace wsprrypico::time::gps;
namespace {
void pairing_trace() {
    const std::string status =
        R"({"serial_present":true,"pps_present":true,"time_valid":false,"position_valid":false,"satellites":8,"observation_raw_ns":"90000000000","age_ns":"0","position":null,"candidate_utc_ns":"1800000000000000000","candidate_raw_ns":"92105000000","candidate_pps_raw_ns":"92000000000","observations":96,"rejected_sentences":0,"dropped":0,"uart_errors":0,"irq_latency_ns":"0","maximum_irq_latency_ns":"0","capture_error_bound_ns":"0","capture_rejections":0,"error":"unpaired_utc"})";
    const auto value = pairing_diagnostic(status, 93'000'000'000);
    assert(value && value->raw_ns == 93'000'000'000 && value->observations == 96);
    assert(value->candidate_raw_ns - value->candidate_pps_ns == 105'000'000);
    assert(value->flags == 3 && pairing_diagnostic_errors[value->error] == "unpaired_utc");
    for (const auto& replacement :
         {std::string("-1"), std::string("4294967296"), std::string("1.5"), std::string("true"),
          std::string("\"96\"")}) {
        auto bad = status;
        bad.replace(bad.find("\"observations\":96"), 17, "\"observations\":" + replacement);
        assert(!pairing_diagnostic(bad, 1));
    }
    auto bad = status;
    bad.replace(bad.find("unpaired_utc"), 12, "unknown_error");
    assert(!pairing_diagnostic(bad, 1));
    assert(!pairing_diagnostic("[]", 1) && !pairing_diagnostic("{", 1));
    bad = status;
    bad.replace(bad.find("\"pps_present\":true"), 18, "\"pps_present\":1");
    assert(!pairing_diagnostic(bad, 1));
}
std::string sentence(std::string_view body) {
    unsigned check = 0;
    for (const auto c : body)
        check ^= unsigned(c);
    char suffix[8];
    std::snprintf(suffix, sizeof(suffix), "*%02X\r\n", check);
    return "$" + std::string(body) + suffix;
}
std::optional<Message> read(Parser& p, std::string_view wire, std::uint64_t start) {
    std::optional<Message> result;
    for (const auto c : wire) {
        if (auto message = p.byte(c, start))
            result = message;
        start += 1'100'000;
    }
    return result;
}
void parser() {
    Parser p;
    const auto wire = sentence("GNRMC,162829.00,A,3900.0000,N,09400.0000,W,0.0,0.0,021126,,,A");
    const auto m = read(p, wire, 100 * second);
    assert(m && m->time_valid && m->position_valid && m->utc_ns);
    assert(*m->utc_ns == 1'793'636'909ULL * second);
    assert(m->received_raw_ns == 100 * second);
    assert(m->position->latitude_e7 == 390'000'000);
    assert(m->position->longitude_e7 == -940'000'000);
    assert(std::string(locator(*m->position)->data()) == "EM39AA");
    auto damaged = wire;
    damaged[10] = 'X';
    assert(!read(p, damaged, 101 * second));
    const auto no_position =
        read(p, sentence("GPRMC,162830.00,A,,,,,0,0,021126,,,A"), 102 * second);
    assert(no_position && no_position->time_valid && !no_position->position_valid);
    const auto no_fix = read(p, sentence("GNGGA,162830.00,,,,,0,00,9.9,0,M,0,M,,"), 103 * second);
    assert(no_fix && !no_fix->position_valid && !no_fix->time_valid);
    assert(no_position->time_valid); // Independent observation domains.
    assert(!read(p, sentence("GPRMC,162860.00,A,,,,,0,0,021126,,,A"), 104 * second));
    assert(!read(p, sentence("GPRMC,162830.00,A,,,,,0,0,310226,,,A"), 105 * second));
    assert(!read(p, sentence("GPRMC,162830.00,A,,,,,0,0,311224,,,A"), 106 * second));
    assert(!read(p, sentence("ZZRMC,162830.00,A,,,,,0,0,021126,,,A"), 107 * second));
    const auto simulator = read(p, sentence("GPRMC,162830.00,A,,,,,0,0,021126,,,S"), 108 * second);
    assert(simulator && !simulator->time_valid);
    assert(!read(p, "$" + std::string(200, 'X') + "\r\n", 109 * second));
    assert(read(p, wire, 110 * second)); // Recover after overflow.
    assert(!read(p, wire.substr(0, 20), 111 * second));
    p.lost();
    assert(!read(p, wire.substr(20), 112 * second));
    assert(read(p, wire, 113 * second));
    const auto rejected = p.rejected();
    assert(!read(p, sentence("GPGSV,1,1,00"), 114 * second));
    assert(p.rejected() == rejected); // Routine unsupported sentences are ignored.
    assert(std::string(locator(Position{900'000'000, 1'800'000'000, 0})->data()) == "RR99XX");
    assert(std::string(locator(Position{-900'000'000, -1'800'000'000, 0})->data()) == "AA00AA");
    assert(!locator(Position{900'000'001, 0, 0}));
}
void pairing() {
    PairingPolicy policy;
    Pairer unqualified(policy);
    assert(unqualified.pulse({second, 1000, 1}));
    Message m;
    m.utc_ns = 1'800'000'000ULL * second;
    m.time_valid = true;
    m.received_raw_ns = second + 100'000'000;
    assert(!unqualified.message(m));
    policy.qualified = true;
    Pairer paired(policy);
    assert(paired.pulse({second, 1000, 1}));
    assert(!paired.message(m));
    assert(paired.pulse({2 * second, 1000, 2}));
    m.utc_ns = *m.utc_ns + second;
    m.received_raw_ns += second;
    const auto obs = paired.message(m);
    assert(obs && obs->raw_ns == 2 * second && obs->uncertainty_ns == 101'000);
    assert(!paired.message(m)); // A repeated sentence cannot refresh the pulse.
    assert(!paired.pulse({2 * second, 1000, 2}));
    assert(paired.pulse({3 * second, 1000, 3}));
    m.utc_ns = *m.utc_ns + second;
    m.received_raw_ns += second;
    assert(!paired.message(m)); // Reacquisition after invalid capture.
    assert(!paired.pulse({5 * second, 1000, 5}));
    m.utc_ns = *m.utc_ns + 2 * second;
    m.received_raw_ns += 2 * second;
    assert(!paired.message(m));
    assert(paired.pulse({6 * second, 1000, 6}));
    m.utc_ns = *m.utc_ns + second;
    m.received_raw_ns += second;
    assert(paired.message(m));
    assert(paired.pulse({7 * second, 1000, 7}));
    m.utc_ns = *m.utc_ns + 2 * second;
    m.received_raw_ns += second;
    assert(!paired.message(m)); // Plausible pulse, wrong associated UTC second.
    // The first '$' arrived before the next pulse, but parsing completed after
    // it. Select the earlier electrical edge, preserving consecutive seconds.
    auto crossing_policy = policy;
    crossing_policy.maximum_message_delay_ns = 999'000'000;
    Pairer crossing(crossing_policy);
    Message delayed;
    delayed.time_valid = true;
    delayed.utc_ns = 1'800'000'000ULL * second;
    delayed.received_raw_ns = second + 950'000'000;
    assert(crossing.pulse({second, 1000, 1}));
    assert(crossing.pulse({2 * second, 1000, 2}));
    assert(!crossing.message(delayed));
    delayed.received_raw_ns += second;
    *delayed.utc_ns += second;
    assert(crossing.pulse({3 * second, 1000, 3}));
    const auto crossed = crossing.message(delayed);
    assert(crossed && crossed->capture_raw_ns == 2 * second && crossed->sequence == 2);
    assert(!crossing.message(delayed)); // The retained edge is still one-use.
    crossing.lost();
    assert(!crossing.preceding_pulse(delayed.received_raw_ns));
    policy.edge_offset_ns = -500'000'000;
    Pairer overflowing(policy);
    assert(overflowing.pulse({UINT64_MAX - 10, 0, 1}));
    m.received_raw_ns = UINT64_MAX - 9;
    assert(!overflowing.message(m) && overflowing.error() == "invalid_pps_offset");
    Pairer future(policy);
    assert(future.pulse({second, 1000, 1}));
    m.received_raw_ns = second + 100'000'000;
    assert(!future.message(m) && future.error() == "future_pps_epoch");
    policy.edge_offset_ns = 0;
    Pairer invalid(policy);
    assert(invalid.pulse({second, 1000, 1}));
    m.received_raw_ns = second + 100'000'000;
    assert(!invalid.message(m));
    m.time_valid = false;
    assert(!invalid.message(m));
    m.time_valid = true;
    ++*m.utc_ns;
    assert(invalid.pulse({2 * second, 1000, 2}));
    m.received_raw_ns += second;
    assert(!invalid.message(m)); // Fractional RMC epochs cannot qualify a PPS second.
}
void late_label_pairing() {
    PairingPolicy policy;
    policy.qualified = true;
    policy.minimum_message_delay_ns = 600'000'000;
    policy.maximum_message_delay_ns = 1'200'000'000;
    assert(valid(policy));
    Pairer pairer(policy);
    Message m;
    m.time_valid = true;
    m.utc_ns = 1'800'000'000ULL * second;
    assert(pairer.pulse({second, 1000, 1}));
    assert(pairer.pulse({2 * second, 1000, 2}));
    m.received_raw_ns = second + 950'000'000;
    assert(!pairer.message(m));
    assert(pairer.pulse({3 * second, 1000, 3}));
    m.received_raw_ns = 3 * second + 25'000'000;
    *m.utc_ns += second;
    const auto late = pairer.message(m);
    assert(late && late->sequence == 2 && late->capture_raw_ns == 2 * second);
    assert(late->utc_ns == *m.utc_ns); // Keep the original PPS edge and UTC label.
    assert(!pairer.message(m));
    assert(pairer.pulse({4 * second, 1000, 4}));
    m.received_raw_ns = 3 * second + 990'000'000;
    *m.utc_ns += second;
    const auto before_edge = pairer.message(m);
    assert(before_edge && before_edge->capture_raw_ns == 3 * second);
    assert(pairer.pulse({5 * second, 1000, 5}));
    assert(pairer.pulse({6 * second, 1000, 6}));
    m.received_raw_ns = 5 * second + 50'000'000;
    *m.utc_ns += second;
    const auto queued = pairer.message(m);
    assert(queued && queued->capture_raw_ns == 4 * second);
    pairer.lost();
    assert(!pairer.message(m));
    Pairer varying_delay(policy);
    PpsCalibration calibration;
    unsigned captured = 0;
    for (unsigned i = 1; i <= 15; ++i) {
        while (captured < i + 1) {
            ++captured;
            assert(varying_delay.pulse({captured * (second + 10'000), 1000, captured}));
        }
        m.utc_ns = (1'800'000'000ULL + i) * second;
        m.received_raw_ns = i * (second + 10'000) + (i % 2 ? 980'000'000 : 1'020'000'000);
        if (const auto observation = varying_delay.message(m))
            calibration.observe(*observation, {}, 0);
    }
    assert(calibration.timer() && calibration.timer()->span_ns >= 10 * second);
    assert(std::abs(calibration.timer()->oscillator_error_ppb - 10'000) <= 1);
    // One out-of-window RMC can suppress two emitted observations: its own
    // label is refused and the next valid label only reacquires pairing.
    Pairer one_late_label(policy);
    captured = 0;
    unsigned emitted = 0;
    for (unsigned i = 1; i <= 6; ++i) {
        while (captured < i + 1) {
            ++captured;
            assert(one_late_label.pulse({captured * second, 1000, captured}));
        }
        m.utc_ns = (1'800'000'000ULL + i) * second;
        m.received_raw_ns = i * second + (i == 3 ? 1'250'000'000 : 1'050'000'000);
        const auto observation = one_late_label.message(m);
        if (observation) {
            assert(i == 2 || i == 5 || i == 6);
            ++emitted;
        }
        if (i == 3)
            assert(!observation && one_late_label.error() == "unpaired_utc");
        if (i == 4)
            assert(!observation && one_late_label.error() == "pairing_acquisition");
    }
    assert(emitted == 3);
    policy.minimum_message_delay_ns = 0;
    assert(!valid(policy)); // A window spanning multiple seconds is not qualified.
    policy.maximum_message_delay_ns = 999'000'000;
    Pairer ambiguous(policy);
    assert(ambiguous.pulse({second, 1000, 1}));
    assert(ambiguous.pulse({second + 999'000'000, 1000, 2}));
    m.received_raw_ns = second + 999'000'000;
    assert(!ambiguous.message(m) && ambiguous.error() == "ambiguous_utc");
    Pairer uncertain(policy);
    assert(uncertain.pulse({second, 2'000'000, 1}));
    assert(uncertain.pulse({2 * second, 2'000'000, 2}));
    m.received_raw_ns = 2 * second + 500'000;
    assert(!uncertain.message(m) && uncertain.error() == "ambiguous_utc");
    Pairer invalid_bound(policy);
    assert(!invalid_bound.pulse({1, 2, 1}));
    assert(!invalid_bound.pulse({UINT64_MAX - 1, 2, 1}));
    policy.minimum_message_delay_ns = second;
    policy.maximum_message_delay_ns = 2 * second - 1;
    assert(valid(policy));
    policy.maximum_message_delay_ns = 2 * second;
    assert(!valid(policy));
    // Boundaries include the permitted fast PPS cadence and delayed parsing.
    // A fifth edge must not evict the uniquely labelled original pulse.
    policy.minimum_message_delay_ns = 1'100'000'000;
    policy.maximum_message_delay_ns = 1'999'000'000;
    Pairer buffered(policy);
    for (unsigned i = 0; i < 5; ++i)
        assert(buffered.pulse({second + i * 999'000'000ULL, 1000, i + 1}));
    m.received_raw_ns = second + 1'998'998'000;
    m.utc_ns = 1'800'000'000ULL * second;
    assert(!buffered.message(m));
    assert(buffered.pulse({second + 5 * 999'000'000ULL, 1000, 6}));
    m.received_raw_ns += 999'000'000;
    *m.utc_ns += second;
    const auto oldest = buffered.message(m);
    assert(oldest && oldest->capture_raw_ns == second + 999'000'000);
}
void reference() {
    using microchrony::Engine;
    microchrony::Config config;
    config.max_clock_error_ppm = 50;
    config.max_drift_ppm = 100;
    for (const int error : {-20'000, 20'000}) {
        Engine e(config);
        assert(e.reference_clock(true, 0));
        std::uint64_t raw = 0;
        for (unsigned i = 1; i <= 120; ++i) {
            raw = i * (second + error);
            assert(e.observe_reference({raw, 1'800'000'000ULL * second + i * second, 100'000, i,
                                        microchrony::Leap::Normal},
                                       raw + 1000));
        }
        const auto value = e.tracking(raw + 1000);
        assert(value.synchronized && value.reference_clock);
        assert(std::abs(value.utc_frequency_ppb + error) < 100);
        const auto source_time = value.source_raw_ns;
        e.online(false, raw + second); // Wi-Fi loss must not remove GPS.
        assert(e.tracking(raw + second).reference_clock);
        e.poll(raw + 6 * second);
        const auto lost = e.tracking(raw + 6 * second);
        assert(!lost.synchronized && lost.source_raw_ns == source_time);
        assert(lost.uncertainty_ns > value.uncertainty_ns);
        assert(!e.observe_reference(
            {raw, 1'800'000'120ULL * second, 100'000, 120, microchrony::Leap::Normal},
            raw + 6 * second));
        assert(!e.observe_reference({raw + 7 * second, 1'800'000'127ULL * second, 100'000, 127,
                                     microchrony::Leap::Unsynchronized},
                                    raw + 7 * second));
        assert(e.reference_clock(false, raw + 7 * second));
        assert(e.reference_clock(true, raw + 8 * second));
        assert(!e.observe_reference(
            {raw, 1'800'000'120ULL * second, 100'000, 120, microchrony::Leap::Normal},
            raw + 8 * second));
    }
}
void delayed_reference() {
    microchrony::Engine engine;
    assert(engine.reference_clock(true, 0));
    for (unsigned i = 1; i <= 40; ++i) {
        const auto raw = std::uint64_t(i) * second;
        // A valid late RMC starts before the next edge and finishes afterward.
        assert(engine.observe_reference(
            {raw, 1'800'000'000ULL * second + raw, 200'000, i, microchrony::Leap::Normal},
            raw + 1'200'000'000));
    }
    const auto tracking = engine.tracking(41'200'000'000);
    assert(tracking.synchronized && tracking.reference_clock);
    assert(std::abs(std::int64_t(tracking.utc_ns) - std::int64_t(1'800'000'041'200'000'000ULL)) <
           2'000'000);
    assert(tracking.source_raw_ns == 40 * second); // Arrival never refreshes source age.
    assert(!engine.observe_reference(
        {41 * second, 1'800'000'041ULL * second, 200'000, 41, microchrony::Leap::Normal},
        44 * second + 1));
}
void calibration() {
    for (const int error : {-20'000, 20'000}) {
        PpsCalibration learner;
        for (unsigned i = 1; i <= 61; ++i) {
            const auto raw = i * (second + error);
            const Observation o{raw, 1'800'000'000ULL * second + i * second, 2000, i};
            // Deliberately different oscillator: Si5351 is fast by 10 ppm,
            // regardless of the sign of the Pico timer error.
            CycleSnapshot count{std::uint64_t(i) * 1'000'010, raw, 1000, 7, 9, true};
            assert(learner.observe(o, count, 1'000'000));
        }
        assert(learner.timer() && learner.synthesizer());
        assert(learner.timer()->oscillator_error_ppb == error);
        assert(learner.synthesizer()->oscillator_error_ppb == 10'000);
        const auto original = *learner.synthesizer();
        assert(original.fresh(original.observed_raw_ns + second, 60 * second));
        learner.lost();
        assert(learner.synthesizer()->observed_raw_ns == original.observed_raw_ns);
        assert(!original.fresh(original.observed_raw_ns + 61 * second, 60 * second));
        assert(original.uncertainty_at(original.observed_raw_ns + 3600 * second) ==
               original.uncertainty_ppb + 50'000);
        assert(original.uncertainty_at(UINT64_MAX) == UINT32_MAX);
        assert(original.uncertainty_at(original.observed_raw_ns - 1) == UINT32_MAX);
        assert(!learner.observe({second, 1'800'000'001ULL * second, 2000, 1}, {}, 1'000'000));
    }
    // IRQ delivery changes the count endpoint, not the synthesizer oscillator.
    // Use known physical time and two independent oscillator errors.
    for (const int error : {-20'000, 20'000}) {
        PpsCalibration delayed;
        for (unsigned i = 1; i <= 61; ++i) {
            const auto raw = std::uint64_t(i) * (second + error);
            const auto delay = i % 2 ? 200'000ULL : 1000ULL;
            const auto truth = i * static_cast<long double>(second) + delay / (1 + error / 1e9L);
            const auto edges = std::uint64_t(std::floor(truth * 1'000'010 / second));
            const CycleSnapshot count{edges, raw + delay, delay + 1000, 1, 1, true};
            assert(delayed.observe({raw, 1'800'000'000ULL * second + i * second, 2000, i, raw},
                                   count, 1'000'000));
            if (i >= 11)
                assert(delayed.synthesizer() &&
                       std::abs(delayed.synthesizer()->oscillator_error_ppb - 10'000) <= 100);
        }
    }
    // Frequent independently owned counter restarts cannot retire the Pico
    // timer's own PPS history or prevent its sixty-second estimate.
    {
        PpsCalibration restarting;
        for (unsigned i = 1; i <= 61; ++i) {
            const auto raw = std::uint64_t(i) * second;
            const CycleSnapshot count{
                std::uint64_t(i % 3) * 1'000'000, raw, 1000, 1, i / 3 + 1, true};
            assert(restarting.observe({raw, 1'800'000'000ULL * second + raw, 2000, i, raw}, count,
                                      1'000'000));
        }
        assert(restarting.timer() && restarting.timer()->span_ns == 60 * second);
        assert(!restarting.synthesizer());
    }
    assert(compose_correction(20'000, -1000) == 19'000);
    assert(compose_correction(100'000, -100'000) == -10);
    assert(!compose_correction(90'000, 20'000));
    // Equinox at Greenwich, independent midnight/noon and polar summer/winter.
    constexpr auto equinox = 1'774'007'200ULL * second; // 2026-03-20 12:00 UTC.
    assert(wsprrypico::time::gps::daylight(Position{0, 0, 0}, equinox) == true);
    assert(wsprrypico::time::gps::daylight(Position{0, 0, 0}, equinox - 12 * 3600 * second) ==
           false);
    assert(wsprrypico::time::gps::daylight(Position{900'000'000, 0, 0},
                                           1'782'043'200ULL * second) == true);
    assert(wsprrypico::time::gps::daylight(Position{900'000'000, 0, 0},
                                           1'797'854'400ULL * second) == false);
    assert(!wsprrypico::time::gps::daylight(Position{900'000'001, 0, 0}, equinox));
}
void allocation() {
    using namespace wsprrypico::hardware;
    GpsSettings s;
    s.enabled = true;
    assert(validate_gps(PinPlan{}, {}, s).empty());
    const auto text = serialize_gps(s);
    assert(parse_gps(text) == s);
    assert(!parse_gps(text.substr(0, text.size() - 1) + ",\"extra\":true}"));
    auto late = s;
    late.minimum_message_delay_ms = 600;
    late.maximum_message_delay_ms = 1200;
    assert(validate_gps_settings(late).empty() && parse_gps(serialize_gps(late)) == late);
    late.minimum_message_delay_ms = 0;
    assert(validate_gps_settings(late) == "invalid_gps_policy");
    late.minimum_message_delay_ms = 1000;
    late.maximum_message_delay_ms = 2000;
    assert(validate_gps_settings(late) == "invalid_gps_policy");
    auto conflict = PinPlan{};
    conflict.button = s.pps_gp;
    assert(validate_gps(conflict, {}, s) == "gps_pin_conflict");
    s.tx_gp = 0;
    assert(validate_gps_settings(s) == "unsupported_gps_transmit");
    s.receiver = GpsSettings::Receiver::E108;
    assert(validate_gps_settings(s).empty());
    s.tx_gp = 4;
    assert(validate_gps_settings(s) == "unsupported_gps_transmit"); // Different UART.
    s.tx_gp.reset();
    s.automatic_rf_calibration = true;
    assert(validate_gps_settings(s) == "gps_required");
    s.pairing_qualified = true;
    assert(validate_gps_settings(s).empty());
    auto even = s;
    even.pps_gp = 6;
    assert(validate_gps_settings(even) == "invalid_gps_pins");
    PinPlan i2c;
    i2c.engine = PinPlan::Engine::I2c;
    i2c.rf.reset();
    i2c.i2c_pair = 1;
    Si5351Settings si;
    si.synthesis.reference_hz = 25'000'000;
    si.synthesis.reference = wsprrypico::rf::si5351::Reference::ExternalXa;
    si.loopback_input = 7;
    si.synthesis.loopback = wsprrypico::rf::si5351::Output::Clk2;
    assert(validate_gps(i2c, si, s).empty());
    si.loopback_input = 19; // GP19 and PPS GP3 alias the same complete PWM slice.
    assert(validate_gps(i2c, si, s) == "invalid_si5351_allocation");
}
void utc_horizon() {
    using namespace std::chrono;
    constexpr auto transition =
        std::uint64_t(sys_days{year{2026} / December / 1}.time_since_epoch().count()) * 86400ULL *
        second;
    assert(utc_valid_until(transition - 6 * second) == transition - 5 * second);
    assert(!utc_valid_until(transition - 5 * second));
    assert(!utc_valid_until(transition + 4 * second));
    assert(utc_valid_until(transition + 5 * second));
    std::uint64_t raw = 100 * second;
    wsprrypico::time::UtcDiscipline clock([](void* p) { return *static_cast<std::uint64_t*>(p); },
                                          &raw);
    wsprrypico::time::NtpClient client(clock);
    assert(client.reference_clock(true, raw));
    for (unsigned i = 1; i <= 60; ++i) {
        raw += second;
        assert(client.reference_observation(
            {raw, transition - (120 - i) * second, 100'000, i, microchrony::Leap::Normal}, raw));
    }
    auto value = clock.snapshot();
    assert(value.state == wsprrypico::wtp::ClockState::Synchronized);
    assert(value.valid_until_utc_ns == transition - 5 * second);
    raw += 58 * second;
    value = clock.snapshot();
    assert(value.state == wsprrypico::wtp::ClockState::Unsynchronized);
    assert(value.leap == wsprrypico::wtp::LeapState::Unknown);
    // Advancing into the next month cannot renew an old GPS model.
    raw += 20 * second;
    assert(clock.snapshot().state == wsprrypico::wtp::ClockState::Unsynchronized);
}
void arbitration() {
    using namespace wsprrypico;
    std::uint64_t raw = 0;
    const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    time::UtcDiscipline clock(now, &raw);
    time::ControllerTimeArbiter arbiter(clock, now, &raw, "gps-test");
    time::NtpClient client(arbiter);
    assert(client.reference_clock(true, raw));
    for (unsigned i = 1; i <= 60; ++i) {
        raw = i * second;
        assert(client.reference_observation(
            {raw, 1'800'000'000ULL * second + raw, 150'000, i, microchrony::Leap::Normal}, raw));
    }
    client.online(false, raw);
    raw += 120 * second;
    assert(clock.snapshot().state == wtp::ClockState::Holdover);
    assert(arbiter.status().source == time::ActiveTimeSource::Gps);
    assert(!arbiter.observe(time::ObservationSource::Browser, clock.snapshot().utc_now_ns, raw,
                            250'000'000, wtp::LeapState::Normal, {}, "phone"));
    // Explicit removal revokes the GPS epoch; loss alone retained holdover.
    assert(client.reference_clock(false, raw));
    assert(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    assert(arbiter.status().source == time::ActiveTimeSource::None);
    raw += second;
    assert(arbiter.observe(time::ObservationSource::Browser, 1'800'000'000ULL * second + raw, raw,
                           250'000'000, wtp::LeapState::Normal, {}, "phone"));
    // Removing a different source cannot invalidate a healthy selected epoch.
    clock.invalidate(time::ObservationSource::Gps);
    assert(clock.snapshot().state != wtp::ClockState::Unsynchronized);
}
} // namespace
int main() {
    pairing_trace();
    parser();
    pairing();
    late_label_pairing();
    reference();
    delayed_reference();
    calibration();
    allocation();
    utc_horizon();
    arbitration();
    std::cout << "GPS parsing, separate validity, pairing, locator, and reference holdover passed; "
                 "Engine bytes="
              << sizeof(microchrony::Engine) << '\n';
}
