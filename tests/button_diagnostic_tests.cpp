#include "provisioning/button_diagnostic.hpp"
#include "provisioning/button_runtime.hpp"
#include "provisioning/button_safety.hpp"
#include "provisioning/button_sample_stream.hpp"
#include "provisioning/pico/rp2350_dma_progress.hpp"

#include <cassert>
#include <initializer_list>

using wsprrypico::provisioning::ButtonDiagnostic;
using wsprrypico::provisioning::ButtonSafety;
using wsprrypico::provisioning::ButtonSampleStream;
using wsprrypico::provisioning::Rp2350DmaProgress;

namespace {
void independent_safety_policy() {
    ButtonSafety held;
    assert(!held.observe(0, false));
    assert(!held.observe(100'000, true));
    assert(!held.observe(110'000, true));
    assert(!held.observe(999'999, true));
    assert(held.observe(1'000'000, true));
    assert(held.requested_at_us() == 1'000'000 && held.duration_us() == 900'000);
    assert(!held.reset() && !held.fault());
    assert(held.observe(20'000'000, false));
    assert(held.observe(20'010'000, false));
    assert(held.requested_at_us() == 1'000'000); // Never rearm after release.

    for (const auto duration : {20'000ULL, 399'999ULL, 400'000ULL, 899'999ULL}) {
        ButtonSafety release;
        assert(!release.observe(0, false));
        assert(!release.observe(100'000, true));
        assert(!release.observe(110'000, true));
        assert(!release.observe(100'000 + duration, false));
        assert(release.observe(100'000 + duration + ButtonDiagnostic::release_debounce_us, false));
        assert(release.reset() == (duration < 400'000));
        assert(release.duration_us() == duration);
    }
    ButtonSafety boot;
    assert(!boot.observe(0, true));
    assert(!boot.observe(12'000'000, true));
    assert(!boot.observe(12'001'000, false));
    assert(!boot.observe(12'011'000, false));
    // Sub-debounce noise cannot trigger a worker stop.
    assert(!boot.observe(12'100'000, true));
    assert(!boot.observe(12'109'999, false));
    assert(!boot.observe(12'120'000, false));
    assert(boot.observe(12'119'999, false));
    assert(boot.fault() && boot.inhibited());
}
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
    const auto done = button.observe(30'201'000, false);
    assert(done.released && done.duration_us == 30'001'000);
    assert(!done.request_stop && !done.request_setup_ap && !done.request_reset);
    edge(button, 31'000'000, true);
    button.observe(31'200'000, false);
    const auto next = button.observe(31'300'000, false);
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
        const auto done =
            button.observe(100'000 + duration + ButtonDiagnostic::release_debounce_us, false);
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
    const auto done = button.observe(1'100'000, false);
    assert(done.released && done.duration_us == 900'000 && done.request_stop);
}

void startup_low_bounce_and_clock_fault() {
    ButtonDiagnostic button;
    button.observe(0, true);
    button.observe(10'000, true);
    button.observe(20'000, false);
    assert(!button.observe(120'000, false).released);
    button.observe(140'000, true);
    button.observe(149'999, false);
    assert(!button.observe(249'999, false).released);
    edge(button, 300'000, true);
    button.observe(400'000, false);
    const auto done = button.observe(500'000, false);
    assert(done.released && done.request_reset);
    assert(!button.observe(499'999, true).request_stop);
    assert(button.fault());
}

void interrupted_hold_remains_one_gesture() {
    // A 42 ms initial contact followed by a 50 ms open gap must not turn a
    // five-second hold into a reset. Exercise both worker sampling and the
    // packed PIO/DMA replay, including a later 99 ms interruption.
    ButtonDiagnostic button;
    ButtonSafety safety;
    ButtonSampleStream stream;
    unsigned resets = 0, stops = 0, releases = 0;
    unsigned packed_resets = 0, packed_stops = 0, packed_releases = 0;
    std::uint64_t duration = 0, packed_duration = 0;
    std::uint32_t word = 0;
    for (std::uint64_t at = 0; at < 5'304'000; at += 1'000) {
        const bool pressed = at >= 100'000 && at < 5'100'000 && !(at >= 142'000 && at < 192'000) &&
                             !(at >= 3'000'000 && at < 3'099'000);
        const auto event = button.observe(at, pressed);
        resets += event.request_reset;
        stops += event.request_stop;
        releases += event.released;
        if (event.released)
            duration = event.duration_us;
        (void)safety.observe(at, pressed);
        if (at < 1'000'000)
            assert(!safety.inhibited());
        word = (word << 1) | !pressed;
        if ((at / 1'000) % 8 == 7) {
            for (unsigned bit = 0; bit < 8; ++bit) {
                const auto packed = stream.observe_word(word, bit);
                packed_resets += packed.request_reset;
                packed_stops += packed.request_stop;
                packed_releases += packed.released;
                if (packed.released)
                    packed_duration = packed.duration_us;
            }
            word = 0;
        }
    }
    assert(resets == 0 && stops == 1 && releases == 1 && duration == 5'000'000);
    assert(packed_resets == 0 && packed_stops == 1 && packed_releases == 1 &&
           packed_duration == duration);
    assert(safety.inhibited() && !safety.reset() && !safety.fault());
    assert(safety.requested_at_us() == 1'000'000 && safety.duration_us() == 900'000);
    assert(!button.fault() && !stream.fault());
}

void release_confirmation_and_long_hold() {
    // A confirmed release still resets a genuine quick tap. Its duration is
    // measured at the first high sample, excluding the confirmation delay.
    ButtonDiagnostic quick;
    quick.observe(0, false);
    edge(quick, 100'000, true);
    assert(!quick.observe(142'000, false).released);
    assert(!quick.observe(241'999, false).released);
    const auto reset = quick.observe(242'000, false);
    assert(reset.released && reset.request_reset && reset.duration_us == 42'000);

    ButtonDiagnostic held;
    unsigned resets = 0, stops = 0, setups = 0, releases = 0;
    std::uint64_t duration = 0;
    for (std::uint64_t at = 0; at <= 10'300'000; at += 1'000) {
        const bool pressed = at >= 100'000 && at < 10'100'000 && !(at >= 142'000 && at < 192'000) &&
                             !(at >= 8'910'000 && at < 9'009'000);
        const auto event = held.observe(at, pressed);
        resets += event.request_reset;
        stops += event.request_stop;
        setups += event.request_setup_ap;
        releases += event.released;
        if (event.released)
            duration = event.duration_us;
    }
    assert(resets == 0 && stops == 1 && setups == 1 && releases == 1 && duration == 10'000'000);
    assert(!held.fault());

    // A short high interval at boot must not arm a jumper that is still held.
    ButtonDiagnostic boot;
    boot.observe(0, true);
    boot.observe(100'000, false);
    assert(!boot.observe(199'999, false).released);
    boot.observe(200'000, true);
    assert(!boot.observe(20'000'000, true).request_setup_ap);
    assert(!boot.active());
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
    for (unsigned i = 0; i < 14; ++i)
        replay_word(0xff);
    assert(reset == 1 && stop == 1 && ap == 1 && release == 2);
    assert(!stream.fault());
    assert(ButtonSampleStream::backlog_valid(2048, 0, 2048));
    assert(!ButtonSampleStream::backlog_valid(2049, 0, 2048));
    assert(!ButtonSampleStream::backlog_valid(1, 2, 2048));
}

void rp2350_dma_count_is_not_endless_mode() {
    constexpr auto block = Rp2350DmaProgress::transfer_words;
    constexpr auto mode = Rp2350DmaProgress::self_trigger;
    Rp2350DmaProgress progress;
    assert(progress.observe(mode | block, 0) == 0);
    // More than 400 days of 1 kHz sampling, including the old 28-bit finite
    // limit and the 32-bit software word counter limit, in seconds of host time.
    std::uint64_t words = 0;
    for (; words < 4'400'000'000ULL; words += 1000) {
        auto remaining = block - static_cast<std::uint32_t>(words % block);
        assert(progress.observe(mode | remaining, words * 8000) == words);
    }
    assert(progress.blocks() > 1'000'000);
    Rp2350DmaProgress boundary;
    for (unsigned word = 0; word <= block; ++word)
        assert(boundary.observe(mode | (block - word), word * 8000ULL) == word);
    assert(boundary.observe(mode | block, block * 8000ULL) == block);
    assert(boundary.observe(mode | (block - 1), (block + 1) * 8000ULL) == block + 1);
    for (auto invalid : {0xffffffffU, block, mode | (block + 1)}) {
        Rp2350DmaProgress broken;
        assert(!broken.observe(invalid, 0));
        assert(!broken.observe(mode | block, 0)); // sticky fault
    }
    Rp2350DmaProgress gap;
    assert(!gap.observe(mode | block, Rp2350DmaProgress::maximum_gap_us + 1));
    Rp2350DmaProgress backwards(100);
    assert(!backwards.observe(mode | block, 99));
    Rp2350DmaProgress reset;
    assert(reset.observe(mode | (block - 1), 8000) == 1);
    assert(!reset.observe(mode | block, 8001));
    assert(ButtonSampleStream::backlog_valid(0x100000001ULL, 0xffffffffULL, 2048));
    assert(!ButtonSampleStream::backlog_valid(0x100001000ULL, 0xffffffffULL, 2048));
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
    assert(runtime.setup_events() == 1 && runtime.setup_attempts() == 0 &&
           runtime.setup_accepts() == 0);
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
           accepted.setup_attempts() == 1 && accepted.setup_accepts() == 1 &&
           accepted.reset_events() == 1);

    auto rejected = wsprrypico::provisioning::ButtonRuntime{[]() { return true; },
                                                            [&](std::uint64_t, bool) {
                                                                ++setups;
                                                                return false;
                                                            },
                                                            [](std::uint64_t) {}, []() {}};
    rejected.observe({.request_stop = true}, 900, true);
    rejected.observe({.request_setup_ap = true}, 9'000, true);
    assert(rejected.stop_verified() && rejected.setup_events() == 1 &&
           rejected.setup_attempts() == 1 && rejected.setup_accepts() == 0 && setups == 2);
}
} // namespace

int main() {
    independent_safety_policy();
    thresholds_and_stuck_hold();
    release_boundaries();
    startup_low_bounce_and_clock_fault();
    interrupted_hold_remains_one_gesture();
    release_confirmation_and_long_hold();
    packed_samples_survive_foreground_blackout();
    rp2350_dma_count_is_not_endless_mode();
    runtime_actions_require_verified_stop();
}
