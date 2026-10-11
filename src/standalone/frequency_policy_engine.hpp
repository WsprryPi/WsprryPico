#pragma once

#include "standalone/storage.hpp"
#include "wtp/job_service.hpp"

namespace wsprrypico::standalone {
// One application admission boundary for USB/LAN/BLE/browser and autonomous
// jobs. WTP remains device-neutral; the underlying engine retains all physical
// limits, preparation, timing, ownership and safety behavior.
class FrequencyPolicyEngine final : public wtp::RfEngine {
  public:
    FrequencyPolicyEngine(wtp::RfEngine& engine, const Store& store,
                          std::uint64_t minimum_frequency_nhz, std::uint64_t maximum_frequency_nhz)
        : engine_(engine), store_(store), minimum_(minimum_frequency_nhz),
          maximum_(maximum_frequency_nhz) {}
    wtp::PrepareResult prepare(const wtp::Job& job) override;
    bool set_frequency_correction_ppb(std::int32_t value) override {
        return engine_.set_frequency_correction_ppb(value);
    }
    std::string_view diagnostic() const override {
        return engine_.diagnostic();
    }
    bool schedules_locally() const override {
        return engine_.schedules_locally();
    }
    bool owns_execution_plan() const override {
        return engine_.owns_execution_plan();
    }
    std::uint64_t start_resolution_ns() const override {
        return engine_.start_resolution_ns();
    }
    std::uint64_t completion_acknowledgement_ns() const override {
        return engine_.completion_acknowledgement_ns();
    }
    bool schedule(const wtp::Job& job, std::uint64_t start,
                  const wtp::LocalStartConditions& conditions) override {
        return engine_.schedule(job, start, conditions);
    }
    bool begin(const wtp::Job& job, std::uint64_t start) override {
        return engine_.begin(job, start);
    }
    wtp::EngineReport poll(std::uint64_t now) override {
        return engine_.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return engine_.disable(deadline);
    }
    bool output_active() const override {
        return engine_.output_active();
    }

  private:
    wtp::RfEngine& engine_;
    const Store& store_;
    const std::uint64_t minimum_, maximum_;
};
} // namespace wsprrypico::standalone
