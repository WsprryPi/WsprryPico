// SPDX-License-Identifier: MIT
#include "sdk.hpp"
#include "time/capture_gap.hpp"
#include "time/pico/gps_input.hpp"
#include "wtp/json.hpp"

#include <cstdio>
#include <vector>
using namespace wsprrypico;
namespace {
std::string sentence(unsigned second, bool valid = true) {
    char text[100];
    std::snprintf(text, sizeof(text),
                  "GNRMC,1200%02u.00,%c,3900.0000,N,09400.0000,W,0,0,021126,,,A", second,
                  valid ? 'A' : 'V');
    unsigned sum = 0;
    for (const char* p = text; *p; ++p)
        sum ^= unsigned(*p);
    char suffix[8];
    std::snprintf(suffix, sizeof(suffix), "*%02X\r\n", sum);
    return "$" + std::string(text) + suffix;
}
std::vector<time::gps::Observation> received;
void observe(const time::gps::Observation& o, void*) {
    received.push_back(o);
}
void pulse(time::PicoGpsInput& input, unsigned i, bool rising = true) {
    const auto edge = std::uint64_t(i) * 1'000'000;
    // Feed the inactive edge too: hardware gating must reset while inactive,
    // never at the selected edge. Allow delivery latency independent of edges.
    const auto opposite = rising ? edge - 900'000 : edge - 100'000;
    gps_mock::edge(3, !rising, opposite);
    gps_mock::us = opposite + gps_mock::irq_delay_us;
    input.pps_interrupt();
    gps_mock::edge(3, rising, edge);
    gps_mock::us = edge + gps_mock::irq_delay_us;
    input.pps_interrupt();
}
void serial(time::PicoGpsInput& input, std::string_view text) {
    gps_mock::us += 100'000;
    for (const auto c : text) {
        gps_mock::receive.push_back(std::uint8_t(c));
        input.uart_interrupt();
        gps_mock::us += 1100;
    }
}
void poll(time::PicoGpsInput& input) {
    input.poll(gps_mock::us * 1000, observe, nullptr);
}
} // namespace
int main() {
    time::PicoGpsInput input, other;
    hardware::GpsSettings s;
    s.enabled = true;
    s.pairing_qualified = true;
    assert(input.open({}, {}, s));
    assert(!other.open({}, {}, s));
    assert(gps_mock::sent.empty()); // Receive-only QLG3, including peripheral handovers.
    pulse(input, 1);
    serial(input, sentence(1));
    poll(input);
    assert(received.empty());
    pulse(input, 2);
    serial(input, sentence(2));
    poll(input);
    assert(received.size() == 1);
    const auto original = received.back();
    for (unsigned i = 0; i < 100; ++i)
        poll(input);
    assert(received.size() == 1 && input.last_observation()->raw_ns == original.raw_ns);
    // Checksum failures break acquisition, even when their next RMC is plausible.
    pulse(input, 3);
    auto bad = sentence(3);
    bad[9] = 'X';
    serial(input, bad);
    poll(input);
    pulse(input, 4);
    serial(input, sentence(4));
    poll(input);
    assert(received.size() == 1);
    pulse(input, 5);
    serial(input, sentence(5));
    poll(input);
    assert(received.size() == 2);
    // Queue overflow discards both sides of the gap, then requires two new pairs.
    pulse(input, 6);
    serial(input, std::string(400, 'X'));
    poll(input);
    assert(input.status(gps_mock::us * 1000).find("\"dropped\":0") == std::string::npos);
    pulse(input, 7);
    serial(input, sentence(7));
    poll(input);
    assert(received.size() == 2);
    pulse(input, 8);
    serial(input, sentence(8));
    poll(input);
    assert(received.size() == 3);
    // UART framing errors cannot silently bridge acquisition.
    pulse(input, 9);
    gps_mock::receive.push_back(0x100 | '$');
    input.uart_interrupt();
    poll(input);
    pulse(input, 10);
    serial(input, sentence(10));
    poll(input);
    assert(received.size() == 3);
    pulse(input, 11);
    serial(input, sentence(11));
    poll(input);
    assert(received.size() == 4);
    gps_mock::us += 31'000'000;
    assert(!input.position(gps_mock::us * 1000));
    input.close();
    assert(!gps_mock::enabled[0]);
    assert(other.open({}, {}, s));
    assert(!other.last_observation());
    other.close();
    // Optional receiver command is finite; failed send relinquishes ownership.
    s.receiver = hardware::GpsSettings::Receiver::E108;
    s.tx_gp = 0;
    gps_mock::writable = false;
    assert(!input.open({}, {}, s));
    assert(!gps_mock::enabled[0]);
    gps_mock::writable = true;
    assert(other.open({}, {}, s));
    assert(gps_mock::sent.starts_with("$PGKC161,1,100,1000*"));
    other.close();
    assert(!gps_mock::direction[1] && !gps_mock::direction[3]);
    // The production IRQ adapter selects one polarity; the opposite edge
    // cannot supply a PPS sequence or establish UTC.
    s.receiver = hardware::GpsSettings::Receiver::Qlg3;
    s.tx_gp.reset();
    s.pps_active_high = false;
    received.clear();
    assert(input.open({}, {}, s));
    pulse(input, 1);
    serial(input, sentence(1));
    poll(input);
    assert(received.empty());
    pulse(input, 2, false);
    serial(input, sentence(2));
    poll(input);
    assert(received.empty());
    pulse(input, 3, false);
    serial(input, sentence(3));
    poll(input);
    assert(received.size() == 1 &&
           std::abs(std::int64_t(received[0].raw_ns) - 3'000'000'000LL) < 10'000);
    {
        time::CaptureGap flash;
        {
            time::CaptureGap nested;
            pulse(input, 4, false);
            serial(input, sentence(4));
        }
        pulse(input, 5, false);
        serial(input, sentence(5));
    }
    poll(input);
    assert(received.size() == 1 && input.last_observation()->raw_ns == received[0].raw_ns);
    pulse(input, 6, false);
    serial(input, sentence(6));
    poll(input);
    assert(received.size() == 1);
    pulse(input, 7, false);
    serial(input, sentence(7));
    poll(input);
    assert(received.size() == 2 &&
           std::abs(std::int64_t(received.back().raw_ns) - 7'000'000'000LL) < 10'000);
    // A complete queued pair before a flash gap is also retired, even if the
    // IRQ timestamp itself preceded the masked interval.
    pulse(input, 8, false);
    serial(input, sentence(8));
    {
        time::CaptureGap flash;
    }
    poll(input);
    assert(received.size() == 2);
    pulse(input, 9, false);
    serial(input, sentence(9));
    poll(input);
    assert(received.size() == 2);
    pulse(input, 10, false);
    serial(input, sentence(10));
    poll(input);
    assert(received.size() == 3);
    // Alternating 5 us and 20 ms IRQ delivery must not move the electrical
    // timestamp or destroy consecutive one-second observations.
    for (unsigned i = 11; i <= 14; ++i) {
        gps_mock::irq_delay_us = i % 2 ? 20'000 : 5;
        pulse(input, i, false);
        serial(input, sentence(i));
        poll(input);
        assert(received.size() == i - 7);
        assert(std::abs(std::int64_t(received.back().raw_ns) - std::int64_t(i) * 1'000'000'000) <
               10'000);
    }
    const auto status_text = input.status(gps_mock::us * 1000);
    auto status = wtp::json::parse(status_text);
    assert(status && std::stoull(status->get("maximum_irq_latency_ns")->string()) >= 19'000'000);
    assert(std::stoull(status->get("capture_error_bound_ns")->string()) <= 100'000);
    gps_mock::irq_delay_us = 130'000;
    pulse(input, 15, false);
    serial(input, sentence(15));
    poll(input);
    assert(received.size() == 7); // Wrapped hardware count is never guessed.
    gps_mock::irq_delay_us = 5;
    gps_mock::sys_hz = 139'000'000;
    pulse(input, 16, false);
    serial(input, sentence(16));
    poll(input);
    assert(received.size() == 7);
    gps_mock::sys_hz = 138'000'000;
    pulse(input, 17, false);
    serial(input, sentence(17));
    poll(input);
    assert(received.size() == 7);
    pulse(input, 18, false);
    serial(input, sentence(18));
    poll(input);
    assert(received.size() == 7);
    pulse(input, 19, false);
    serial(input, sentence(19));
    poll(input);
    assert(received.size() == 8);
    ticks_hw->ticks[TICK_TIMER0].cycles = 13; // SDK Hz labels are unchanged.
    pulse(input, 20, false);
    serial(input, sentence(20));
    poll(input);
    assert(received.size() == 8 && !input.capture_clock_bound());
    assert(!input.position(gps_mock::us * 1000));
    assert(input.status(gps_mock::us * 1000).find("\"time_valid\":false") != std::string::npos);
    ticks_hw->ticks[TICK_TIMER0].cycles = 12;
    for (unsigned i = 21; i <= 23; ++i) {
        pulse(input, i, false);
        serial(input, sentence(i));
        poll(input);
    }
    assert(received.size() == 9);
    input.close();
    assert(!(pwm_hw->en & (1u << 1)));
    s.capture_uncertainty_us = 1;
    assert(input.open({}, {}, s));
    pulse(input, 25, false);
    serial(input, sentence(25));
    poll(input);
    assert(received.size() == 9);
    assert(input.status(gps_mock::us * 1000).find("capture_uncertainty_exceeded") !=
           std::string::npos);
    input.close();
    // Real parser first-byte timestamps and CLK2 endpoints must survive an RMC
    // sentence finishing across the following PPS edge.
    s.capture_uncertainty_us = 100;
    s.pps_active_high = true;
    s.maximum_message_delay_ms = 999;
    received.clear();
    input.cycle_capture(+[]() -> time::gps::CycleSnapshot {
        return {gps_mock::us * 10, gps_mock::us * 1000, 1000, 1, 1, true};
    });
    assert(input.open({}, {}, s));
    pulse(input, 30);
    poll(input);
    for (unsigned i = 30; i <= 31; ++i) {
        gps_mock::edge(3, false, std::uint64_t(i) * 1'000'000 + 100'000);
        gps_mock::us += 5;
        input.pps_interrupt();
        gps_mock::us = std::uint64_t(i) * 1'000'000 + 950'000;
        bool next = false;
        for (const auto c : sentence(i)) {
            if (!next && gps_mock::us >= std::uint64_t(i + 1) * 1'000'000) {
                const auto delivery = gps_mock::us;
                gps_mock::edge(3, true, std::uint64_t(i + 1) * 1'000'000);
                gps_mock::us = delivery;
                input.pps_interrupt();
                next = true;
            }
            gps_mock::receive.push_back(std::uint8_t(c));
            input.uart_interrupt();
            gps_mock::us += 1100;
        }
        assert(next);
        poll(input);
    }
    assert(received.size() == 1);
    assert(std::abs(std::int64_t(received.back().capture_raw_ns) - 31'000'000'000LL) < 10'000);
    assert(input.cycle() && input.cycle()->raw_ns < 31'001'000'000ULL);
    const auto text = input.status(gps_mock::us * 1000);
    const auto view = wtp::json::parse(text);
    assert(view && std::stoull(view->get("candidate_pps_raw_ns")->string()) < 31'001'000'000ULL);
    input.close();
    // The label can arrive almost two seconds after its edge, with another
    // edge during parsing. Preserve that edge's independent count snapshot.
    s.minimum_message_delay_ms = 1000;
    s.maximum_message_delay_ms = 1999;
    received.clear();
    assert(input.open({}, {}, s));
    pulse(input, 50);
    poll(input);
    pulse(input, 51);
    poll(input);
    for (unsigned i = 50; i <= 51; ++i) {
        gps_mock::edge(3, false, std::uint64_t(i + 1) * 1'000'000 + 100'000);
        gps_mock::us += 5;
        input.pps_interrupt();
        gps_mock::us = std::uint64_t(i + 1) * 1'000'000 + 950'000;
        bool next = false;
        for (const auto c : sentence(i)) {
            if (!next && gps_mock::us >= std::uint64_t(i + 2) * 1'000'000) {
                const auto delivery = gps_mock::us;
                gps_mock::edge(3, true, std::uint64_t(i + 2) * 1'000'000);
                gps_mock::us = delivery;
                input.pps_interrupt();
                next = true;
            }
            gps_mock::receive.push_back(std::uint8_t(c));
            input.uart_interrupt();
            gps_mock::us += 1100;
        }
        assert(next);
        poll(input);
    }
    assert(received.size() == 1);
    assert(std::abs(std::int64_t(received.back().capture_raw_ns) - 51'000'000'000LL) < 10'000);
    assert(input.cycle() && input.cycle()->raw_ns < 51'001'000'000ULL);
    input.close();
}
