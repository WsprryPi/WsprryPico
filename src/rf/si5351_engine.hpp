// SPDX-License-Identifier: MIT
#pragma once
#include "rf/amplifier_enable.hpp"
#include "rf/filter_selector.hpp"
#include "rf/indicator_gate.hpp"
#include "rf/si5351_device.hpp"
#include "rf/si5351_job.hpp"

namespace wsprrypico::rf::si5351 {
// The execution owner also owns this adapter. Bus, capture, discovery and
// reference work never run concurrently with a symbol-time transaction.
class ExecutionPlatform {
  public:
    virtual ~ExecutionPlatform() = default;
    virtual std::uint64_t now_ns() const = 0;
    virtual bool initialize() = 0;
    virtual bool set_gate(bool active) = 0;
    virtual bool gate_active_or_unknown() const = 0;
    virtual bool arm_cutoff(std::uint64_t end_ns) = 0;
    virtual void cancel_cutoff() = 0;
    virtual bool pause_reference(std::uint64_t deadline_ns) = 0;
    virtual void service_reference(bool permitted) = 0;
    virtual void inhibit_reference() = 0;
};

class Engine final : public wtp::RfEngine {
  public:
    Engine(const Configuration& configuration, Device& device, ExecutionPlatform& platform,
           bool engineering_allowed, IndicatorGate* indicator = nullptr,
           AmplifierEnable* amplifier = nullptr, FilterSelector* filters = nullptr,
           bool ordinary_qualified = false);
    std::size_t preparation_memory_bytes(const wtp::Job&) const override;
    wtp::PrepareResult prepare(const wtp::Job&) override;
    bool set_frequency_correction_ppb(std::int32_t) override;
    bool schedules_locally() const override {
        return true;
    }
    bool owns_execution_plan() const override {
        return true;
    }
    std::uint64_t start_resolution_ns() const override {
        return 1000;
    }
    std::uint64_t completion_acknowledgement_ns() const override {
        return transition_budget_ns;
    }
    bool externally_controlled_completion() const override {
        return true;
    }
    std::uint64_t amplifier_lead_ns() const override;
    std::uint64_t amplifier_tail_ns() const override;
    std::uint64_t filter_preparation_ns() const override;
    bool schedule(const wtp::Job&, std::uint64_t, const wtp::LocalStartConditions&) override;
    bool begin(const wtp::Job&, std::uint64_t) override;
    wtp::EngineReport poll(std::uint64_t) override;
    bool disable(std::uint64_t deadline_ns) override;
    bool output_active() const override;
    bool execution_started() const override {
        return launch_ns_.has_value();
    }
    std::string_view diagnostic() const override {
        return failure_;
    }
    // Called by the owner on permanent configuration/recovery inhibition.
    void inhibit_output() override;
    bool background_work_allowed() const override;
    // RF-owner rendezvous before halting this core for flash access. Interrupted
    // reference windows are discarded; this never clears permanent inhibition.
    bool suspend_background(std::uint64_t deadline_ns);
    void resume_background();

    struct Observation {
        ClockOutputState transmit = ClockOutputState::Unknown;
        ClockOutputState reference = ClockOutputState::Unknown;
        std::uint64_t epoch = 0, enable_command_completed_ns = 0;
        std::uint64_t disable_command_completed_ns = 0;
        AmplifierObservation amplifier;
        bool engineering_allowed = false, inhibited = false;
    };
    Observation observation() const;

  private:
    static constexpr std::uint64_t preparation_budget_ns = 60'000'000;
    static constexpr std::uint64_t transition_budget_ns = 8'000'000;
    static constexpr std::uint64_t minimum_transition_ns = 10'000'000;
    static constexpr std::uint64_t chain_service_margin_ns = 1'000'000;
    bool initialize();
    bool fail(std::string_view, wtp::EngineState = wtp::EngineState::Failed);
    bool project_start(std::uint64_t& target) const;
    bool launch();
    bool transition(unsigned index);
    bool finish_rf();
    wtp::EngineReport report() const;
    const Configuration configuration_;
    Device& device_;
    ExecutionPlatform& platform_;
    const bool engineering_allowed_;
    const bool ordinary_qualified_;
    IndicatorGate* indicator_;
    AmplifierEnable* amplifier_;
    FilterSelector* filters_;
    bool initialized_ = false, inhibited_ = false, primed_ = false, background_suspended_ = false;
    std::optional<JobPlan> plan_;
    std::int32_t correction_ppb_ = 0;
    wtp::EngineState state_ = wtp::EngineState::Idle;
    wtp::ChainPhase phase_ = wtp::ChainPhase::Inactive;
    wtp::LocalStartConditions conditions_;
    std::uint64_t epoch_ = 0, start_ns_ = 0, end_ns_ = 0, deadline_ns_ = 0;
    std::optional<std::uint64_t> launch_ns_, release_ns_, selection_ns_, enable_ns_, tail_ns_;
    std::uint64_t enable_command_ns_ = 0, disable_command_ns_ = 0;
    AmplifierObservation amplifier_observation_;
    unsigned event_ = 0;
    std::uint8_t primed_tone_ = JobPlan::off;
    std::string_view failure_ = "not_initialized";
};
} // namespace wsprrypico::rf::si5351
