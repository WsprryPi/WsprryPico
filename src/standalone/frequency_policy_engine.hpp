#pragma once

#include "standalone/ntp_retention.hpp"
#include "standalone/storage.hpp"
#include "time/ntp_filter.hpp"
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
    // Sole correction authority; external setters cannot bypass persisted selection.
    bool set_frequency_correction_ppb(std::int32_t) override {
        return false;
    }
    void calibration_boundary() override {
        frozen_.reset();
        pair_frozen_ = false;
    }
    void freeze_pair_calibration(bool freeze) override {
        pair_frozen_ = freeze;
    }
    void ntp_candidate(time::RateEstimate candidate, const wtp::Clock& clock,
                       bool topology_supported) {
        candidate_ = candidate;
        clock_ = &clock;
        topology_supported_ = topology_supported;
    }
    void retention(const NtpRetention& value) {
        retention_ = &value;
    }
    std::string calibration_status(std::uint64_t now) const override;
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
        // Preparation may precede a latched storage fault. Keep cleanup paths
        // below available even when a new launch is no longer admitted.
        return store_.healthy() && engine_.schedule(job, start, conditions);
    }
    bool begin(const wtp::Job& job, std::uint64_t start) override {
        return store_.healthy() && engine_.begin(job, start);
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
    struct Selection {
        std::int32_t ppb = 0;
        std::uint64_t generation = 0;
        bool ntp = false;
        bool saved = false;
    };
    Selection selection(std::uint64_t now) const;
    const char* fallback_reason(std::uint64_t now) const;
    std::optional<Selection> frozen_;
    bool pair_frozen_ = false;
    std::optional<std::int32_t> programmed_;
    time::RateEstimate candidate_;
    const NtpRetention* retention_ = nullptr;
    const wtp::Clock* clock_ = nullptr;
    bool topology_supported_ = false;
    // Physical applicability is unverified for this source/image. There is no
    // API toggle that can promote software fitting into independent RF evidence.
    static constexpr bool independent_rf_verified_ = false;
    wtp::RfEngine& engine_;
    const Store& store_;
    const std::uint64_t minimum_, maximum_;
};
} // namespace wsprrypico::standalone
