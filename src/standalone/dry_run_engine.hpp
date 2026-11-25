#pragma once
#include "rf/job_service.hpp"

namespace wsprrypico::standalone {
// No hardware access. Models a locally scheduled job in the inhibited image;
// it provides lifecycle diagnostics, never evidence of a physical launch.
class DryRunEngine final : public execution::RfEngine {
  public:
    execution::PrepareResult prepare(const execution::Job&) override {
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const execution::Job& job, std::uint64_t start,
                  const execution::LocalStartConditions& conditions) override;
    bool begin(const execution::Job&, std::uint64_t) override {
        return false;
    }
    execution::EngineReport poll(std::uint64_t now) override;
    bool disable(std::uint64_t) override {
        state_ = execution::EngineState::Idle;
        return true;
    }
    bool output_active() const override {
        return false;
    }

  private:
    execution::LocalStartConditions conditions_{};
    std::uint64_t start_ = 0, duration_ = 0;
    execution::EngineState state_ = execution::EngineState::Idle;
};
} // namespace wsprrypico::standalone
