#include "runtime/activity_trace.hpp"

#include <cassert>
#include <cstdint>

using namespace wsprrypico::runtime;

int main() {
    ActivityTrace trace;
    unsigned calls = 0;
    std::uint64_t now = 100;
    const auto clock = [&] {
        ++calls;
        return ++now;
    };
    {
        ActivitySpan disabled(trace, ActivityKind::Status, clock);
    }
    assert(!trace.enabled() && trace.records().empty() && calls == 0);
    assert(trace.begin() && trace.capture_epoch() == 1);
    {
        ActivitySpan ignored(trace, ActivityKind::Status, clock, false);
        assert(calls == 0);
        ActivitySpan status(trace, ActivityKind::Status, clock);
        {
            ActivitySpan flash(trace, ActivityKind::StandaloneProgram, clock);
            flash.outcome(false);
            assert(trace.open_spans() == 2);
        }
        assert(trace.open_spans() == 1);
    }
    const auto first = trace.records();
    assert(first.size() == 4 && calls == 4 && trace.open_spans() == 0);
    assert(first[0].span == 1 && first[1].span == 2 && first[2].span == 2 && first[3].span == 1);
    assert(first[2].outcome == ActivityOutcome::Failed &&
           first[3].outcome == ActivityOutcome::Complete);
    for (std::size_t i = 0; i < first.size(); ++i) {
        assert(first[i].sequence == i + 1);
        if (i)
            assert(first[i].monotonic_ns >= first[i - 1].monotonic_ns);
    }
    assert(!trace.finish(1, ActivityKind::Status, now, ActivityOutcome::Complete));
    assert(!trace.finish(99, ActivityKind::Status, now, ActivityOutcome::Complete));
    assert(trace.records().size() == 4);
    trace.end();
    assert(!trace.enabled() && trace.records().size() == 4);
    assert(trace.begin() && trace.capture_epoch() == 2);
    const auto id = trace.start(ActivityKind::Status, 200);
    assert(id == 1 && trace.open_spans() == 1);
    assert(!trace.begin()); // Never destroy a pending pair, including while disabled.
    trace.end();
    assert(!trace.begin() && trace.start(ActivityKind::Status, 201) == 0);
    assert(!trace.finish(id, ActivityKind::ProfileErase, 202, ActivityOutcome::Complete));
    assert(trace.finish(id, ActivityKind::Status, 203, ActivityOutcome::Complete));
    assert(trace.records().size() == 2 && trace.open_spans() == 0 && !trace.enabled());
    assert(trace.begin());
    // Fill every usable pair. Entire overflowing spans are rejected, preserving
    // the earliest data and every admitted END rather than silently wrapping.
    for (std::size_t i = 0; i < ActivityTrace::capacity / 2; ++i) {
        const auto span = trace.start(ActivityKind::AccessErase, i * 2);
        assert(span);
        assert(trace.finish(span, ActivityKind::AccessErase, i * 2 + 1, ActivityOutcome::Complete));
    }
    assert(trace.records().size() == ActivityTrace::capacity);
    assert(trace.start(ActivityKind::Status, 1000) == 0);
    assert(trace.overflow() && trace.dropped_spans() == 1 && trace.open_spans() == 0);
    assert(trace.records().front().sequence == 1 && trace.records().back().sequence == 256);
    trace.end();
    assert(trace.begin() && !trace.overflow() && !trace.clock_regressed());
    // Reservation also works when many beginnings precede all their endings.
    std::uint64_t ids[128]{};
    for (std::size_t i = 0; i < 128; ++i)
        ids[i] = trace.start(ActivityKind::Status, i);
    assert(trace.start(ActivityKind::ProfileProgram, 129) == 0);
    for (std::size_t i = 0; i < 128; ++i)
        assert(
            trace.finish(ids[127 - i], ActivityKind::Status, 130 + i, ActivityOutcome::Complete));
    assert(trace.records().size() == 256 && trace.open_spans() == 0 && trace.overflow());
    assert(trace.begin());
    const auto regressed = trace.start(ActivityKind::Status, 100);
    assert(trace.finish(regressed, ActivityKind::Status, 99, ActivityOutcome::Complete));
    assert(trace.clock_regressed() && trace.records().back().monotonic_ns == 99);
    trace.end();
    calls = 0;
    {
        ActivitySpan disabled_again(trace, ActivityKind::Status, clock);
    }
    assert(calls == 0 && trace.records().size() == 2);
}
