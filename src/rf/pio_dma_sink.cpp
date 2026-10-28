#include "rf/pio_dma_sink.hpp"

#include <algorithm>

namespace wsprrypico::rf {

bool PioDmaSink::halt_output(std::uint64_t deadline_ns) {
    hw_.force_inactive();
    if (observation_.rf_start_ns && !observation_.rf_off_ns && hw_.rf_inactive_verified())
        observation_.rf_off_ns = hw_.now_ns();
    const bool amplifier_inactive = !amplifier_ || amplifier_->deactivate();
    if (observation_.enable_ns && !observation_.disable_ns && amplifier_inactive)
        observation_.disable_ns = hw_.now_ns();
    const bool stopped = hw_.halt(deadline_ns);
    const bool inactive = !hw_.active();
    if (indicator_ && inactive)
        indicator_->inactive();
    return stopped && inactive && amplifier_inactive;
}

bool PioDmaSink::stop(std::uint64_t deadline_ns) {
    Guard lock(hw_);
    // Also clean no-open and partially-open paths. Never short-circuit enable
    // cleanup behind a failed open/halt or an unconfirmed RF state.
    if (!halt_output(deadline_ns) || output_active()) {
        state_ = wtp::EngineState::Failed;
        return false;
    }
    if (indicator_)
        indicator_->inactive();
    state_ = wtp::EngineState::Idle;
    queue_ = {};
    head_ = queued_ = 0;
    tail_ = tail_submitted_ = false;
    guard_ = {};
    launch_ns_.reset();
    enable_ns_.reset();
    tail_deadline_ns_.reset();
    submitted_ = accepted_ = dma_blocks_ = dma_samples_ = total_ = 0;
    return !output_active();
}

bool PioDmaSink::submit(std::uint64_t epoch, std::uint64_t sequence,
                        std::span<const std::uint32_t> words, std::uint64_t samples) {
    Guard lock(hw_);
    if (state_ == wtp::EngineState::Idle)
        failure_ = "";
    if (state_ != wtp::EngineState::Idle && state_ != wtp::EngineState::Armed &&
        state_ != wtp::EngineState::Running) {
        if (!*failure_)
            failure_ = "state_changed";
        return false;
    }
    if (epoch == 0 || sequence != submitted_ || (submitted_ && epoch != epoch_) || queued_ == 2 ||
        samples == 0 || samples > block_samples || words.size() != (samples + 31) / 32 ||
        (reinterpret_cast<std::uintptr_t>(words.data()) & 3U) != 0 ||
        accepted_ > max_duration_ns / 1000 * (sample_rate / 1000000) - samples ||
        (total_ && samples > total_ - accepted_) ||
        (submitted_ && accepted_ % block_samples != 0) ||
        (samples % 32 && (words.back() >> (samples % 32)) != 0)) {
        failure_ = "submit_contract";
        return false;
    }
    if (!opened_) {
        if (!hw_.open(dispatch, this)) {
            failure_ = "open_rejected";
            return false;
        }
        opened_ = true;
    }
    epoch_ = epoch;
    queue_[(head_ + queued_) % 2] = {words, samples, sequence};
    ++queued_;
    ++submitted_;
    accepted_ += samples;
    if (state_ != wtp::EngineState::Idle) {
        if (!hw_.dma(words.data(), static_cast<std::uint32_t>(words.size()), true, epoch,
                     sequence)) {
            failure_ = "dma_rejected";
            return false;
        }
        if (!queue_tail()) {
            failure_ = "tail_rejected";
            return false;
        }
    }
    return true;
}

bool PioDmaSink::queue_tail() {
    if (!tail_submitted_ && accepted_ == total_ && queued_ < 2) {
        if (!hw_.dma(&zero_, 10, false, epoch_, submitted_))
            return false;
        tail_submitted_ = true;
    }
    return true;
}

bool PioDmaSink::arm(std::uint64_t epoch, std::uint64_t start_ns, std::uint64_t total_samples,
                     LaunchGuard guard) {
    Guard lock(hw_);
    if (state_ != wtp::EngineState::Idle || !opened_ || epoch != epoch_ || queued_ == 0 ||
        total_samples == 0 || total_samples > max_duration_ns / 1000 * (sample_rate / 1000000) ||
        accepted_ > total_samples ||
        (accepted_ < total_samples && accepted_ % block_samples != 0) || start_ns % 1000 != 0 ||
        start_ns <= hw_.now_ns() || hw_.inhibited() ||
        (amplifier_ && !amplifier_->timing().valid()) ||
        (amplifier_lead_ns() && (start_ns < amplifier_lead_ns() + 1'000'000 ||
                                 hw_.now_ns() >= start_ns - amplifier_lead_ns() - 1'000'000))) {
        return false;
    }
    start_ = start_ns;
    observation_ = {};
    observation_.epoch = epoch;
    observation_.configured = amplifier_ && amplifier_->enabled();
    if (amplifier_) {
        observation_.lead_ms = amplifier_->timing().lead_ms;
        observation_.tail_ms = amplifier_->timing().tail_ms;
    }
    total_ = total_samples;
    guard_ = guard;
    state_ = wtp::EngineState::Armed;
    for (std::size_t i = 0; i < queued_; ++i) {
        const auto& block = queue_[(head_ + i) % 2];
        if (!hw_.dma(block.words.data(), static_cast<std::uint32_t>(block.words.size()), true,
                     epoch_, block.sequence)) {
            fault("arm_dma_rejected");
            return false;
        }
    }
    const bool alarm_ok = amplifier_lead_ns()
                              ? hw_.retry_alarm(start_ - amplifier_lead_ns() - 1'000'000, epoch_)
                              : hw_.alarm(start_, epoch_);
    if (!queue_tail() || !alarm_ok) {
        fault("arm_tail_or_alarm_rejected");
        return false;
    }
    return true;
}

void PioDmaSink::fault(const char* reason) {
    if (!*failure_)
        failure_ = reason;
    state_ = wtp::EngineState::Failed;
    (void)halt_output(hw_.now_ns());
}

void PioDmaSink::dispatch(void* context, DriverEvent event) {
    static_cast<PioDmaSink*>(context)->event(event);
}

void PioDmaSink::event(DriverEvent event) {
    Guard lock(hw_);
    if (event.epoch != epoch_ ||
        (state_ != wtp::EngineState::Armed && state_ != wtp::EngineState::Running)) {
        return;
    }
    if (event.kind == DriverEventKind::Alarm) {
        if (tail_deadline_ns_) {
            finish_tail();
            return;
        }
        if (state_ != wtp::EngineState::Armed) {
            return;
        }
        const auto deadline = guard_.deadline_ns ? guard_.deadline_ns : start_ + 1;
        const auto target = guard_.target(start_);
        if (!target.admissible || target.monotonic_ns >= deadline || hw_.inhibited()) {
            failure_ = "launch_clock_guard_rejected";
            state_ =
                halt_output(hw_.now_ns()) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
            return;
        }
        start_ = target.monotonic_ns;
        const auto lead = amplifier_lead_ns();
        if (lead) {
            auto now = hw_.now_ns();
            if (!enable_ns_) {
                if (start_ < lead || now > start_ - lead) {
                    failure_ = "insufficient_amplifier_lead";
                    state_ = halt_output(now) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
                    return;
                }
                const auto activation = start_ - lead;
                if (activation > now && activation - now > 1'000'000) {
                    if (!hw_.retry_alarm(activation - 1'000'000, epoch_))
                        fault("lead_alarm_rejected");
                    return;
                }
                hw_.force_inactive();
                if (hw_.active() || hw_.inhibited() || !amplifier_->activate()) {
                    fault("amplifier_activation_failed");
                    return;
                }
                // Settling starts after completion of the checked enable write.
                now = hw_.now_ns();
                enable_ns_ = now;
                observation_.enable_ns = now;
                if (hw_.inhibited() || now > start_ - lead) {
                    fault("amplifier_activation_late");
                    return;
                }
                if (!hw_.alarm(start_, epoch_))
                    fault("rf_alarm_rejected");
                return;
            }
            if (start_ < *enable_ns_ || start_ - *enable_ns_ < lead) {
                failure_ = "shortened_amplifier_lead";
                state_ = halt_output(now) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
                return;
            }
        }
        if (indicator_ && indicator_->enabled()) {
            const auto now = hw_.now_ns();
            // ARM and early alarm entry retain the non-TX cue. Only a valid
            // attempt at/after the local start requests the checked on write.
            if (now < start_ || !indicator_->request_launch()) {
                constexpr std::uint64_t retry_ns = 100'000;
                // The timer can advance while entering/programming the SDK alarm.
                // Retain a full retry margin even when the guarded start is only
                // a few microseconds ahead; the original UTC deadline still bounds it.
                const auto wake = std::max(start_, now + retry_ns);
                if (wake < now || wake >= deadline || !hw_.retry_alarm(wake, epoch_)) {
                    failure_ = "launch_retry_alarm_rejected";
                    state_ = halt_output(now) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
                }
                return;
            }
        }
        const auto launch = hw_.launch(start_, deadline,
                                       {amplifier_, enable_ns_.has_value(),
                                        [](void* context) {
                                            auto& self = *static_cast<PioDmaSink*>(context);
                                            self.observation_.enable_ns = self.hw_.now_ns();
                                        },
                                        this});
        if (launch == LaunchResult::Rejected) {
            failure_ = "launch_driver_rejected";
            state_ =
                halt_output(hw_.now_ns()) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
        } else if (launch == LaunchResult::Launched) {
            const auto observed = hw_.launch_observed_ns();
            if (observed < start_ || observed >= deadline) {
                fault("invalid_launch_boundary");
                return;
            }
            launch_ns_ = observed;
            observation_.rf_start_ns = observed;
            start_ = *launch_ns_;
            state_ = wtp::EngineState::Running;
        }
        return;
    }
    if (event.sequence < dma_blocks_) {
        return;
    }
    if (event.sequence != dma_blocks_ || event.kind == DriverEventKind::DmaError) {
        fault(event.kind == DriverEventKind::DmaError ? "dma_error" : "dma_sequence");
        return;
    }
    if (tail_) {
        // Ten zero words have entered an eight-word FIFO: every data word,
        // including the OSR word, has drained and a zero word has been emitted. No
        // frequency-bearing tail remains.
        if (state_ != wtp::EngineState::Running || dma_samples_ != total_) {
            fault("tail_completion");
            return;
        }
        complete_rf();
        return;
    }
    if (queued_ == 0 || (state_ == wtp::EngineState::Running && hw_.stalled())) {
        fault(queued_ == 0 ? "empty_dma_queue" : "pio_txstall");
        return;
    }
    dma_samples_ += queue_[head_].samples;
    ++dma_blocks_;
    queue_[head_] = {};
    head_ = (head_ + 1) % 2;
    --queued_;
    if (dma_samples_ == total_) {
        tail_ = true;
        if (!tail_submitted_)
            fault("missing_zero_tail");
    } else if (queued_ == 0 || !queue_tail()) {
        fault(queued_ == 0 ? "refill_starved" : "zero_tail_rejected");
        // Never chain into an unprepared or previously consumed buffer.
    }
}

void PioDmaSink::complete_rf() {
    if (tail_deadline_ns_)
        return;
    hw_.force_inactive();
    if (!hw_.rf_inactive_verified() || hw_.inhibited()) {
        fault("rf_completion_unconfirmed");
        return;
    }
    if (indicator_)
        indicator_->inactive();
    const auto now = hw_.now_ns(), dwell = amplifier_tail_ns();
    observation_.rf_off_ns = now;
    observation_.normal_rf_completion = true;
    if (!dwell) {
        if (halt_output(now))
            state_ = wtp::EngineState::Complete;
        else
            fault("tail_cleanup_failed");
        return;
    }
    if (now > UINT64_MAX - dwell) {
        fault("tail_deadline_overflow");
        return;
    }
    tail_deadline_ns_ = now + dwell;
    if (!hw_.retry_alarm(*tail_deadline_ns_, epoch_))
        fault("tail_alarm_rejected");
}

void PioDmaSink::finish_tail() {
    const auto now = hw_.now_ns();
    if (!tail_deadline_ns_ || state_ != wtp::EngineState::Running)
        return;
    if (hw_.inhibited() || hw_.active()) {
        fault("tail_inhibited_or_rf_active");
        return;
    }
    if (now < *tail_deadline_ns_) {
        if (!hw_.retry_alarm(*tail_deadline_ns_, epoch_))
            fault("tail_retry_rejected");
        return;
    }
    if (halt_output(now))
        state_ = wtp::EngineState::Complete;
    else
        fault("tail_cleanup_failed");
}

SinkReport PioDmaSink::poll(std::uint64_t) {
    Guard lock(hw_);
    const auto now_ns = hw_.now_ns();
    if (state_ == wtp::EngineState::Running && !tail_ && hw_.stalled()) {
        fault("pio_txstall");
    }
    // The zero-tail descriptor chains directly to the hardware stop channel.
    // Once the final data IRQ established tail_ and hardware is inactive, all
    // ten zero words have crossed the eight-word FIFO and the stop write has
    // executed. That is authoritative completion even if tail DMA IRQ entry is
    // delayed; requiring the software IRQ first creates a false DEVICE_FAULT
    // window after output is already safely low.
    if (state_ == wtp::EngineState::Running && tail_ && !hw_.active()) {
        complete_rf();
        if (tail_deadline_ns_ && (now_ns >= *tail_deadline_ns_ || hw_.inhibited()))
            finish_tail();
    }
    // A failed stop may later become verifiably inactive. Pending activation
    // is the exception: Armed retains its request while waiting for the LED.
    if (indicator_ && state_ != wtp::EngineState::Armed && !hw_.active())
        indicator_->inactive();
    if (state_ == wtp::EngineState::Complete) {
        return {state_, epoch_,          submitted_, total_,
                now_ns, output_active(), launch_ns_, wtp::ChainPhase::Inactive};
    }
    if (tail_deadline_ns_ && state_ == wtp::EngineState::Running) {
        return {state_, epoch_,          submitted_, total_,
                now_ns, output_active(), launch_ns_, wtp::ChainPhase::Tail};
    }
    if (state_ != wtp::EngineState::Running) {
        return {state_,
                epoch_,
                0,
                0,
                now_ns,
                output_active(),
                launch_ns_,
                state_ == wtp::EngineState::Armed
                    ? (enable_ns_ ? wtp::ChainPhase::Lead : wtp::ChainPhase::Waiting)
                : state_ == wtp::EngineState::Failed ? wtp::ChainPhase::Fault
                                                     : wtp::ChainPhase::Inactive};
    }
    const auto elapsed = now_ns > start_ ? std::min(now_ns - start_, max_duration_ns) : 0;
    // Conservative nominal-clock progress; DMA completion is FIFO delivery, not RF timing.
    const auto samples =
        std::min({elapsed * (sample_rate / 1000000) / 1000, dma_samples_, total_ - 1});
    return {state_,
            epoch_,
            std::min(dma_blocks_, samples / block_samples),
            samples,
            now_ns,
            output_active(),
            launch_ns_,
            wtp::ChainPhase::Rf};
}

} // namespace wsprrypico::rf
