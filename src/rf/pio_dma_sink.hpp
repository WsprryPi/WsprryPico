#pragma once

#include "rf/stream_engine.hpp"

namespace wsprrypico::rf {

enum class DriverEventKind { Alarm, DmaComplete, DmaError };
struct DriverEvent {
    DriverEventKind kind;
    std::uint64_t epoch;
    std::uint64_t sequence = 0;
};

// Same-core IRQ/foreground boundary. No methods allocate on the execution path.
class PioDmaHardware {
  public:
    using Handler = void (*)(void*, DriverEvent);
    virtual ~PioDmaHardware() = default;
    virtual std::uint32_t lock() = 0;
    virtual void unlock(std::uint32_t saved) = 0;
    virtual bool open(Handler handler, void* context) = 0;
    virtual bool halt(std::uint64_t deadline_ns) = 0;
    virtual bool dma(const std::uint32_t* data, std::uint32_t words, bool increment,
                     std::uint64_t epoch, std::uint64_t sequence) = 0;
    virtual bool alarm(std::uint64_t start_ns, std::uint64_t epoch) = 0;
    // Waits only inside the short prelaunch window; deadline is exclusive.
    virtual bool launch(std::uint64_t start_ns, std::uint64_t deadline_ns) = 0;
    [[nodiscard]] virtual std::uint64_t launch_observed_ns() const = 0;
    [[nodiscard]] virtual std::uint64_t now_ns() const = 0;
    [[nodiscard]] virtual bool stalled() const = 0;
    [[nodiscard]] virtual bool active() const = 0;
};

class PioDmaSink final : public BlockSink {
  public:
    explicit PioDmaSink(PioDmaHardware& hardware) : hw_(hardware) {}
    PioDmaSink(const PioDmaSink&) = delete;
    PioDmaSink& operator=(const PioDmaSink&) = delete;
    [[nodiscard]] std::string_view diagnostic() const override {
        return failure_;
    }
    bool stop(std::uint64_t deadline_ns) override;
    bool submit(std::uint64_t epoch, std::uint64_t sequence, std::span<const std::uint32_t> words,
                std::uint64_t samples) override;
    [[nodiscard]] bool schedules_locally() const override {
        return true;
    }
    [[nodiscard]] std::uint64_t start_resolution_ns() const override {
        return 1000;
    }
    bool arm(std::uint64_t epoch, std::uint64_t start_ns, std::uint64_t total_samples,
             LaunchGuard guard = {}) override;
    SinkReport poll(std::uint64_t now_ns) override;
    [[nodiscard]] bool output_active() const override {
        return hw_.active();
    }

  private:
    struct Guard {
        PioDmaHardware& hw;
        std::uint32_t saved;
        explicit Guard(PioDmaHardware& h) : hw(h), saved(h.lock()) {}
        ~Guard() {
            hw.unlock(saved);
        }
    };
    struct Block {
        std::span<const std::uint32_t> words;
        std::uint64_t samples = 0;
        std::uint64_t sequence = 0;
    };
    static void dispatch(void* context, DriverEvent event);
    void event(DriverEvent event);
    bool queue_tail();
    void fault(const char* reason);
    PioDmaHardware& hw_;
    std::array<Block, 2> queue_{};
    std::size_t head_ = 0, queued_ = 0;
    bool opened_ = false, tail_ = false, tail_submitted_ = false;
    wtp::EngineState state_ = wtp::EngineState::Idle;
    LaunchGuard guard_{};
    std::uint64_t epoch_ = 0, submitted_ = 0, accepted_ = 0;
    std::uint64_t dma_blocks_ = 0, dma_samples_ = 0, total_ = 0, start_ = 0;
    std::uint32_t zero_ = 0;
    std::optional<std::uint64_t> launch_ns_ = {};
    const char* failure_ = "";
};

} // namespace wsprrypico::rf
