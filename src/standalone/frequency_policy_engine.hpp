#pragma once

#include "rf/filter_selector.hpp"
#include "standalone/storage.hpp"
#include "time/ntp_filter.hpp"
#include "rf/job_service.hpp"
#include "time/gps_calibration.hpp"

namespace wsprrypico::standalone {
// One application admission boundary for USB/LAN/BLE/browser and autonomous
// jobs. The job representation is device-neutral, and the underlying engine retains all physical
// limits, preparation, timing, ownership and safety behavior.
class FrequencyPolicyEngine final : public execution::RfEngine {
  public:
    FrequencyPolicyEngine(execution::RfEngine& engine, const Store& store,
                          std::uint64_t minimum_frequency_nhz, std::uint64_t maximum_frequency_nhz,
                          bool boot_ordinary_si5351 = false)
        : engine_(engine), store_(store), minimum_(minimum_frequency_nhz),
          maximum_(maximum_frequency_nhz), boot_filters_(store.filters()),
          boot_engine_(store.config() ? store.config()->pins.engine
                                      : hardware::PinPlan::Engine::Direct),
          boot_si5351_(store.config() ? store.config()->si5351 : std::nullopt),
          boot_ordinary_si5351_(boot_ordinary_si5351) {}
    execution::PadObservation pad_observation() const override {
        return engine_.pad_observation();
    }
    execution::SynthesisObservation synthesis_observation() const override {
        return engine_.synthesis_observation();
    }
    std::size_t preparation_memory_bytes(const execution::Job& job) const override {
        return engine_.preparation_memory_bytes(job);
    }
    execution::PrepareResult prepare(const execution::Job& job) override;
    execution::PrepareResult prepare_native_test_tone(const execution::Job& job) override;
    void inhibit_output() override {
        engine_.inhibit_output();
    }
    bool background_work_allowed() const override {
        return engine_.background_work_allowed();
    }
    // Sole correction authority; external setters cannot bypass persisted selection.
    bool set_frequency_correction_ppb(std::int32_t) override {
        return false;
    }
    void calibration_boundary() override {
        frozen_.reset();
        prepared_job_id_.clear();
        pair_frozen_ = false;
    }
    void freeze_pair_calibration(bool freeze) override {
        pair_frozen_ = freeze;
    }
    std::string calibration_status(std::uint64_t now) const override;
    struct CorrectionSnapshot {
        std::int32_t ppb;
        bool automatic;
        std::uint64_t generation, observed_raw_ns;
        std::uint32_t uncertainty_ppb;
    };
    struct ToneAssessment {
        std::string_view refusal;
        std::optional<CorrectionSnapshot> correction;
        std::optional<std::uint32_t> increment;
        std::optional<std::uint64_t> programmed_nhz;
    };
    // Numerical/policy assessment only: no engine methods, calibration freeze,
    // filter preparation, GPIO access, or journal writes.
    ToneAssessment assess_direct_tone(std::uint64_t frequency_nhz) const;
    struct SynthesisToneAssessment {
        std::string_view refusal;
        std::optional<CorrectionSnapshot> correction;
        std::optional<std::uint64_t> programmed_nhz;
        std::uint64_t numerical_bound_nhz = 0;
    };
    // Pure numerical and frequency policy assessment for native Si5351 Test Tone.
    SynthesisToneAssessment assess_si5351_tone(std::uint64_t frequency_nhz,
                                               unsigned proposed_drive_ma) const;
    std::optional<CorrectionSnapshot> prepared_correction() const {
        if (!frozen_) return {};
        return CorrectionSnapshot{frozen_->ppb, frozen_->automatic, frozen_->generation,
            frozen_->observed_raw_ns, frozen_->uncertainty_ppb};
    }
    void gps_calibration(std::optional<time::gps::Calibration> value, std::uint64_t now,
                         bool clock_bound, bool disagreement) {
        gps_calibration_ = value; gps_now_ = now;
        gps_clock_bound_ = clock_bound; gps_disagreement_ = disagreement;
    }
    std::string_view diagnostic() const override {
        return failure_ ? failure_ : engine_.diagnostic();
    }
    bool schedules_locally() const override {
        return engine_.schedules_locally();
    }
    std::uint64_t filter_preparation_ns() const override {
        return engine_.filter_preparation_ns();
    }
    std::uint64_t amplifier_lead_ns() const override {
        return engine_.amplifier_lead_ns();
    }
    std::uint64_t amplifier_tail_ns() const override {
        return engine_.amplifier_tail_ns();
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
    bool externally_controlled_completion() const override {
        return engine_.externally_controlled_completion();
    }
    bool schedule(const execution::Job& job, std::uint64_t start,
                  const execution::LocalStartConditions& conditions) override {
        // Preparation may precede a latched storage fault. Keep cleanup paths
        // below available even when a new launch is no longer admitted.
        return store_.healthy() && engine_.schedule(job, start, conditions);
    }
    bool begin(const execution::Job& job, std::uint64_t start) override {
        return store_.healthy() && engine_.begin(job, start);
    }
    execution::EngineReport poll(std::uint64_t now) override {
        return engine_.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return engine_.disable(deadline);
    }
    bool execution_started() const override {
        return engine_.execution_started();
    }
    bool output_active() const override {
        return engine_.output_active();
    }

  private:
    struct Selection {
        std::int32_t ppb = 0;
        std::uint64_t generation = 0;
        bool valid = true, automatic = false;
        std::uint64_t observed_raw_ns = 0;
        std::uint32_t uncertainty_ppb = 0;
        std::int32_t manual_ppb = 0;
        std::uint64_t selected_raw_ns = 0;
        std::optional<time::gps::Calibration> input;
    };
    Selection selection() const;
    bool qualified_test_tone_carrier(std::uint64_t requested_nhz) const;
    const char* frequency_refusal(std::uint64_t frequency_nhz,
                                  bool qualified_test_tone = false) const;
    execution::PrepareResult prepare_job(const execution::Job& job, bool qualified_test_tone);
    std::optional<Selection> frozen_;
    std::string prepared_job_id_;
    bool pair_frozen_ = false;
    std::optional<std::int32_t> programmed_;
    execution::RfEngine& engine_;
    const Store& store_;
    const std::uint64_t minimum_, maximum_;
    const hardware::FilterSettings boot_filters_;
    const hardware::PinPlan::Engine boot_engine_;
    const std::optional<hardware::Si5351Settings> boot_si5351_;
    const bool boot_ordinary_si5351_;
    const char* failure_ = nullptr;
    std::optional<time::gps::Calibration> gps_calibration_;
    std::uint64_t gps_now_ = 0;
    bool gps_clock_bound_ = false, gps_disagreement_ = false;
};
} // namespace wsprrypico::standalone
