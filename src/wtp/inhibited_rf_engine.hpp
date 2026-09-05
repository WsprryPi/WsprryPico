#pragma once

#include "wtp/job_service.hpp"

#include <cstdint>
#include <optional>

namespace wsprrypico::wtp {

class InhibitedRfEngine final : public RfEngine {
  public:
    PrepareResult prepare(const Job& job) override;
    bool begin(const Job& job, std::uint64_t start_monotonic_ns) override;
    [[nodiscard]] EngineReport poll(std::uint64_t monotonic_now_ns) override;
    bool disable(std::uint64_t deadline_monotonic_ns) override;
    [[nodiscard]] bool output_active() const override;

  private:
    std::optional<Job> job_;
    std::uint64_t start_monotonic_ns_ = 0;
    bool running_ = false;
};

} // namespace wsprrypico::wtp
