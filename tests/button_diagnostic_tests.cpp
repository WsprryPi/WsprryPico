#include "provisioning/button_diagnostic.hpp"
#include "provisioning/button_runtime.hpp"
#include "provisioning/button_sample_stream.hpp"
#include "provisioning/pico/rp2350_dma_progress.hpp"

#include <cassert>
#include <initializer_list>

using wsprrypico::provisioning::ButtonDiagnostic;
using wsprrypico::provisioning::ButtonSampleStream;
using wsprrypico::provisioning::Rp2350DmaProgress;

namespace {
void edge(ButtonDiagnostic& button, std::uint64_t at_us, bool pressed) {
    assert(!button.observe(at_us, pressed).released);
    assert(!button.observe(at_us + ButtonDiagnostic::debounce_us, pressed).released);
}

void thresholds_and_stuck_hold() {
    ButtonDiagnostic button;
    assert(!button.observe(0, false).released);
    edge(button, 100'000, true);
    assert(!button.observe(999'999, true).request_stop);
    assert(button.observe(1'000'000, true).request_stop);
    assert(!button.observe(1'100'000, true).request_stop);
    assert(!button.observe(9'099'999, true).request_setup_ap);
    assert(button.observe(9'100'000, true).request_setup_ap);
    assert(!button.observe(30'100'000, true).request_setup_ap);
    const auto release = button.observe(30'101'000, false);
    assert(!release.released);
    const auto done = button.observe(30'111'000, false);
    assert(done.released && done.duration_us == 30'001'000);
    assert(!done.request_stop && !done.request_setup_ap && !done.request_reset);
    edge(button, 31'000'000, true);
    button.observe(31'200'000, false);
    const auto next = button.observe(31'210'000, false);
    assert(next.released && next.request_reset);
}

void release_boundaries() {
    for (const auto duration : {10'000ULL, 19'999ULL, 20'000ULL, 399'999ULL, 400'000ULL, 899'999ULL,
                                900'000ULL, 8'999'999ULL, 9'000'000ULL}) {
        ButtonDiagnostic button;
        button.observe(0, false);
        edge(button, 100'000, true);
        if (duration >= 900'000)
            assert(button.observe(100'000 + duration, true).request_stop);
        const auto first = button.observe(100'000 + duration, false);
        assert(!first.released);
        const auto done = button.observe(110'000 + duration, false);
        assert(done.released && done.duration_us == duration);
        assert(done.request_reset == (duration < 400'000));
        assert(done.request_stop == (duration >= 400'000 && duration < 900'000));
        assert(done.request_setup_ap == false);
    }
    ButtonDiagnostic button;
    button.observe(0, false);
    edge(button, 100'000, true);
    button.observe(999'999, true);
    button.observe(1'000'000, false);
    const auto done = button.observe(1'010'000, false);
    assert(done.released && done.duration_us == 900'000 && done.request_stop);
}

void startup_low_bounce_and_clock_fault() {
    ButtonDiagnostic button;
    button.observe(0, true);
    button.observe(10'000, true);
    button.observe(20'000, false);
    assert(!button.observe(30'000, false).released);
    button.observe(40'000, true);
    button.observe(49'999, false);
    assert(!button.observe(59'999, false).released);
    edge(button, 100'000, true);
    button.observe(200'000, false);
    const auto done = button.observe(210'000, false);
    assert(done.released && done.request_reset);
    assert(!button.observe(209'999, true).request_stop);
    assert(button.fault());
}

void packed_samples_survive_foreground_blackout() {
    ButtonSampleStream stream;
    unsigned reset = 0, stop = 0, ap = 0, release = 0;
    auto replay_word = [&](std::uint32_t word) {
        for (unsigned bit = 0; bit < 8; ++bit) {
            const auto event = stream.observe_word(word, bit);
            reset += event.request_reset;
            stop += event.request_stop;
            ap += event.request_setup_ap;
            release += event.released;
        }
    };
    // 200 ms of samples may be delivered in one batch after flash writing.
    // A complete 104 ms tap inside that interval must still request reset.
    for (unsigned i = 0; i < 16; ++i)
        replay_word(0xff);
    for (unsigned i = 0; i < 13; ++i)
        replay_word(0x00);
    for (unsigned i = 0; i < 16; ++i)
        replay_word(0xff);
    assert(reset == 1 && stop == 0 && ap == 0 && release == 1);
    // A later held jumper crosses both thresholds, remains down beyond 10 s,
    // then releases without a duplicate request.
    for (unsigned i = 0; i < 1'375; ++i)
        replay_word(0x00);
    for (unsigned i = 0; i < 2; ++i)
        replay_word(0xff);
    assert(reset == 1 && stop == 1 && ap == 1 && release == 2);
    assert(!stream.fault());
    assert(ButtonSampleStream::backlog_valid(2048, 0, 2048));
    assert(!ButtonSampleStream::backlog_valid(2049, 0, 2048));
    assert(!ButtonSampleStream::backlog_valid(1, 2, 2048));
}

void rp2350_dma_count_is_not_endless_mode() {
    constexpr auto initial = Rp2350DmaProgress::transfer_words;
    static_assert(initial == 0x0fffffffU);
    assert(Rp2350DmaProgress::produced(initial) == 0);
    assert(Rp2350DmaProgress::produced(initial - 1) == 1);
    assert(Rp2350DmaProgress::produced(0) == initial);
    // The old 0xffffffff configuration selects RP2350 endless mode: it
    // cannot provide a monotonically decreasing producer count.
    assert(!Rp2350DmaProgress::produced(0xffffffffU));
}

void runtime_actions_require_verified_stop() {
    unsigned stops = 0, setups = 0, releases = 0, resets = 0;
    bool stop_succeeds = false;
    auto runtime = wsprrypico::provisioning::ButtonRuntime{[&]() {
                                                               ++stops;
                                                               return stop_succeeds;
                                                           },
                                                           [&](std::uint64_t, bool) {
                                                               ++setups;
                                                               return true;
                                                           },
                                                           [&](std::uint64_t) { ++releases; },
                                                           [&]() { ++resets; }};
    runtime.observe({.request_stop = true}, 900, true);
    runtime.observe({.request_setup_ap = true}, 9'000, true);
    runtime.observe({.request_reset = true, .released = true, .duration_us = 285'000}, 9'300,
                    false);
    assert(stops == 1 && setups == 0 && resets == 0 && releases == 1);
    assert(runtime.last_duration_us() == 285'000);
    runtime.capture_fault();
    runtime.observe({.request_setup_ap = true}, 20'000, true);
    assert(stops == 2 && setups == 0 && resets == 0);

    stop_succeeds = true;
    auto accepted = wsprrypico::provisioning::ButtonRuntime{[&]() {
                                                                ++stops;
                                                                return stop_succeeds;
                                                            },
                                                            [&](std::uint64_t, bool held) {
                                                                assert(held && stops == 3);
                                                                ++setups;
                                                                return true;
                                                            },
                                                            [&](std::uint64_t) { ++releases; },
                                                            [&]() { ++resets; }};
    accepted.observe({.request_stop = true}, 900, true);
    accepted.observe({.request_setup_ap = true}, 9'000, true);
    accepted.observe({.released = true, .duration_us = 9'100'000}, 9'100, false);
    accepted.observe({.request_reset = true, .released = true, .duration_us = 285'000}, 10'000,
                     false);
    assert(accepted.stop_verified() && setups == 1 && resets == 1 && releases == 3);
    assert(accepted.stop_events() == 1 && accepted.setup_events() == 1 &&
           accepted.reset_events() == 1);
}
} // namespace

int main() {
    thresholds_and_stuck_hold();
    release_boundaries();
    startup_low_bounce_and_clock_fault();
    packed_samples_survive_foreground_blackout();
    rp2350_dma_count_is_not_endless_mode();
    runtime_actions_require_verified_stop();
}
