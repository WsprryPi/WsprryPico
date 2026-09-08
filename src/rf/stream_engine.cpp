#include "rf/stream_engine.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::rf {

bool StreamEngine::schedule(const wtp::Job& job, std::uint64_t start_ns,
                            const wtp::LocalStartConditions& conditions) {
    if (!schedules_locally() || !conditions.clock || state_ != wtp::EngineState::Idle) {
        return false;
    }
    start_conditions_ = conditions;
    return begin(job, start_ns);
}

bool StreamEngine::check_clock(void* context) {
    const auto& self = *static_cast<StreamEngine*>(context);
    const auto& conditions = self.start_conditions_;
    const auto now = conditions.clock->snapshot();
    if (!self.job_ || now.monotonic_now_ns > self.start_ns_ ||
        now.uncertainty_ns > conditions.maximum_uncertainty_ns ||
        !(now.state == wtp::ClockState::Synchronized ||
          (now.state == wtp::ClockState::Holdover && conditions.maximum_holdover_age_ns > 0 &&
           now.sync_age_ns <= conditions.maximum_holdover_age_ns))) {
        return false;
    }
    const auto lead = self.start_ns_ - now.monotonic_now_ns;
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    if (now.utc_now_ns > limit - lead ||
        conditions.start_utc_ns > limit - self.job_->total_duration_ns) {
        return false;
    }
    const auto predicted = now.utc_now_ns + lead;
    const auto error = predicted > conditions.start_utc_ns ? predicted - conditions.start_utc_ns
                                                           : conditions.start_utc_ns - predicted;
    const auto pending =
        now.leap == wtp::LeapState::InsertPending || now.leap == wtp::LeapState::DeletePending;
    if (error > now.uncertainty_ns || now.leap == wtp::LeapState::Unknown ||
        pending != now.leap_transition_utc_ns.has_value()) {
        return false;
    }
    if (now.leap_transition_utc_ns) {
        const auto leap = *now.leap_transition_utc_ns;
        const auto low = leap > 1'000'000'000 ? leap - 1'000'000'000 : 0;
        const auto high = leap > limit - 1'000'000'000 ? limit : leap + 1'000'000'000;
        return conditions.start_utc_ns > high ||
               conditions.start_utc_ns + self.job_->total_duration_ns < low;
    }
    return true;
}

bool StreamEngine::set_frequency_correction_ppb(std::int32_t ppb) {
    if (state_ != wtp::EngineState::Idle || job_ || output_active() || ppb < -max_correction_ppb ||
        ppb > max_correction_ppb)
        return false;
    correction_ppb_ = ppb;
    return true;
}

wtp::PrepareResult StreamEngine::prepare(const wtp::Job& job) {
    if (state_ != wtp::EngineState::Idle || output_active()) {
        return {};
    }
    const auto candidate = plan_job(job, correction_ppb_);
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
    failure_ = "";
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
        const auto reason = sink_.diagnostic();
        failure_ = reason.empty() ? "sink_rejected" : reason.data();
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
    if (!submit_next(0) || !submit_next(1) ||
        !sink_.arm(epoch_, start_ns_, plan_.total_samples,
                   start_conditions_.clock ? LaunchGuard{check_clock, this} : LaunchGuard{})) {
        (void)fail(start_ns_, failure_);
        return false;
    }
    state_ = wtp::EngineState::Armed;
    return true;
}

wtp::EngineReport StreamEngine::fail(std::uint64_t now_ns, const char* reason) {
    failure_ = reason;
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
    if (report.observed_monotonic_ns) {
        if (*report.observed_monotonic_ns < now_ns) {
            return fail(now_ns, "invalid_progress");
        }
        now_ns = *report.observed_monotonic_ns;
    }
    // Do not compare a locked pre-launch snapshot against post-unlock IRQ state.
    const bool active =
        report.observed_output_active ? *report.observed_output_active : output_active();
    if (now_ns < last_poll_ns_ || report.epoch != epoch_ || report.completed_blocks < completed_ ||
        report.completed_blocks > submitted_ || report.consumed_samples < consumed_ ||
        report.consumed_samples > plan_.total_samples ||
        report.consumed_samples <
            std::min(report.completed_blocks * block_samples, plan_.total_samples) ||
        report.consumed_samples >
            std::min((report.completed_blocks + 1) * block_samples, plan_.total_samples)) {
        return fail(now_ns, "progress_counters");
    }
    const auto expected_completed =
        report.consumed_samples / block_samples + (report.consumed_samples == plan_.total_samples &&
                                                   plan_.total_samples % block_samples != 0);
    const auto elapsed =
        now_ns > start_ns_ ? std::min(now_ns - start_ns_, job_->total_duration_ns) : 0;
    // A terminal RF-off tail can include one low padding sample. After the
    // declared job end, permit that planned tail without relaxing RF-on timing.
    const auto expected_samples = elapsed == job_->total_duration_ns
                                      ? plan_.total_samples
                                      : (elapsed * (sample_rate / 1000000) + 500) / 1000;
    if (report.completed_blocks != expected_completed ||
        report.consumed_samples > expected_samples) {
        return fail(now_ns, "progress_time");
    }
    last_poll_ns_ = now_ns;
    if (report.state == wtp::EngineState::Missed) {
        if (report.consumed_samples != 0 || active) {
            return fail(now_ns);
        }
        state_ = wtp::EngineState::Missed;
        return {state_, false};
    }
    if (report.state == wtp::EngineState::Complete) {
        if (now_ns < end_ns_ || report.consumed_samples != plan_.total_samples ||
            report.completed_blocks != submitted_ || waveform_.position() != plan_.total_samples ||
            active) {
            return fail(now_ns, "invalid_completion");
        }
        state_ = wtp::EngineState::Complete;
        return {state_, false};
    }
    // Final data and zero-tail IRQ acknowledgements can both lag the hardware.
    // Allow only the final submitted block to be unacknowledged, for at most
    // 100 us after the nominal end. This does not generate extra RF samples.
    const bool awaiting_tail =
        report.state == wtp::EngineState::Running && waveform_.position() == plan_.total_samples &&
        submitted_ == (plan_.total_samples + block_samples - 1) / block_samples &&
        report.consumed_samples >= (submitted_ - 1) * block_samples && now_ns >= end_ns_ &&
        now_ns - end_ns_ <= 100'000;
    if ((now_ns < start_ns_ &&
         (report.state != wtp::EngineState::Armed || report.consumed_samples != 0 || active)) ||
        (now_ns >= start_ns_ && report.state != wtp::EngineState::Running) ||
        (now_ns >= end_ns_ && !awaiting_tail) || report.completed_blocks == submitted_) {
        return fail(now_ns, now_ns >= end_ns_ ? "completion_deadline" : "sink_state");
    }
    for (auto sequence = completed_; sequence < report.completed_blocks; ++sequence) {
        const auto slot = static_cast<std::size_t>(sequence % 2);
        valid_[slot] = waveform_.render(buffers_[slot]);
        if (!submit_next(slot)) {
            return fail(now_ns, failure_);
        }
    }
    completed_ = report.completed_blocks;
    consumed_ = report.consumed_samples;
    state_ = report.state;
    return {state_, active};
}

bool StreamEngine::disable(std::uint64_t deadline_monotonic_ns) {
    if (!sink_.stop(deadline_monotonic_ns) || output_active()) {
        state_ = wtp::EngineState::Failed;
        return false;
    }
    state_ = wtp::EngineState::Idle;
    job_.reset();
    start_conditions_ = {};
    valid_ = {};
    return true;
}

} // namespace wsprrypico::rf
