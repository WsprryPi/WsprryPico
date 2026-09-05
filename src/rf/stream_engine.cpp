#include "rf/stream_engine.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::rf {

wtp::PrepareResult StreamEngine::prepare(const wtp::Job& job) {
    if (state_ != wtp::EngineState::Idle || output_active()) {
        return {};
    }
    const auto candidate = plan_job(job);
    if (!candidate) {
        return {};
    }
    wtp::PrepareResult result{true, {}};
    for (std::size_t i = 0; i < candidate->count; ++i) {
        if (candidate->segments[i].increment != 0) {
            const auto realized = realized_nhz(candidate->segments[i].increment);
            if (realized != *job.events[i].frequency_nhz) {
                result.adjustments.push_back({i, *job.events[i].frequency_nhz, realized});
            }
        }
    }
    job_ = job;
    plan_ = *candidate;
    waveform_.reset(plan_);
    valid_[0] = waveform_.render(buffers_[0]);
    valid_[1] = waveform_.render(buffers_[1]);
    return result;
}

bool StreamEngine::submit_next(std::size_t slot) {
    if (valid_[slot] == 0) {
        return true;
    }
    const auto words = static_cast<std::size_t>((valid_[slot] + 31) / 32);
    if (!sink_.submit(epoch_, submitted_, std::span(buffers_[slot]).first(words), valid_[slot])) {
        return false;
    }
    ++submitted_;
    return true;
}

bool StreamEngine::begin(const wtp::Job& job, std::uint64_t start_monotonic_ns) {
    if (state_ != wtp::EngineState::Idle || !job_ || *job_ != job ||
        epoch_ == std::numeric_limits<std::uint64_t>::max() ||
        start_monotonic_ns > std::numeric_limits<std::uint64_t>::max() - job.total_duration_ns) {
        return false;
    }
    if (!sink_.stop(start_monotonic_ns) || output_active()) {
        state_ = wtp::EngineState::Failed;
        return false;
    }
    ++epoch_;
    submitted_ = completed_ = consumed_ = 0;
    start_ns_ = start_monotonic_ns;
    end_ns_ = start_ns_ + job.total_duration_ns;
    last_poll_ns_ = 0;
    if (!submit_next(0) || !submit_next(1) || !sink_.arm(epoch_, start_ns_, plan_.total_samples)) {
        (void)fail(start_ns_);
        return false;
    }
    state_ = wtp::EngineState::Armed;
    return true;
}

wtp::EngineReport StreamEngine::fail(std::uint64_t now_ns) {
    state_ = wtp::EngineState::Failed;
    // Even when stop fails, never recycle buffers or restart without successful disable.
    (void)sink_.stop(now_ns);
    return {state_, output_active()};
}

wtp::EngineReport StreamEngine::poll(std::uint64_t now_ns) {
    if (state_ != wtp::EngineState::Armed && state_ != wtp::EngineState::Running) {
        return {state_, output_active()};
    }
    const auto report = sink_.poll(now_ns);
    if (now_ns < last_poll_ns_ || report.epoch != epoch_ || report.completed_blocks < completed_ ||
        report.completed_blocks > submitted_ || report.consumed_samples < consumed_ ||
        report.consumed_samples > plan_.total_samples ||
        report.consumed_samples <
            std::min(report.completed_blocks * block_samples, plan_.total_samples) ||
        report.consumed_samples >
            std::min((report.completed_blocks + 1) * block_samples, plan_.total_samples)) {
        return fail(now_ns);
    }
    const auto expected_completed =
        report.consumed_samples / block_samples + (report.consumed_samples == plan_.total_samples &&
                                                   plan_.total_samples % block_samples != 0);
    const auto elapsed =
        now_ns > start_ns_ ? std::min(now_ns - start_ns_, job_->total_duration_ns) : 0;
    if (report.completed_blocks != expected_completed ||
        report.consumed_samples > (elapsed * 3 + 10) / 20) {
        return fail(now_ns);
    }
    last_poll_ns_ = now_ns;
    if (report.state == wtp::EngineState::Complete) {
        if (now_ns < end_ns_ || report.consumed_samples != plan_.total_samples ||
            report.completed_blocks != submitted_ || waveform_.position() != plan_.total_samples ||
            output_active()) {
            return fail(now_ns);
        }
        state_ = wtp::EngineState::Complete;
        return {state_, false};
    }
    if ((now_ns < start_ns_ && (report.state != wtp::EngineState::Armed ||
                                report.consumed_samples != 0 || output_active())) ||
        (now_ns >= start_ns_ && report.state != wtp::EngineState::Running) || now_ns >= end_ns_ ||
        report.completed_blocks == submitted_) {
        return fail(now_ns);
    }
    for (auto sequence = completed_; sequence < report.completed_blocks; ++sequence) {
        const auto slot = static_cast<std::size_t>(sequence % 2);
        valid_[slot] = waveform_.render(buffers_[slot]);
        if (!submit_next(slot)) {
            return fail(now_ns);
        }
    }
    completed_ = report.completed_blocks;
    consumed_ = report.consumed_samples;
    state_ = report.state;
    return {state_, output_active()};
}

bool StreamEngine::disable(std::uint64_t deadline_monotonic_ns) {
    if (!sink_.stop(deadline_monotonic_ns) || output_active()) {
        state_ = wtp::EngineState::Failed;
        return false;
    }
    state_ = wtp::EngineState::Idle;
    job_.reset();
    valid_ = {};
    return true;
}

} // namespace wsprrypico::rf
