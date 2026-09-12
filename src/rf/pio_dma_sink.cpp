#include "rf/pio_dma_sink.hpp"

#include <algorithm>

namespace wsprrypico::rf {

bool PioDmaSink::stop(std::uint64_t deadline_ns) {
    Guard lock(hw_);
    if ((opened_ && !hw_.halt(deadline_ns)) || hw_.active()) {
        state_ = wtp::EngineState::Failed;
        return false;
    }
    state_ = wtp::EngineState::Idle;
    queue_ = {};
    head_ = queued_ = 0;
    tail_ = tail_submitted_ = false;
    guard_ = {};
    launch_ns_.reset();
    submitted_ = accepted_ = dma_blocks_ = dma_samples_ = total_ = 0;
    return !hw_.active();
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
        start_ns <= hw_.now_ns()) {
        return false;
    }
    start_ = start_ns;
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
    if (!queue_tail() || !hw_.alarm(start_, epoch_)) {
        fault("arm_tail_or_alarm_rejected");
        return false;
    }
    return true;
}

void PioDmaSink::fault(const char* reason) {
    if (!*failure_)
        failure_ = reason;
    state_ = wtp::EngineState::Failed;
    (void)hw_.halt(hw_.now_ns());
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
        if (state_ != wtp::EngineState::Armed) {
            return;
        }
        const auto deadline = guard_.deadline_ns ? guard_.deadline_ns : start_ + 1;
        if (!guard_.ready() || !hw_.launch(start_, deadline)) {
            state_ = hw_.halt(hw_.now_ns()) ? wtp::EngineState::Missed : wtp::EngineState::Failed;
        } else {
            launch_ns_ = hw_.launch_observed_ns();
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
        if (state_ != wtp::EngineState::Running || dma_samples_ != total_ ||
            !hw_.halt(hw_.now_ns())) {
            fault("tail_completion");
            return;
        }
        state_ = wtp::EngineState::Complete;
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

SinkReport PioDmaSink::poll(std::uint64_t) {
    Guard lock(hw_);
    const auto now_ns = hw_.now_ns();
    if (state_ == wtp::EngineState::Running && !tail_ && hw_.stalled()) {
        fault("pio_txstall");
    }
    if (state_ == wtp::EngineState::Complete) {
        return {state_, epoch_, submitted_, total_, now_ns, hw_.active(), launch_ns_};
    }
    if (state_ != wtp::EngineState::Running) {
        return {state_, epoch_, 0, 0, now_ns, hw_.active(), launch_ns_};
    }
    const auto elapsed = now_ns > start_ ? std::min(now_ns - start_, max_duration_ns) : 0;
    // Conservative nominal-clock progress; DMA completion is FIFO delivery, not RF timing.
    const auto samples =
        std::min({elapsed * (sample_rate / 1000000) / 1000, dma_samples_, total_ - 1});
    return {state_,    epoch_, std::min(dma_blocks_, samples / block_samples),
            samples,   now_ns, hw_.active(),
            launch_ns_};
}

} // namespace wsprrypico::rf
