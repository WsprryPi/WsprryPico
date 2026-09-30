#include "rf/worker.hpp"

#include <algorithm>
#include <cstdlib>

namespace wsprrypico::rf {
WorkerEngine::WorkerEngine(wtp::RfEngine& engine, time::UtcDiscipline& clock, Now now, Wait wait,
                           Failure failure, Mask mask, Restore restore)
    : engine_(engine), clock_(clock), staged_clock_(clock), worker_clock_(clock), now_(now),
      wait_(wait), failure_(failure), mask_(mask), restore_(restore),
      completion_acknowledgement_ns_(engine.completion_acknowledgement_ns()),
      owns_execution_plan_(engine.owns_execution_plan()) {}
void WorkerEngine::call(Op op) const {
    // No reentrancy, no queue overwrite, no retry after ambiguous completion.
    if (phase_.load(std::memory_order_acquire) != 0) {
        failure_();
        std::abort();
    }
    staged_clock_ = clock_;
    op_ = op;
    const auto start = now_();
    phase_.store(1, std::memory_order_release);
    while (phase_.load(std::memory_order_acquire) != 2) {
        if (now_() - start >= 100'000'000ULL) {
            failure_();
            std::abort();
        }
        wait_();
    }
    max_roundtrip_ = std::max(max_roundtrip_, now_() - start);
    phase_.store(0, std::memory_order_release);
}
void WorkerEngine::check_safety() {
    if (safety_probe_ && safety_probe_(safety_context_))
        safety_inhibited_.store(true, std::memory_order_release);
    if (!safety_inhibited() || safety_stopped_)
        return;
    const auto requested = now_();
    if (!engine_.disable(requested + 100'000'000ULL) || engine_.output_active()) {
        failure_();
        std::abort();
    }
    safety_stopped_ = true;
    worker_metrics_.safety_requested_ns = requested;
    worker_metrics_.safety_stopped_ns = now_();
}
void WorkerEngine::step() {
    check_safety();
    const auto now = now_();
    const bool executing =
        worker_state_ == wtp::EngineState::Armed || worker_state_ == wtp::EngineState::Running;
    if (executing && last_step_)
        worker_metrics_.max_service_gap_ns =
            std::max(worker_metrics_.max_service_gap_ns, now - last_step_);
    last_step_ = now;
    // Local state stays local even while the producer is serializing a response.
    const auto observed = engine_.poll(now);
    worker_state_ = observed.state;
    if (executing)
        worker_metrics_.max_poll_ns = std::max(worker_metrics_.max_poll_ns, now_() - now);
    if (phase_.load(std::memory_order_acquire) != 1)
        return;
    // Launch IRQ reads only worker_clock_. Never mask across allocation or RPC.
    const auto saved = mask_();
    worker_clock_ = staged_clock_;
    restore_(saved);
    switch (op_) {
    case Op::Inspect:
    case Op::Metrics:
        break;
    case Op::Prepare:
        prepared_ = safety_inhibited() ? wtp::PrepareResult{} : engine_.prepare(*job_);
        break;
    case Op::Schedule:
        conditions_.clock = &worker_clock_;
        result_ = !safety_inhibited() && engine_.schedule(*job_, instant_, conditions_);
        break;
    case Op::Disable:
        result_ = engine_.disable(instant_);
        break;
    case Op::Correct:
        result_ = !safety_inhibited() && engine_.set_frequency_correction_ppb(correction_);
        break;
    }
    check_safety();
    if (safety_inhibited()) {
        if (op_ == Op::Prepare)
            prepared_ = {};
        if (op_ == Op::Schedule || op_ == Op::Correct)
            result_ = false;
    }
    report_ = (op_ == Op::Inspect || op_ == Op::Metrics) && !safety_inhibited()
                  ? observed
                  : engine_.poll(now_());
    diagnostic_ = safety_inhibited() ? "gp14_safety_inhibit" : engine_.diagnostic();
    ++worker_metrics_.commands;
    // Stack scans and driver snapshots are diagnostic work, not ordinary RPC work.
    // Execute only on an explicit metrics request, retaining single-core ownership.
    if (op_ == Op::Metrics && probe_) {
        const auto before = now_();
        probe_(worker_metrics_, probe_context_);
        worker_metrics_.max_probe_ns = std::max(worker_metrics_.max_probe_ns, now_() - before);
        ++worker_metrics_.probes;
    }
    if (op_ == Op::Metrics)
        reply_metrics_ = worker_metrics_;
    phase_.store(2, std::memory_order_release);
}
wtp::PrepareResult WorkerEngine::prepare(const wtp::Job& job) {
    job_ = &job;
    call(Op::Prepare);
    job_ = nullptr;
    return std::move(prepared_);
}
bool WorkerEngine::set_frequency_correction_ppb(std::int32_t ppb) {
    correction_ = ppb;
    call(Op::Correct);
    return result_;
}
bool WorkerEngine::schedule(const wtp::Job& job, std::uint64_t when,
                            const wtp::LocalStartConditions& conditions) {
    if (conditions.clock != &clock_)
        return false;
    job_ = &job;
    instant_ = when;
    conditions_ = conditions;
    call(Op::Schedule);
    job_ = nullptr;
    return result_;
}
wtp::EngineReport WorkerEngine::poll(std::uint64_t) {
    call(Op::Inspect);
    return report_;
}
bool WorkerEngine::disable(std::uint64_t deadline) {
    instant_ = deadline;
    call(Op::Disable);
    return result_;
}
bool WorkerEngine::output_active() const {
    call(Op::Inspect);
    return report_.output_active;
}
WorkerEngine::Metrics WorkerEngine::metrics() {
    call(Op::Metrics);
    auto result = reply_metrics_;
    result.max_roundtrip_ns = max_roundtrip_;
    return result;
}
} // namespace wsprrypico::rf
