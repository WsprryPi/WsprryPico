// SPDX-License-Identifier: MIT
#include "application/resources.hpp"
#include "hardware/si5351_qualification.hpp"
#include "network/api.hpp"
#include "network/control_contract.hpp"
#include "network/test_tone_query.hpp"
#include "rf/waveform.hpp"
#include "runtime/memory_budget.hpp"
#include "rf/observation.hpp"

#include <charconv>
#include <climits>

namespace wsprrypico::network {
namespace {
using execution::json::quote;
std::string number(std::uint64_t value) {
    return quote(std::to_string(value));
}
std::string optional_number(std::optional<std::uint64_t> value) {
    return value ? number(*value) : "null";
}
std::string boolean(bool value) {
    return value ? "true" : "false";
}
std::string engine_name(hardware::PinPlan::Engine engine) {
    return engine == hardware::PinPlan::Engine::I2c ? "si5351" : "pio-dma-gp2";
}
std::string synthesis_identity(const std::optional<rf::si5351::Configuration>& configuration,
                               std::string_view execution) {
    const bool synthesis = configuration.has_value();
    return ",\"execution_engine\":" + quote(execution) + ",\"transmit_output\":" +
           (synthesis ? std::to_string(static_cast<unsigned>(configuration->transmit)) : "null") +
           ",\"reference_hz\":" +
           (synthesis ? std::to_string(configuration->reference_hz) : "null");
}
bool integer(execution::json::Value value, std::uint64_t& out) {
    if (value.raw.empty() || value.raw.size() > 20)
        return false;
    std::string raw(value.raw);
    if ((raw.size() > 1 && raw[0] == '0') || raw.find_first_not_of("0123456789") != raw.npos)
        return false;
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), out);
    return parsed.ec == std::errc{} && parsed.ptr == raw.data() + raw.size();
}
std::string realization(const application::TestToneReview& r, bool synthesis) {
    const auto& f = r.frequency;
    std::string correction = "null";
    if (f.correction) {
        const auto& c = *f.correction;
        correction = "{\"ppb\":" + std::to_string(c.ppb) +
                     ",\"automatic\":" + boolean(c.automatic) +
                     ",\"generation\":" + number(c.generation) +
                     ",\"observed_raw_ns\":" + number(c.observed_raw_ns) +
                     ",\"uncertainty_ppb\":" + std::to_string(c.uncertainty_ppb) + "}";
    }
    return "{\"requested_nhz\":" + optional_number(r.requested_nhz) +
           ",\"programmed_nhz\":" + optional_number(f.programmed_nhz) +
           ",\"increment\":" + (f.increment ? std::to_string(*f.increment) : "null") +
           ",\"nominal_sample_hz\":" + (synthesis ? "null" : std::to_string(rf::sample_rate)) +
           ",\"quantization_bound_nhz\":" +
           (f.programmed_nhz ? number(r.quantization_bound_nhz) : "null") +
           ",\"correction\":" + correction + "}";
}
std::string record_json(const application::TestToneRecord& r) {
    const char* phase = r.terminal                       ? "terminal"
                        : r.state == execution::State::Running ? "running"
                                                         : "accepted";
    const char* outcome = r.state == execution::State::Complete  ? "completed"
                          : r.state == execution::State::Aborted ? "stopped"
                          : r.state == execution::State::Missed  ? "missed"
                                                           : "failed";
    const auto& pad = r.pad;
    const bool verified_pad = r.rf_pin && pad.epoch && pad.rf_pin == int(*r.rf_pin) &&
                              pad.drive_ma == int(r.proposal.proposed_drive_ma);
    const bool synthesis = r.synthesis_configuration.has_value();
    const auto& observation = r.synthesis;
    const bool verified_synthesis =
        synthesis && observation.epoch &&
        observation.transmit_output == static_cast<int>(r.synthesis_configuration->transmit) &&
        observation.reference_hz == r.synthesis_configuration->reference_hz &&
        observation.drive_ma == static_cast<int>(r.proposal.proposed_drive_ma);
    const auto synthesis_readback =
        !synthesis
            ? "null"
            : "{\"epoch\":" + (observation.epoch ? number(observation.epoch) : "null") +
                  ",\"observed_monotonic_ns\":" +
                  (observation.epoch ? number(observation.observed_monotonic_ns) : "null") +
                  ",\"transmit_output\":" +
                  (observation.transmit_output >= 0 ? std::to_string(observation.transmit_output)
                                                    : "null") +
                  ",\"reference_hz\":" +
                  (observation.reference_hz ? std::to_string(observation.reference_hz) : "null") +
                  ",\"drive_ma\":" +
                  (observation.drive_ma > 0 ? std::to_string(observation.drive_ma) : "null") +
                  ",\"stage\":" +
                  quote(verified_synthesis  ? "verified"
                        : observation.epoch ? "failed"
                                            : "unavailable") +
                  "}";
    return "{\"request_id\":" + quote(r.request_id) + ",\"job_id\":" + quote(r.job_id) +
           ",\"phase\":" + quote(phase) + ",\"native_state\":" + quote(execution::state_name(r.state)) +
           ",\"outcome\":" + (r.terminal ? quote(outcome) : "null") +
           ",\"carrier_hz\":" + std::to_string(r.proposal.carrier_hz) +
           ",\"duration_ms\":" + std::to_string(r.proposal.duration_ms) +
           ",\"engine\":" + quote(engine_name(r.proposal.engine)) +
           synthesis_identity(r.synthesis_configuration, r.execution_engine) +
           ",\"profile_id\":" + (r.matched_profile ? quote(hardware::si5351_support::id) : "null") +
           ",\"rf_pin\":" + (r.rf_pin ? std::to_string(*r.rf_pin) : "null") +
           ",\"boot_drive_ma\":" + std::to_string(r.proposal.proposed_drive_ma) +
           ",\"admission_revision\":" + quote(r.admission_revision) +
           ",\"control_revision\":" + quote(r.control_revision) +
           ",\"accepted_monotonic_ns\":" + number(r.accepted_ns) +
           ",\"scheduled_utc_ns\":" + optional_number(r.assessment.launch_utc_ns) +
           ",\"scheduled_monotonic_ns\":" + optional_number(r.assessment.launch_monotonic_ns) +
           ",\"launch_monotonic_ns\":" + optional_number(r.launch_ns) +
           ",\"ended_monotonic_ns\":" + (r.terminal ? number(r.ended_ns) : "null") +
           ",\"realization\":" + realization(r.assessment, synthesis) + ",\"pad_readback\":" +
           (synthesis
                ? "null"
                : "{\"epoch\":" + (pad.epoch ? number(pad.epoch) : "null") +
                      ",\"observed_monotonic_ns\":" +
                      (pad.drive_ma != -1 ? number(pad.observed_monotonic_ns) : "null") +
                      ",\"rf_pin\":" + (pad.rf_pin >= 0 ? std::to_string(pad.rf_pin) : "null") +
                      ",\"drive_ma\":" +
                      (pad.drive_ma > 0 ? std::to_string(pad.drive_ma) : "null") + ",\"stage\":" +
                      quote(verified_pad         ? "verified"
                            : pad.drive_ma != -1 ? "failed"
                                                 : "unavailable") +
                      "}") +
           ",\"synthesis_readback\":" + synthesis_readback + ",\"inactivity_basis\":" +
           quote(synthesis ? "si5351_register_shutdown" : "native_gpio_shutdown") +
           ",\"output_inactive_confirmed\":" + boolean(r.output_inactive_confirmed) +
           ",\"recovery_required\":" + boolean(r.recovery_required) + ",\"native_error\":" +
           (r.error == execution::ErrorCode::None ? "null" : execution::error_json(r.error)) + "}";
}
} // namespace
std::string BrowserApi::test_tone_capability() const {
    auto descriptor = std::string(control_descriptor("test_tone"));
    descriptor.pop_back();
    const auto limit = std::min({application::test_tone_maximum_duration_ms,
                                 service_.config().max_job_duration_ns / 1'000'000,
                                 rf::max_duration_ns / 1'000'000});
    const auto& execution = service_.config().capability_engine;
    const bool available =
        test_tone_.supported() &&
        (execution == "pio-dma-gp2" || execution == "si5351" || execution == "si5351-engineering");
    const bool synthesis = scheduler_.active_pins().engine == hardware::PinPlan::Engine::I2c;
    return descriptor + ",\"available\":" + boolean(available) + ",\"active_engine\":" +
           (available ? quote(synthesis ? "si5351" : "pio-dma-gp2") : "null") +
           ",\"minimum_duration_ms\":" + std::to_string(available ? (synthesis ? 10 : 1) : 0) +
           ",\"maximum_duration_ms\":" + std::to_string(limit) +
           ",\"output_disable_timeout_ns\":" + number(service_.config().output_disable_timeout_ns) +
           "}";
}
HttpResponse BrowserApi::test_tone_resource(const HttpRequest& request,
                                            const application::TestToneAuthority& authority) {
    constexpr std::string_view prefix = "/api/control/v1/test-tone/";
    const auto operation = std::string_view(request.path).substr(prefix.size());
    const auto boot = service_.status(false).boot_id;
    const auto saved_config = saved_settings();
    const auto& pins = scheduler_.active_pins();
    const bool synthesis = pins.engine == hardware::PinPlan::Engine::I2c;
    const auto& boot_si = scheduler_.active_si5351();
    const auto boot_drive =
        synthesis ? (boot_si ? boot_si->synthesis.drive_ma : 0) : scheduler_.active_gpio_drive_ma();
    const auto saved_drive =
        !saved_config ? "null"
        : synthesis
            ? (saved_config->si5351 ? std::to_string(saved_config->si5351->synthesis.drive_ma)
                                    : "null")
            : std::to_string(saved_config->gpio_drive_ma);
    const bool matched_profile = synthesis && boot_si &&
                                 hardware::si5351_ordinary_qualified(
                                     pins, *boot_si, rf::sample_rate, scheduler_.active_filters());
    const std::optional<rf::si5351::Configuration> boot_synthesis =
        synthesis && boot_si ? std::optional(boot_si->synthesis) : std::nullopt;
    if (!test_tone_.supported())
        return http_error(409, "test_tone_unavailable");
    if (!execution::memory_admitted(16'384))
        return http_error(503, "resource_exhausted");
    HttpResponse response;
    response.body.reserve(4096); // reserve the bounded reply before Start/Stop effects
    const auto status_response = [&](const application::TestTone::Result& result, unsigned code) {
        if (!result.error.empty() && result.error != "receipt_unavailable") {
            const auto status =
                result.error == "foreign_authority"                                          ? 403
                : result.error == "revision_required"                                        ? 428
                : result.error == "revision_conflict"                                        ? 412
                : result.error == "resource_exhausted" || result.error == "receipt_capacity" ? 503
                                                                                             : 409;
            auto failure = http_error(status, result.error);
            if (result.native_error != execution::ErrorCode::None)
                failure.body = "{\"error\":" + quote(result.error) +
                               ",\"native_error\":" + execution::error_json(result.native_error) + "}";
            return failure;
        }
        const auto current = service_.activity();
        response.status = result.record ? code : 404;
        response.body =
            "{\"schema\":\"test-tone-status\",\"target\":" + application::target(device_, boot) +
            ",\"receipt\":" + quote(result.record ? "known" : "receipt_unavailable") +
            ",\"job\":" + (result.record ? record_json(*result.record) : "null") +
            ",\"observation_monotonic_ns\":" + number(service_.clock_snapshot().monotonic_now_ns) +
            ",\"current\":{\"engine\":" + quote(engine_name(pins.engine)) +
            ",\"saved_drive_ma\":" + saved_drive +
            ",\"boot_drive_ma\":" + std::to_string(boot_drive) +
            ",\"output_active\":" + boolean(current.output_active) +
            ",\"owned\":" + boolean(current.owned) +
            ",\"native_state\":" + quote(execution::state_name(current.state)) + "}}";
        if (result.record)
            response.etag = result.record->control_revision;
        return std::move(response);
    };
    if (request.method == "GET") {
        if (!request.body_view().empty())
            return http_error(400, "unexpected_status_body");
        const auto query = test_tone_query(request.path);
        if (!query)
            return http_error(400, "invalid_test_tone_selector");
        if (query->device != device_ || query->boot != boot)
            return http_error(409, "target_mismatch");
        return status_response(test_tone_.status(authority, query->selector, query->by_job), 200);
    }
    const auto root = execution::json::parse(request.body_view());
    if (!root || root->type() != '{')
        return http_error(400, "invalid_test_tone_request");
    using execution::json::fields;
    const bool review = operation == "review", start = operation == "start",
               stop = operation == "stop";
    if (request.method != "POST" || (!review && !start && !stop))
        return http_error(404, "not_found");
    if (!(review  ? fields(*root, {"schema", "target", "tone"})
          : start ? fields(*root, {"schema", "target", "request_id", "tone"})
                  : fields(*root, {"schema", "target", "job_id"})))
        return http_error(400, "invalid_test_tone_request");
    const auto schema = *root->get("schema"), target = *root->get("target");
    if (schema.type() != '"' || schema.string() != "test-tone-" + std::string(operation) ||
        !fields(target, {"scope", "device_id", "boot_id"}))
        return http_error(400, "invalid_test_tone_request");
    for (const auto name : {"scope", "device_id", "boot_id"})
        if (target.get(name)->type() != '"')
            return http_error(400, "invalid_test_tone_target");
    if (target.get("scope")->string() != "member" || target.get("device_id")->string() != device_ ||
        target.get("boot_id")->string() != boot)
        return http_error(409, "target_mismatch");
    if (stop) {
        if (!execution::json::identifier(*root->get("job_id")))
            return http_error(400, "invalid_job_id");
        return status_response(
            test_tone_.stop(authority, root->get("job_id")->string(), request.header("if-match")),
            200);
    }
    const auto tone = *root->get("tone");
    const auto drive_key = review ? "proposed_drive_ma" : "expected_drive_ma";
    if (!fields(tone, {"engine", "carrier_hz", "duration_ms", drive_key}))
        return http_error(400, "invalid_tone");
    application::TestToneProposal proposal;
    std::uint64_t drive;
    if (!integer(*tone.get("carrier_hz"), proposal.carrier_hz) ||
        !integer(*tone.get("duration_ms"), proposal.duration_ms) ||
        !integer(*tone.get(drive_key), drive) || drive > UINT_MAX)
        return http_error(400, "invalid_tone_integer");
    const auto requested_engine = tone.get("engine");
    if (requested_engine->type() != '"' ||
        (requested_engine->string() != "pio-dma-gp2" && requested_engine->string() != "si5351"))
        return http_error(400, "invalid_tone_engine");
    proposal.engine = requested_engine->string() == "si5351" ? hardware::PinPlan::Engine::I2c
                                                             : hardware::PinPlan::Engine::Direct;
    proposal.proposed_drive_ma = static_cast<unsigned>(drive);
    if (start) {
        if (!execution::json::identifier(*root->get("request_id")))
            return http_error(400, "invalid_request_id");
        return status_response(test_tone_.start(authority, root->get("request_id")->string(),
                                                proposal, request.header("if-match"), revision(),
                                                mutation_pending()),
                               202);
    }
    const auto assessed = test_tone_.review(proposal, mutation_pending());
    std::string reasons = "[";
    for (std::size_t i = 0; i < assessed.refusal_count; ++i) {
        if (i)
            reasons += ',';
        reasons += quote(assessed.refusals[i]);
    }
    reasons += ']';
    const auto admission = assessed.admission == application::TestToneAdmission::Ready ? "ready"
                           : assessed.admission == application::TestToneAdmission::RequiresRestart
                               ? "requires_restart"
                               : "refused";
    const auto clock = service_.clock_snapshot();
    response.body =
        "{\"schema\":\"test-tone-review\",\"target\":" + application::target(device_, boot) +
        ",\"assessment_revision\":" + quote(revision()) + ",\"admission\":" + quote(admission) +
        ",\"reasons\":" + reasons +
        ",\"minimum_duration_ms\":" + std::to_string(assessed.minimum_duration_ms) +
        ",\"maximum_duration_ms\":" + std::to_string(assessed.maximum_duration_ms) +
        ",\"proposed_drive_ma\":" + std::to_string(proposal.proposed_drive_ma) +
        ",\"saved_drive_ma\":" + saved_drive + ",\"boot_drive_ma\":" + std::to_string(boot_drive) +
        ",\"requires_restart\":" +
        boolean(scheduler_.reboot_required() || proposal.proposed_drive_ma != boot_drive) +
        ",\"rf_pin\":" + (pins.rf ? std::to_string(*pins.rf) : "null") +
        ",\"engine\":" + quote(engine_name(pins.engine)) +
        synthesis_identity(boot_synthesis, service_.config().capability_engine) +
        ",\"profile_id\":" + (matched_profile ? quote(hardware::si5351_support::id) : "null") +
        ",\"realization\":" + realization(assessed, synthesis) +
        ",\"clock_assumptions\":{\"state\":" +
        quote(clock.state == execution::ClockState::Synchronized ? "synchronized"
              : clock.state == execution::ClockState::Holdover   ? "holdover"
                                                           : "unsynchronized") +
        ",\"observed_monotonic_ns\":" + number(clock.monotonic_now_ns) +
        ",\"uncertainty_ns\":" + number(clock.uncertainty_ns) +
        ",\"maximum_uncertainty_ns\":" + number(service_.config().maximum_arm_uncertainty_ns) +
        "}" + ",\"prospective_utc_ns\":" + optional_number(assessed.launch_utc_ns) +
        ",\"clock_error\":" +
        (assessed.clock_error == execution::ErrorCode::None ? "null"
                                                      : execution::error_json(assessed.clock_error)) +
        "}";
    response.etag = revision();
    return response;
}
} // namespace wsprrypico::network
