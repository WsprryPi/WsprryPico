// SPDX-License-Identifier: MIT
#include "rf/si5351_engine.hpp"

#include "time/mapping.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace wsprrypico::rf::si5351 {
namespace {
std::uint64_t add(std::uint64_t left, std::uint64_t right) {
    return left > UINT64_MAX - right ? UINT64_MAX : left + right;
}
std::uint64_t realized_nhz(const Tone& tone) {
    return static_cast<std::uint64_t>(std::llround(tone.achieved_hz * 1'000'000'000.L));
}
} // namespace
Engine::Engine(const Configuration& configuration, Device& device, ExecutionPlatform& platform,
               bool engineering_allowed, IndicatorGate* indicator, AmplifierEnable* amplifier,
               FilterSelector* filters, bool ordinary_qualified)
    : configuration_(configuration), device_(device), platform_(platform),
      engineering_allowed_(engineering_allowed), ordinary_qualified_(ordinary_qualified),
      indicator_(indicator), amplifier_(amplifier), filters_(filters) {}
std::uint64_t Engine::amplifier_lead_ns() const {
    return amplifier_ && amplifier_->enabled() ? amplifier_->timing().lead_ns() : 0;
}
std::uint64_t Engine::amplifier_tail_ns() const {
    return amplifier_ && amplifier_->enabled() ? amplifier_->timing().tail_ns() : 0;
}
std::uint64_t Engine::filter_preparation_ns() const {
    // Leave owner/GPIO service time before the full configured lead/settle
    // intervals. A delayed poll still refuses a shortened interval at launch.
    return (filters_ && filters_->required() ? filters_->preparation_ns() : 0) +
           chain_service_margin_ns;
}
std::size_t Engine::preparation_memory_bytes(const wtp::Job& job) const {
    const auto marks = std::count_if(job.events.begin(), job.events.end(),
                                     [](const auto& event) { return event.rf_on; });
    return 4096 + marks * (sizeof(wtp::FrequencyAdjustment) + sizeof(std::uint16_t));
}
bool Engine::initialize() {
    // Idempotent initialization can reopen a failed controller for shutdown;
    // it never enables a clock or clears JobService fault/ownership state.
    initialized_ = platform_.initialize();
    if (!initialized_) {
        failure_ = "si5351_platform_unavailable";
        state_ = wtp::EngineState::Failed;
    }
    return initialized_;
}
bool Engine::set_frequency_correction_ppb(std::int32_t value) {
    if (state_ != wtp::EngineState::Idle || plan_ || inhibited_ || value < -correction_limit_ppb ||
        value > correction_limit_ppb)
        return false;
    correction_ppb_ = value;
    return true;
}
wtp::PrepareResult Engine::prepare(const wtp::Job& job) {
    if (!(engineering_allowed_ || ordinary_qualified_) || inhibited_ || background_suspended_ ||
        state_ != wtp::EngineState::Idle) {
        failure_ = !(engineering_allowed_ || ordinary_qualified_) ? "si5351_engineering_gate"
                                                                  : "si5351_not_idle";
        return {};
    }
    // All frequency/event and filter checks precede any hardware preparation.
    auto candidate = plan_job(configuration_, job, correction_ppb_, minimum_transition_ns, 0.001L);
    if (!candidate.plan) {
        failure_ = candidate.error;
        return {};
    }
    std::array<wtp::FrequencyAdjustment, Plan::maximum_tones * 2> coverage{};
    unsigned coverage_count = 0;
    for (const auto& tone : candidate.plan->synthesis.tones()) {
        const auto realized = realized_nhz(tone);
        // Guard the nHz projection against platform floating-point rounding.
        constexpr std::uint64_t guard = 1024;
        coverage[coverage_count++] = {0, tone.requested_nhz, realized - guard};
        coverage[coverage_count++] = {0, tone.requested_nhz, realized + guard};
    }
    if (filters_ && !filters_->prepare_frequencies(std::span(coverage).first(coverage_count))) {
        failure_ = "filter_coverage_required";
        return {};
    }
    wtp::PrepareResult result{true, {}};
    result.adjustments.reserve(std::count_if(job.events.begin(), job.events.end(),
                                             [](const auto& event) { return event.rf_on; }));
    for (std::size_t i = 0; i < job.events.size(); ++i) {
        if (!job.events[i].rf_on)
            continue;
        const auto realized =
            realized_nhz(candidate.plan->synthesis.tones()[candidate.plan->tone[i]]);
        if (realized != *job.events[i].frequency_nhz)
            result.adjustments.push_back({i, *job.events[i].frequency_nhz, realized});
    }
    if (!initialize())
        return {};
    const auto deadline = add(platform_.now_ns(), preparation_budget_ns);
    if (!platform_.pause_reference(deadline) || !platform_.set_gate(false)) {
        fail("si5351_prepare_shutdown_failed");
        return {};
    }
    if (!(device_.configured() ? device_.transmit_enabled(false, deadline)
                               : device_.quiesce(deadline))) {
        fail("si5351_prepare_shutdown_failed");
        return {};
    }
    // A previous job can leave PLLA on its final VHF tone. A fixed-PLL HF/LF
    // tone contains only its MultiSynth update, so reusing that state would
    // silently synthesize the next job against the wrong PLL frequency.
    // Restore the complete initial transmit plan once per job, while RF is
    // disabled. Device::configure preserves an established independent PLLB.
    if (!device_.configure(configuration_, candidate.plan->synthesis, deadline)) {
        fail("si5351_configuration_failed");
        return {};
    }
    bool locked = false;
    for (unsigned attempt = 0;
         attempt < 128 && platform_.now_ns() < deadline && device_.configured(); ++attempt)
        if (device_.locked(deadline)) {
            locked = true;
            break;
        }
    if (!locked || !device_.configured() || platform_.now_ns() >= deadline ||
        !device_.prime_transmit(deadline)) {
        fail("si5351_lock_or_prime_failed");
        return {};
    }
    plan_ = std::move(candidate.plan);
    primed_ = true;
    primed_tone_ = 0;
    launch_ns_.reset();
    failure_ = {};
    return result;
}
bool Engine::schedule(const wtp::Job& job, std::uint64_t start,
                      const wtp::LocalStartConditions& conditions) {
    if (!conditions.clock || !plan_ || background_suspended_ || state_ != wtp::EngineState::Idle ||
        start > UINT64_MAX - wtp::start_window_ns(conditions.start_utc_ns))
        return false;
    conditions_ = conditions;
    conditions_.start_adjustment_ns = (1000 - start % 1000) % 1000;
    const auto window = wtp::start_window_ns(conditions.start_utc_ns);
    if (conditions.start_utc_ns > UINT64_MAX - window ||
        !time::inverse(conditions.clock->snapshot(), conditions.start_utc_ns + window,
                       deadline_ns_))
        return false;
    std::uint64_t projected{};
    if (!project_start(projected))
        return false;
    return begin(job, start + conditions_.start_adjustment_ns);
}
bool Engine::begin(const wtp::Job& job, std::uint64_t start) {
    if (!plan_ || !primed_ || inhibited_ || background_suspended_ ||
        state_ != wtp::EngineState::Idle || plan_->digest != wtp::job_digest(job) ||
        epoch_ == UINT64_MAX ||
        start > UINT64_MAX - plan_->requested_duration_ns - amplifier_tail_ns() - 1'000'000 ||
        output_active())
        return false;
    const auto lead = amplifier_lead_ns() + filter_preparation_ns();
    if (start < lead || platform_.now_ns() > start - lead)
        return false;
    if (!platform_.pause_reference(add(platform_.now_ns(), transition_budget_ns)))
        return fail("si5351_reference_pause_failed");
    ++epoch_;
    start_ns_ = start;
    end_ns_ = start + static_cast<std::uint64_t>(plan_->end_us[plan_->count - 1]) * 1000;
    release_ns_.reset();
    selection_ns_.reset();
    enable_ns_.reset();
    tail_ns_.reset();
    launch_ns_.reset();
    enable_command_ns_ = disable_command_ns_ = 0;
    event_ = 0;
    amplifier_observation_ = {};
    amplifier_observation_.epoch = epoch_;
    amplifier_observation_.configured = amplifier_ && amplifier_->enabled();
    amplifier_observation_.lead_ms = unsigned(amplifier_lead_ns() / 1'000'000);
    amplifier_observation_.tail_ms = unsigned(amplifier_tail_ns() / 1'000'000);
    state_ = wtp::EngineState::Armed;
    phase_ = wtp::ChainPhase::Waiting;
    return true;
}
bool Engine::project_start(std::uint64_t& target) const {
    if (!conditions_.clock) {
        target = start_ns_;
        return platform_.now_ns() < add(start_ns_, 1'000'000'000);
    }
    const auto now = conditions_.clock->snapshot();
    const auto window = wtp::start_window_ns(conditions_.start_utc_ns);
    if (now.monotonic_now_ns >= deadline_ns_ ||
        now.uncertainty_ns > conditions_.maximum_uncertainty_ns ||
        !(now.state == wtp::ClockState::Synchronized ||
          (now.state == wtp::ClockState::Holdover && conditions_.maximum_holdover_age_ns &&
           now.sync_age_ns <= conditions_.maximum_holdover_age_ns)) ||
        now.utc_now_ns >= conditions_.start_utc_ns + window)
        return false;
    target = now.monotonic_now_ns;
    if (now.utc_now_ns < conditions_.start_utc_ns &&
        !time::inverse(now, conditions_.start_utc_ns, target))
        return false;
    const auto rounding = (1000 - target % 1000) % 1000;
    if (target > UINT64_MAX - rounding)
        return false;
    target += rounding;
    std::uint64_t mapped{}, rounding_utc{}, growth{};
    const bool pending =
        now.leap == wtp::LeapState::InsertPending || now.leap == wtp::LeapState::DeletePending;
    if (!time::project(now, target, mapped) || mapped >= conditions_.start_utc_ns + window ||
        target >= deadline_ns_ || now.leap == wtp::LeapState::Unknown ||
        pending != now.leap_transition_utc_ns.has_value() ||
        !time::growth(target - now.monotonic_now_ns, now.rate_uncertainty_ppb, growth) ||
        !time::elapsed_utc(rounding + (now.rate_ppb != 0), now.rate_ppb, rounding_utc, true) ||
        growth > conditions_.maximum_uncertainty_ns - now.uncertainty_ns ||
        rounding_utc > conditions_.maximum_uncertainty_ns - now.uncertainty_ns - growth)
        return false;
    if (now.leap_transition_utc_ns) {
        const auto leap = *now.leap_transition_utc_ns;
        const auto low = leap > 1'000'000'000 ? leap - 1'000'000'000 : 0;
        const auto high = add(leap, 1'000'000'000);
        const auto latest = conditions_.start_utc_ns + window - 1;
        std::uint64_t duration{};
        if (!time::duration_utc_bound(plan_->requested_duration_ns, now, duration) ||
            !(conditions_.start_utc_ns > high ||
              (latest <= UINT64_MAX - duration && latest + duration < low)))
            return false;
    }
    return true;
}
bool Engine::launch() {
    if (indicator_ && !indicator_->request_launch())
        return true; // The original UTC window, not arrival of an acknowledgement, bounds this.
    if ((filters_ && !filters_->verify()) ||
        (amplifier_ && amplifier_->enabled() && !amplifier_->verify_active()))
        return fail("si5351_launch_chain_changed");
    const auto deadline = add(platform_.now_ns(), transition_budget_ns);
    if (plan_->tone[0] != JobPlan::off && !device_.request_transmit_enabled(true, deadline))
        return fail("si5351_launch_write_failed");
    const auto completed = platform_.now_ns();
    if (conditions_.clock && completed >= deadline_ns_)
        return fail("si5351_launch_control_late");
    if (!platform_.set_gate(plan_->tone[0] != JobPlan::off))
        return fail("si5351_gate_enable_failed");
    launch_ns_ = completed;
    start_ns_ = completed;
    enable_command_ns_ = plan_->tone[0] != JobPlan::off ? completed : 0;
    end_ns_ = add(completed, static_cast<std::uint64_t>(plan_->end_us[plan_->count - 1]) * 1000);
    if (!platform_.arm_cutoff(end_ns_))
        return fail("si5351_cutoff_rejected");
    amplifier_observation_.rf_start_ns = enable_command_ns_;
    state_ = wtp::EngineState::Running;
    phase_ = wtp::ChainPhase::Rf;
    if (plan_->tone[0] != JobPlan::off &&
        !device_.verify_transmit(add(completed, transition_budget_ns)))
        return fail("si5351_launch_unconfirmed");
    return true;
}
bool Engine::transition(unsigned index) {
    const auto deadline = add(platform_.now_ns(), transition_budget_ns);
    const auto next = plan_->tone[index], previous = plan_->tone[index - 1];
    if (next == previous)
        return true;
    if (next == JobPlan::off) {
        if (!platform_.set_gate(false) || !device_.request_transmit_enabled(false, deadline))
            return fail("si5351_gap_shutdown_failed");
        disable_command_ns_ = platform_.now_ns();
        if (!device_.verify_transmit(deadline))
            return fail("si5351_gap_shutdown_unconfirmed");
        // Precompute/program the next keyed-on tone while the output is
        // masked, so its RF edge only needs the bounded enable transaction.
        for (unsigned following = index + 1; following < plan_->count; ++following) {
            const auto tone = plan_->tone[following];
            if (tone == JobPlan::off)
                continue;
            if (!device_.transmit_tone(plan_->synthesis.tones()[tone], deadline) ||
                !device_.prime_transmit(deadline))
                return fail("si5351_gap_tone_preparation_failed");
            primed_tone_ = tone;
            break;
        }
    } else {
        if ((previous != JobPlan::off || primed_tone_ != next) &&
            !device_.transmit_tone(plan_->synthesis.tones()[next], deadline))
            return fail("si5351_symbol_write_failed");
        if (previous == JobPlan::off) {
            if (!device_.prime_transmit(deadline) ||
                !device_.request_transmit_enabled(true, deadline))
                return fail("si5351_gap_restart_failed");
            enable_command_ns_ = platform_.now_ns();
            if (!amplifier_observation_.rf_start_ns)
                amplifier_observation_.rf_start_ns = enable_command_ns_;
            if (!platform_.set_gate(true) || !device_.verify_transmit(deadline))
                return fail("si5351_gap_restart_unconfirmed");
        }
        primed_tone_ = next;
    }
    return true;
}
bool Engine::finish_rf() {
    if (!platform_.set_gate(false))
        return fail("si5351_final_gate_failed");
    if (device_.transmit_state() != ClockOutputState::RegisterDisabled) {
        if (!device_.request_transmit_enabled(false, add(end_ns_, transition_budget_ns)))
            return fail("si5351_final_shutdown_request_failed");
        disable_command_ns_ = platform_.now_ns();
    }
    if (disable_command_ns_ > add(end_ns_, transition_budget_ns))
        return fail("si5351_final_shutdown_late");
    // With no amplifier tail, JobService invokes bounded verified disable
    // before terminal success under the WTP shutdown-confirmation deadline.
    // ACK is not misreported as physical RF readback.
    if (!amplifier_tail_ns()) {
        state_ = wtp::EngineState::Complete;
        return true;
    }
    if (!device_.verify_transmit(add(platform_.now_ns(), transition_budget_ns)))
        return fail("si5351_final_shutdown_unconfirmed");
    amplifier_observation_.rf_off_ns = platform_.now_ns();
    amplifier_observation_.normal_rf_completion = true;
    tail_ns_ = add(amplifier_observation_.rf_off_ns, amplifier_tail_ns());
    phase_ = wtp::ChainPhase::Tail;
    return true;
}
wtp::EngineReport Engine::poll(std::uint64_t) {
    if (state_ == wtp::EngineState::Idle) {
        platform_.service_reference(initialized_ && (engineering_allowed_ || ordinary_qualified_) &&
                                    !inhibited_ && !background_suspended_);
        return report();
    }
    const auto now = platform_.now_ns();
    if (state_ == wtp::EngineState::Armed) {
        std::uint64_t projected{};
        if (!project_start(projected)) {
            fail("si5351_launch_clock_rejected", wtp::EngineState::Missed);
            return report();
        }
        start_ns_ = projected;
        if (filters_ && filters_->required()) {
            const auto due =
                start_ns_ - std::min(start_ns_, amplifier_lead_ns() + filter_preparation_ns());
            if (!release_ns_ && now >= due) {
                if (!filters_->deactivate()) {
                    fail("filter_release_failed");
                    return report();
                }
                release_ns_ = platform_.now_ns();
                phase_ = wtp::ChainPhase::Selecting;
            }
            if (release_ns_ && !selection_ns_ && now >= add(*release_ns_, filters_->release_ns())) {
                if (!filters_->activate()) {
                    fail("filter_activation_failed");
                    return report();
                }
                selection_ns_ = platform_.now_ns();
            }
            if (!selection_ns_ || now < add(*selection_ns_, filters_->settle_ns()))
                return report();
        }
        if (amplifier_ && amplifier_->enabled()) {
            const auto due =
                start_ns_ - std::min(start_ns_, amplifier_lead_ns() + chain_service_margin_ns);
            if (!enable_ns_ && now >= due) {
                if (!amplifier_->activate()) {
                    fail("amplifier_activation_failed");
                    return report();
                }
                enable_ns_ = platform_.now_ns();
                amplifier_observation_.enable_ns = *enable_ns_;
                phase_ = wtp::ChainPhase::Lead;
            }
            if (!enable_ns_ || add(*enable_ns_, amplifier_lead_ns()) > start_ns_) {
                if (now >= start_ns_)
                    fail("shortened_amplifier_lead", wtp::EngineState::Missed);
                return report();
            }
        }
        if (now >= start_ns_)
            (void)launch();
    } else if (state_ == wtp::EngineState::Running && phase_ == wtp::ChainPhase::Tail) {
        if (tail_ns_ && now >= *tail_ns_) {
            if ((amplifier_ && !amplifier_->deactivate()) || (filters_ && !filters_->deactivate()))
                fail("si5351_tail_cleanup_failed");
            else {
                amplifier_observation_.disable_ns = platform_.now_ns();
                state_ = wtp::EngineState::Complete;
            }
        }
    } else if (state_ == wtp::EngineState::Running) {
        if (now >= end_ns_)
            (void)finish_rf();
        else if (now >= add(start_ns_, static_cast<std::uint64_t>(plan_->end_us[event_]) * 1000)) {
            const auto boundary =
                add(start_ns_, static_cast<std::uint64_t>(plan_->end_us[event_]) * 1000);
            if (now > add(boundary, transition_budget_ns) || event_ + 1 >= plan_->count)
                fail("si5351_transition_deadline");
            else if (transition(event_ + 1))
                ++event_;
        }
    }
    return report();
}
bool Engine::disable(std::uint64_t deadline) {
    const bool normal_completion = state_ == wtp::EngineState::Complete;
    const bool opened = initialize();
    platform_.cancel_cutoff();
    const bool gate = platform_.set_gate(false);
    const bool amplifier = !amplifier_ || amplifier_->deactivate();
    const bool reference = platform_.pause_reference(deadline);
    bool clocks = false;
    if (opened) {
        if (device_.configured()) {
            const bool transmit = device_.transmit_enabled(false, deadline);
            const bool reference_clock = device_.reference_enabled(false, deadline);
            clocks = transmit && reference_clock;
            if (!clocks && !device_.configured())
                clocks = device_.quiesce(deadline);
        } else
            clocks = device_.quiesce(deadline);
    }
    const bool filters = !filters_ || (clocks && filters_->deactivate());
    if (!opened || !gate || !amplifier || !reference || !clocks || !filters || output_active()) {
        state_ = wtp::EngineState::Failed;
        phase_ = wtp::ChainPhase::Fault;
        failure_ = "si5351_shutdown_unconfirmed";
        return false;
    }
    if (indicator_)
        indicator_->inactive();
    if (normal_completion) {
        if (!amplifier_observation_.rf_off_ns)
            amplifier_observation_.rf_off_ns = platform_.now_ns();
        amplifier_observation_.normal_rf_completion = true;
        if (!amplifier_observation_.disable_ns)
            amplifier_observation_.disable_ns = platform_.now_ns();
    }
    state_ = wtp::EngineState::Idle;
    phase_ = wtp::ChainPhase::Inactive;
    plan_.reset();
    primed_ = false;
    launch_ns_.reset();
    tail_ns_.reset();
    conditions_ = {};
    failure_ = {};
    return true;
}
bool Engine::fail(std::string_view reason, wtp::EngineState outcome) {
    const bool stopped = disable(add(platform_.now_ns(), 10'000'000));
    failure_ = reason;
    state_ = stopped ? outcome : wtp::EngineState::Failed;
    phase_ = wtp::ChainPhase::Fault;
    return false;
}
bool Engine::output_active() const {
    return device_.transmit_state() != ClockOutputState::RegisterDisabled ||
           platform_.gate_active_or_unknown() ||
           (amplifier_ && amplifier_->output_active_or_unknown()) ||
           (filters_ && filters_->output_active_or_unknown());
}
wtp::EngineReport Engine::report() const {
    return {state_, output_active(), launch_ns_,
            phase_, tail_ns_,        filters_ ? filters_->observation() : -1};
}
void Engine::inhibit_output() {
    inhibited_ = true;
    platform_.inhibit_reference();
}
bool Engine::background_work_allowed() const {
    return !background_suspended_ && state_ != wtp::EngineState::Armed &&
           state_ != wtp::EngineState::Running;
}
bool Engine::suspend_background(std::uint64_t deadline) {
    if (background_suspended_ || state_ != wtp::EngineState::Idle || output_active())
        return false;
    background_suspended_ = true;
    if (platform_.pause_reference(deadline) && !output_active())
        return true;
    background_suspended_ = false;
    return false;
}
void Engine::resume_background() {
    background_suspended_ = false;
}
Engine::Observation Engine::observation() const {
    return {device_.transmit_state(),
            device_.reference_state(),
            epoch_,
            enable_command_ns_,
            disable_command_ns_,
            amplifier_observation_,
            engineering_allowed_,
            inhibited_};
}
} // namespace wsprrypico::rf::si5351
