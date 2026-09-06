#pragma once

#include "rf/stream_engine.hpp"

namespace wsprrypico::rf {

// Diagnostic interface only. RUN uses a local relative epoch, never claimed UTC/WTP.
class BenchClock {
  public:
    virtual ~BenchClock() = default;
    virtual std::uint64_t now_ns() const = 0;
};

class Bench {
  public:
    Bench(wtp::RfEngine& engine, const BenchClock& clock) : engine_(engine), clock_(clock) {}
    std::string command(std::string_view line);
    void poll();
    [[nodiscard]] bool busy() const {
        return running_ || benchmarking_;
    }
    [[nodiscard]] std::string status() const;

  private:
    wtp::RfEngine& engine_;
    const BenchClock& clock_;
    bool running_ = false, benchmarking_ = false;
    std::string state_ = "idle";
    std::uint64_t start_ns_ = 0, ended_ns_ = 0, last_poll_ns_ = 0, max_poll_gap_ns_ = 0;
    std::uint64_t max_render_ns_ = 0, benchmark_ns_ = 0, checksum_ = 0;
    unsigned remaining_ = 0, rendered_ = 0;
    std::optional<Plan> plan_;
    Waveform waveform_;
    std::array<std::uint32_t, block_words> buffer_{};
};

} // namespace wsprrypico::rf
