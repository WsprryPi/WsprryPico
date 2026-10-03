#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace wsprrypico::runtime {
enum class ActivityKind : std::uint8_t {
    None,
    Status,
    StandaloneErase,
    StandaloneProgram,
    ProfileErase,
    ProfileProgram,
    AccessErase,
    AccessProgram
};
enum class ActivityPhase : std::uint8_t { Begin, End };
enum class ActivityOutcome : std::uint8_t { Pending, Complete, Failed };
struct ActivityRecord {
    std::uint64_t sequence = 0, span = 0, monotonic_ns = 0;
    ActivityKind kind = ActivityKind::None;
    ActivityPhase phase = ActivityPhase::Begin;
    ActivityOutcome outcome = ActivityOutcome::Pending;
};

// Single core-0 caller only; never call from interrupts/core 1. No allocation,
// persistence, payloads, addresses or protocol identifiers. Captures are opt-in
// and retain the first 256 records until the next successful begin(). Each
// admitted span reserves its END: overflow drops a whole new span, not a mate.
class ActivityTrace {
  public:
    static constexpr std::size_t capacity = 256;
    bool begin() {
        if (open_spans_)
            return false;
        count_ = 0;
        ++capture_epoch_;
        sequence_ = 0;
        dropped_spans_ = 0;
        last_ns_ = 0;
        clock_regressed_ = false;
        enabled_ = true;
        return true;
    }
    void end() {
        enabled_ = false;
    }
    std::uint64_t capture_epoch() const {
        return capture_epoch_;
    }
    bool enabled() const {
        return enabled_;
    }
    bool overflow() const {
        return dropped_spans_ != 0;
    }
    bool clock_regressed() const {
        return clock_regressed_;
    }
    std::uint64_t dropped_spans() const {
        return dropped_spans_;
    }
    std::size_t open_spans() const {
        return open_spans_;
    }
    std::span<const ActivityRecord> records() const {
        return {records_.data(), count_};
    }
    std::uint64_t start(ActivityKind kind, std::uint64_t now_ns) {
        if (!enabled_ || kind == ActivityKind::None)
            return 0;
        if (count_ + open_spans_ + 2 > capacity) {
            ++dropped_spans_;
            return 0;
        }
        ++open_spans_;
        const auto id = sequence_ + 1;
        append({0, id, now_ns, kind, ActivityPhase::Begin, ActivityOutcome::Pending});
        return id;
    }
    // An admitted span may close after END disables new recording. The caller
    // is its non-copyable scope guard; duplicate/unknown completion is rejected.
    bool finish(std::uint64_t id, ActivityKind kind, std::uint64_t now_ns,
                ActivityOutcome outcome) {
        if (!id || outcome == ActivityOutcome::Pending)
            return false;
        bool found = false;
        for (std::size_t i = 0; i < count_; ++i) {
            const auto& record = records_[i];
            if (record.span != id)
                continue;
            if (record.kind != kind || record.phase == ActivityPhase::End)
                return false;
            found = true;
        }
        if (!found || !open_spans_)
            return false;
        --open_spans_;
        append({0, id, now_ns, kind, ActivityPhase::End, outcome});
        return true;
    }

  private:
    void append(ActivityRecord record) {
        if (count_ && record.monotonic_ns < last_ns_)
            clock_regressed_ = true;
        last_ns_ = record.monotonic_ns;
        record.sequence = ++sequence_;
        records_[count_++] = record;
    }
    std::array<ActivityRecord, capacity> records_{};
    std::size_t count_ = 0, open_spans_ = 0;
    std::uint64_t sequence_ = 0, dropped_spans_ = 0, last_ns_ = 0, capture_epoch_ = 0;
    bool enabled_ = false, clock_regressed_ = false;
};
inline ActivityTrace& activity_trace() {
    static ActivityTrace value;
    return value;
}

// Clock is invoked only while tracing is enabled or closing an admitted span.
// Overflow may sample the clock before rejecting a span; disabled capture never does.
// STATUS Complete means handler completion, including replay/protocol rejection;
// flash Complete means the adapter returned true, not durable journal activation.
template <typename Clock> class ActivitySpan {
  public:
    ActivitySpan(ActivityTrace& trace, ActivityKind kind, Clock clock, bool selected = true)
        : trace_(trace), kind_(kind), clock_(clock) {
        if (selected && trace_.enabled())
            id_ = trace_.start(kind_, clock_());
    }
    ~ActivitySpan() {
        if (id_)
            (void)trace_.finish(id_, kind_, clock_(), outcome_);
    }
    ActivitySpan(const ActivitySpan&) = delete;
    ActivitySpan& operator=(const ActivitySpan&) = delete;
    void outcome(bool complete) {
        outcome_ = complete ? ActivityOutcome::Complete : ActivityOutcome::Failed;
    }

  private:
    ActivityTrace& trace_;
    ActivityKind kind_;
    Clock clock_;
    std::uint64_t id_ = 0;
    ActivityOutcome outcome_ = ActivityOutcome::Complete;
};
inline std::string_view activity_kind_name(ActivityKind kind) {
    constexpr std::array names{
        "none",          "status",          "standalone_erase", "standalone_program",
        "profile_erase", "profile_program", "access_erase",     "access_program"};
    return names[static_cast<unsigned>(kind)];
}
} // namespace wsprrypico::runtime
