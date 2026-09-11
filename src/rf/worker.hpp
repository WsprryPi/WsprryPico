#pragma once
#include "rf/refill_metrics.hpp"
#include "time/utc_discipline.hpp"

#include <atomic>

namespace wsprrypico::rf {
// Single producer/single consumer rendezvous. There is no abandoned command:
// caller-owned payloads remain immutable and alive until a matching completion.
// Failure to acknowledge invokes the platform's non-returning recovery hook.
class WorkerEngine final : public wtp::RfEngine {
  public:
    using Now = std::uint64_t (*)();
    using Wait = void (*)();
    using Failure = void (*)();
    using Mask = std::uint32_t (*)();
    using Restore = void (*)(std::uint32_t);
    WorkerEngine(wtp::RfEngine& engine, time::UtcDiscipline& clock, Now now, Wait wait,
                 Failure failure, Mask mask, Restore restore);
    // Worker owner only; call continuously, including with no commands.
    void step();
    wtp::PrepareResult prepare(const wtp::Job&) override;
    bool set_frequency_correction_ppb(std::int32_t) override;
    bool schedules_locally() const override {
        return true;
    }
    std::uint64_t start_resolution_ns() const override {
        return 1000;
    }
    std::uint64_t completion_acknowledgement_ns() const override {
        return completion_acknowledgement_ns_;
    }
    bool schedule(const wtp::Job&, std::uint64_t, const wtp::LocalStartConditions&) override;
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t) override;
    bool disable(std::uint64_t) override;
    bool output_active() const override;
    std::string_view diagnostic() const override {
        return diagnostic_;
    }
    struct Metrics {
        // Start-to-start gap already includes preceding poll and command/probe work.
        std::uint64_t commands = 0, max_service_gap_ns = 0, max_poll_ns = 0;
        std::uint64_t max_roundtrip_ns = 0;
        std::uint64_t probes = 0, max_probe_ns = 0;
        std::uint64_t dma_irqs = 0, max_irq_ns = 0, launch_ns = 0;
        std::uint64_t launch_epoch = 0, launch_target_ns = 0;
        std::uint64_t alarm_irqs = 0, max_alarm_irq_ns = 0, tail_irqs = 0, dma_errors = 0;
        RefillMetrics::Snapshot refill;
        std::size_t stack_used_bytes = 0;
        std::uint32_t stack_guard_bottom = 0, stack_guard_limit = 0;
        std::uint32_t stack_fault_status = 0;
        bool stack_guard_valid = false;
    };
    Metrics metrics();
    void set_probe(void (*probe)(Metrics&, void*), void* context) {
        probe_ = probe;
        probe_context_ = context;
    }

  private:
    enum class Op { Inspect, Metrics, Prepare, Schedule, Disable, Correct };
    void call(Op) const;
    wtp::RfEngine& engine_;
    time::UtcDiscipline& clock_;
    mutable time::UtcDiscipline staged_clock_;
    time::UtcDiscipline worker_clock_;
    Now now_;
    Wait wait_;
    Failure failure_;
    Mask mask_;
    Restore restore_;
    const std::uint64_t completion_acknowledgement_ns_;
    // 0: producer owns payload, 1: consumer owns it, 2: completed.
    mutable std::atomic<unsigned> phase_{0};
    mutable Op op_ = Op::Inspect;
    const wtp::Job* job_ = nullptr;
    std::uint64_t instant_ = 0;
    std::int32_t correction_ = 0;
    wtp::LocalStartConditions conditions_{};
    wtp::PrepareResult prepared_;
    wtp::EngineReport report_{};
    bool result_ = false;
    mutable std::string_view diagnostic_;
    void (*probe_)(Metrics&, void*) = nullptr;
    void* probe_context_ = nullptr;
    wtp::EngineState worker_state_ = wtp::EngineState::Idle;
    std::uint64_t last_step_ = 0;
    Metrics worker_metrics_{}, reply_metrics_{};
    mutable std::uint64_t max_roundtrip_ = 0;
};
static_assert(std::atomic<unsigned>::is_always_lock_free);
} // namespace wsprrypico::rf
