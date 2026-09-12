#pragma once

#include "rf/waveform.hpp"

namespace wsprrypico::rf {

struct LaunchGuard {
    bool (*check)(void*) = nullptr;
    void* context = nullptr;
    std::uint64_t deadline_ns = 0; // Exclusive; zero retains strict relative bench launch.
    [[nodiscard]] bool ready() const {
        return !check || check(context);
    }
};

struct SinkReport {
    wtp::EngineState state = wtp::EngineState::Idle;
    std::uint64_t epoch = 0;
    std::uint64_t completed_blocks = 0;
    std::uint64_t consumed_samples = 0;
    // IRQ-driven sinks sample time together with state after acquiring their lock.
    std::optional<std::uint64_t> observed_monotonic_ns = {};
    std::optional<bool> observed_output_active = {};
    std::optional<std::uint64_t> launch_monotonic_ns = {};
};

// stop() must release all submitted spans
// synchronously on success. The owner must successfully disable before destroying
// either engine or sink. Calls are serialized, not concurrent/ISR-safe. Progress is ordered,
// epoch-bound and monotonic.
class BlockSink {
  public:
    virtual ~BlockSink() = default;
    [[nodiscard]] virtual std::string_view diagnostic() const {
        return {};
    }
    virtual bool stop(std::uint64_t deadline_ns) = 0;
    virtual bool submit(std::uint64_t epoch, std::uint64_t sequence,
                        std::span<const std::uint32_t> words, std::uint64_t valid_samples) = 0;
    [[nodiscard]] virtual bool schedules_locally() const {
        return false;
    }
    [[nodiscard]] virtual std::uint64_t start_resolution_ns() const {
        return 1;
    }
    virtual bool arm(std::uint64_t epoch, std::uint64_t start_ns, std::uint64_t total_samples,
                     LaunchGuard guard = {}) = 0;
    virtual SinkReport poll(std::uint64_t now_ns) = 0;
    [[nodiscard]] virtual bool output_active() const = 0;
};

class StreamEngine final : public wtp::RfEngine {
  public:
    explicit StreamEngine(BlockSink& sink) : sink_(sink) {}
    StreamEngine(const StreamEngine&) = delete;
    StreamEngine& operator=(const StreamEngine&) = delete;
    std::string_view diagnostic() const override {
        return failure_;
    }
    bool set_frequency_correction_ppb(std::int32_t ppb) override;
    wtp::PrepareResult prepare(const wtp::Job& job) override;
    [[nodiscard]] bool schedules_locally() const override {
        return sink_.schedules_locally();
    }
    bool schedule(const wtp::Job& job, std::uint64_t start_ns,
                  const wtp::LocalStartConditions& conditions) override;
    [[nodiscard]] std::uint64_t start_resolution_ns() const override {
        return sink_.start_resolution_ns();
    }
    [[nodiscard]] std::uint64_t completion_acknowledgement_ns() const override {
        return schedules_locally() ? maximum_completion_acknowledgement_ns : 0;
    }
    bool begin(const wtp::Job& job, std::uint64_t start_monotonic_ns) override;
    wtp::EngineReport poll(std::uint64_t monotonic_now_ns) override;
    bool disable(std::uint64_t deadline_monotonic_ns) override;
    [[nodiscard]] bool output_active() const override {
        return sink_.output_active();
    }

  private:
    static bool check_clock(void* context);
    wtp::LocalStartConditions start_conditions_{};
    bool submit_next(std::size_t slot);
    wtp::EngineReport fail(std::uint64_t now_ns, const char* reason = "sink_rejected");
    std::int32_t correction_ppb_ = 0;
    const char* failure_ = "";
    BlockSink& sink_;
    Plan plan_{};
    Waveform waveform_;
    std::optional<wtp::Job> job_;
    alignas(4) std::array<std::array<std::uint32_t, block_words>, 2> buffers_{};
    std::array<std::uint64_t, 2> valid_{};
    wtp::EngineState state_ = wtp::EngineState::Idle;
    std::uint64_t epoch_ = 0;
    std::uint64_t submitted_ = 0;
    std::uint64_t completed_ = 0;
    std::uint64_t consumed_ = 0;
    std::uint64_t start_ns_ = 0;
    std::uint64_t end_ns_ = 0;
    std::uint64_t last_poll_ns_ = 0;
    std::uint64_t launch_deadline_ns_ = 0;
    std::optional<std::uint64_t> launch_ns_ = {};
};

static_assert(sizeof(StreamEngine) <= 180 * 1024);
static_assert(sizeof(Plan) <= 4096);

} // namespace wsprrypico::rf
