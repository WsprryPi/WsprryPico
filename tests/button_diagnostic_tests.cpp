#include "provisioning/button_diagnostic.hpp"

#include <cassert>
#include <initializer_list>

using wsprrypico::provisioning::ButtonDiagnostic;

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
} // namespace

int main() {
    thresholds_and_stuck_hold();
    release_boundaries();
    startup_low_bounce_and_clock_fault();
}
