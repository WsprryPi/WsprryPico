// SPDX-License-Identifier: MIT
#include "application/test_tone.hpp"

#include "hardware/si5351_qualification.hpp"
#include "wtp/memory_budget.hpp"

namespace wsprrypico::application {
namespace {
constexpr std::string_view session = "dddddddddddddddddddddddddddddddd";
constexpr std::string_view principal = "application:test-tone";
std::string id(std::uint64_t value) {
    std::string result(32, '0');
    for (unsigned i = 0; i < 16; ++i)
        result[31 - i] = "0123456789abcdef"[(value >> (4 * i)) & 15];
    return result;
}
} // namespace
TestTone::TestTone(wtp::JobService& service, standalone::Store& store,
                   standalone::Scheduler& scheduler)
    : service_(service), store_(store), scheduler_(scheduler) {
    boot_ = service_.status(false).boot_id;
    service_.terminal_observer(terminal, this);
}
TestTone::~TestTone() {
    service_.terminal_observer(nullptr, nullptr);
}
TestToneReview TestTone::review(const TestToneProposal& proposal, bool pending) const {
    if (!policy_) {
        TestToneReview result;
        result.refusals[result.refusal_count++] = "test_tone_unavailable";
        return result;
    }
    return review_test_tone(proposal, context(pending), *policy_, service_.config(),
                            service_.clock_snapshot());
}
unsigned TestTone::boot_drive() const {
    const auto& si = scheduler_.active_si5351();
    return scheduler_.active_pins().engine == hardware::PinPlan::Engine::I2c
               ? (si ? si->synthesis.drive_ma : 0)
               : scheduler_.active_gpio_drive_ma();
}
TestToneContext TestTone::context(bool pending) const {
    const auto activity = service_.activity();
    TestToneContext context;
    context.boot_pins = scheduler_.active_pins();
    context.boot_drive_ma = boot_drive();
    context.boot_si5351 = scheduler_.active_si5351();
    context.physical_si5351 = service_.config().capability_engine == "si5351" ||
                              service_.config().capability_engine == "si5351-engineering";
    context.physical_direct = service_.config().capability_engine == "pio-dma-gp2";
    context.wspr_enabled = store_.config() && store_.config()->enabled;
    context.message_enabled = store_.message_schedule() && store_.message_schedule()->enabled;
    context.owned = activity.owned;
    context.busy = activity.output_active || activity.state == wtp::State::Loaded ||
                   activity.state == wtp::State::Armed || activity.state == wtp::State::Running;
    context.faulted = activity.state == wtp::State::Failed ||
                      scheduler_.hardware_application_failed() ||
                      scheduler_.message_recovery_required() || scheduler_.message_pause_pending();
    context.maintenance = service_.maintenance() || pending;
    context.restart_required = scheduler_.reboot_required();
    // A drive-only restart latch must not suppress a numerical projection.
    const auto& config = store_.config();
    auto saved_si5351 = config ? config->si5351 : std::nullopt;
    if (saved_si5351 && context.boot_si5351)
        saved_si5351->synthesis.drive_ma = context.boot_si5351->synthesis.drive_ma;
    context.other_hardware_pending =
        config &&
        (config->pins != context.boot_pins ||
         config->amplifier_timing != scheduler_.active_amplifier_timing() ||
         saved_si5351 != scheduler_.active_si5351() || config->gps != scheduler_.active_gps() ||
         store_.filters() != scheduler_.active_filters());
    context.recovery_inhibited =
        service_.output_inhibited() && !scheduler_.hardware_restart_required();
    context.preparation_lead_ns = scheduler_.message_lead_ns();
    context.start_resolution_ns = service_.start_resolution_ns();
    return context;
}
wtp::Response TestTone::command(std::string_view operation, wtp::RequestBody body) {
    if (native_sequence_ == UINT64_MAX) {
        wtp::Response result;
        result.error = wtp::ErrorCode::DeviceFault;
        return result;
    }
    wtp::Request request;
    request.session_id = session;
    request.principal = principal;
    request.request_id = id(++native_sequence_);
    request.operation = operation;
    request.payload_digest =
        wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(request.request_id.data()),
                              request.request_id.size()));
    request.body = std::move(body);
    if (const auto* arm = std::get_if<wtp::ArmBody>(&request.body)) {
        const auto* record = find(arm->job_id, true);
        return service_.handle_internal(
            std::move(request),
            [](const wtp::PadObservation& pad, const wtp::SynthesisObservation& synthesis,
               const void* context) {
                const auto* record = static_cast<const TestToneRecord*>(context);
                if (!record)
                    return false;
                if (record->synthesis_configuration) {
                    const auto& c = *record->synthesis_configuration;
                    return synthesis.epoch &&
                           synthesis.transmit_output == static_cast<int>(c.transmit) &&
                           synthesis.drive_ma == int(record->proposal.proposed_drive_ma) &&
                           synthesis.reference_hz == c.reference_hz;
                }
                return record->rf_pin && pad.epoch && pad.rf_pin == int(*record->rf_pin) &&
                       pad.drive_ma == int(record->proposal.proposed_drive_ma);
            },
            record);
    }
    if (operation == "LOAD")
        return service_.handle_internal_test_tone_load(std::move(request));
    return service_.handle_internal(std::move(request));
}
TestToneRecord* TestTone::find(std::string_view value, bool job) {
    for (auto& item : records_)
        if (item && (job ? item->job_id : item->request_id) == value)
            return &*item;
    return nullptr;
}
void TestTone::settle(TestToneRecord& record, wtp::State state, wtp::ErrorCode error, bool inactive,
                      std::uint64_t now) {
    if (record.terminal)
        return;
    record.state = state;
    record.error = error;
    record.ended_ns = now;
    record.terminal = true;
    record.output_inactive_confirmed = inactive;
    record.recovery_required = !inactive || state == wtp::State::Failed;
    record.control_revision[record.control_revision.size() - 2] = '2';
}
void TestTone::terminal(const wtp::TerminalRecord& terminal, void* context) {
    auto& self = *static_cast<TestTone*>(context);
    if (auto* record = self.find(terminal.job_id, true)) {
        record->launch_ns = self.service_.execution_launch(terminal.job_id);
        self.settle(*record, terminal.state, terminal.error,
                    !terminal.output_active && terminal.error != wtp::ErrorCode::OutputStateUnknown,
                    terminal.ended_monotonic_ns);
    }
}
void TestTone::prune() {
    const auto now = service_.clock_snapshot().monotonic_now_ns;
    for (auto& item : records_)
        if (item && item->terminal && !item->recovery_required && now >= item->ended_ns &&
            now - item->ended_ns >= retention_ns)
            item.reset();
    for (;;) {
        std::size_t count = 0;
        auto oldest = records_.end();
        for (auto it = records_.begin(); it != records_.end(); ++it)
            if (*it && (*it)->terminal && !(*it)->recovery_required) {
                ++count;
                if (oldest == records_.end() || (*it)->sequence < (*oldest)->sequence)
                    oldest = it;
            }
        if (count <= terminal_capacity)
            break;
        oldest->reset();
    }
}
void TestTone::poll() {
    const auto observed = service_.status(false);
    if (observed.boot_id != boot_) {
        // Do not construct a second receipt array on the guarded Pico stack.
        // poll() also runs inside the nested authenticated Stop/release path.
        for (auto& record : records_)
            record.reset();
        admission_sequence_ = native_sequence_ = 0;
        boot_ = observed.boot_id;
    }
    for (auto& item : records_) {
        if (!item)
            continue;
        if (!item->terminal && observed.job_id == item->job_id) {
            item->state = observed.state;
            const auto chain = service_.rf_chain_observation();
            if (chain.launch_monotonic_ns)
                item->launch_ns = chain.launch_monotonic_ns;
        }
        if (item->terminal && !item->recovery_required && service_.owner_session_id() == session &&
            observed.job_id == item->job_id) {
            // RELEASE only this producer after native confirmed shutdown.
            (void)command("HELLO", wtp::HelloBody{{"WTP/1"}});
            (void)command("RELEASE");
        }
    }
    prune();
}
TestTone::Result TestTone::status(const TestToneAuthority& authority, std::string_view selector,
                                  bool job) {
    poll();
    auto* record = find(selector, job);
    if (!record)
        return {nullptr, "receipt_unavailable"};
    if (!(record->authority == authority))
        return {nullptr, "foreign_authority"};
    return {record, {}};
}
TestTone::Result TestTone::start(const TestToneAuthority& authority, std::string_view request,
                                 const TestToneProposal& proposal, std::string_view match,
                                 std::string_view current_revision, bool pending) {
    poll();
    if (auto* record = find(request, false)) {
        if (!(record->authority == authority))
            return {nullptr, "foreign_authority"};
        if (record->admission_revision != match || record->proposal.engine != proposal.engine ||
            record->proposal.carrier_hz != proposal.carrier_hz ||
            record->proposal.duration_ms != proposal.duration_ms ||
            record->proposal.proposed_drive_ma != proposal.proposed_drive_ma)
            return {nullptr, "request_conflict"};
        return {record, {}};
    }
    if (match.empty())
        return {nullptr, "revision_required"};
    if (match != current_revision)
        return {nullptr, "revision_conflict"};
    if (!authority.valid())
        return {nullptr, "invalid_authority"};
    if (proposal.engine != scheduler_.active_pins().engine)
        return {nullptr, "engine_mismatch"};
    if (proposal.proposed_drive_ma != boot_drive())
        return {nullptr, "boot_drive_mismatch"};
    const auto assessment = review(proposal, pending);
    if (assessment.admission != TestToneAdmission::Ready)
        return {nullptr,
                assessment.admission == TestToneAdmission::RequiresRestart ? "restart_required"
                                                                           : assessment.refusals[0],
                assessment.clock_error};
    if (service_.output_inhibited())
        return {nullptr, "output_recovery_required"};
    if (admission_sequence_ == UINT64_MAX || native_sequence_ > UINT64_MAX - 16)
        return {nullptr, "identifier_exhausted"};
    auto slot =
        std::find_if(records_.begin(), records_.end(), [](const auto& item) { return !item; });
    if (slot == records_.end())
        return {nullptr, "receipt_capacity"};
    wtp::Job job;
    job.job_id = id(admission_sequence_ + 1);
    // Reserve a private namespace within this boot, independent of client IDs.
    job.job_id[0] = 'd';
    job.mode = "tone";
    job.allow_frequency_adjustment = true;
    job.total_duration_ns = proposal.duration_ms * 1'000'000;
    if (!wtp::memory_admitted(service_.preparation_memory_bytes(job) + 16'384) ||
        !job.events.push_back({0, job.total_duration_ns, true, assessment.requested_nhz}))
        return {nullptr, "resource_exhausted"};
    // All receipt strings and the output response budget are allocated before CLAIM.
    TestToneRecord record;
    record.authority = authority;
    record.request_id = request;
    record.job_id = job.job_id;
    record.rf_pin = scheduler_.active_pins().rf;
    record.execution_engine = service_.config().capability_engine;
    if (proposal.engine == hardware::PinPlan::Engine::I2c) {
        record.synthesis_configuration = scheduler_.active_si5351()->synthesis;
        record.matched_profile = hardware::si5351_ordinary_qualified(
            scheduler_.active_pins(), *scheduler_.active_si5351(), rf::sample_rate,
            scheduler_.active_filters());
    }
    record.proposal = proposal;
    record.assessment = assessment;
    record.admission_revision = match;
    record.sequence = admission_sequence_ + 1;
    record.accepted_ns = service_.clock_snapshot().monotonic_now_ns;
    record.control_revision = "\"tone:" + service_.status(false).boot_id + ':' +
                              std::to_string(admission_sequence_ + 1) + ":1\"";
    slot->emplace(std::move(record));
    auto& accepted = **slot;
    ++admission_sequence_; // Never reused, even after receipt eviction or partial admission.
    auto result = command("HELLO", wtp::HelloBody{{"WTP/1"}});
    bool claimed = false;
    if (result.ok) {
        result = command("CLAIM", wtp::ClaimBody{accepted.job_id, 60'000});
        claimed = result.ok;
    }
    if (result.ok) {
        result = command("LOAD", std::move(job));
        if (result.ok) {
            // Preserve the actual LOAD realization, not a later fresh prediction.
            for (const auto& adjustment : result.adjustments)
                if (adjustment.event_index == 0)
                    accepted.assessment.frequency.programmed_nhz =
                        adjustment.realized_frequency_nhz;
            if (policy_)
                accepted.assessment.frequency.correction = policy_->prepared_correction();
            // Preparation may have consumed lead time. Pick the launch again now.
            const auto launch = review_test_tone(proposal, context(false), *policy_,
                                                 service_.config(), service_.clock_snapshot());
            if (!launch.launch_utc_ns) {
                result.ok = false;
                result.error = launch.clock_error;
            } else {
                accepted.assessment.launch_utc_ns = launch.launch_utc_ns;
                result = command("ARM", wtp::ArmBody{accepted.job_id, *launch.launch_utc_ns,
                                                     service_.config().maximum_arm_uncertainty_ns});
                accepted.pad = service_.execution_pad(accepted.job_id);
                accepted.synthesis = service_.execution_synthesis(accepted.job_id);
                if (result.ok)
                    accepted.assessment.launch_monotonic_ns = result.start_monotonic_ns;
            }
        }
    }
    if (!result.ok) {
        if (claimed && service_.status(false).job_id == accepted.job_id && !accepted.terminal)
            (void)command("ABORT", wtp::AbortBody{accepted.job_id});
        if (!accepted.terminal) {
            const auto activity = service_.activity();
            settle(accepted, wtp::State::Failed, result.error, !activity.output_active,
                   service_.clock_snapshot().monotonic_now_ns);
            // A rejected LOAD/CLAIM with no native fault is an identified failed
            // admission, not an unresolved engine shutdown.
            accepted.recovery_required =
                activity.state == wtp::State::Failed || activity.output_active;
        } else if (accepted.state == wtp::State::Aborted) {
            accepted.state = wtp::State::Failed;
            accepted.error = result.error;
        }
        if (claimed && service_.owner_session_id() == session && !service_.status(false).job_id &&
            service_.activity().state != wtp::State::Failed)
            (void)command("RELEASE");
    } else
        accepted.state = wtp::State::Armed;
    poll();
    return {&accepted, {}};
}
TestTone::Result TestTone::stop(const TestToneAuthority& authority, std::string_view job,
                                std::string_view match) {
    auto result = status(authority, job, true);
    if (!result.record)
        return result;
    auto& record = *result.record;
    if (match.empty())
        return {nullptr, "revision_required"};
    // A terminal repeated Stop may carry the original active control revision.
    auto original = record.control_revision;
    original[original.size() - 2] = '1';
    if (match != record.control_revision && !(record.terminal && match == original))
        return {nullptr, "revision_conflict"};
    if (record.terminal)
        return {&record, {}};
    const auto observed = service_.status(false);
    if (observed.job_id != job || service_.owner_session_id() != session)
        return {nullptr, "native_job_mismatch"};
    (void)command("HELLO", wtp::HelloBody{{"WTP/1"}});
    const auto stopped = command("ABORT", wtp::AbortBody{record.job_id});
    if (!stopped.ok && !record.terminal) {
        settle(record, wtp::State::Failed, stopped.error, false,
               service_.clock_snapshot().monotonic_now_ns);
    }
    poll();
    return {&record, {}};
}
} // namespace wsprrypico::application
