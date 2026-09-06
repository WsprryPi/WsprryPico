#pragma once
#include "wtp/job_service.hpp"

namespace wsprrypico::standalone {
// No hardware access. Models a locally scheduled job in the inhibited image;
// it provides lifecycle diagnostics, never evidence of a physical launch.
class DryRunEngine final : public wtp::RfEngine {
  public:
    wtp::PrepareResult prepare(const wtp::Job&) override {
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wtp::Job& job, std::uint64_t start,
                  const wtp::LocalStartConditions& conditions) override;
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t now) override;
    bool disable(std::uint64_t) override {
        state_ = wtp::EngineState::Idle;
        return true;
    }
    bool output_active() const override {
        return false;
    }

  private:
    wtp::LocalStartConditions conditions_{};
    std::uint64_t start_ = 0, duration_ = 0;
    wtp::EngineState state_ = wtp::EngineState::Idle;
};
} // namespace wsprrypico::standalone
