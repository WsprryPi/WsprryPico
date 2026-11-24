// SPDX-License-Identifier: MIT
#include "application/resources.hpp"
#include "network/api.hpp"
#include "network/control_contract.hpp"
#include "network/test_tone_query.hpp"
#include "rf/waveform.hpp"
#include "wtp/memory_budget.hpp"
#include "wtp/observation.hpp"

#include <charconv>
#include <climits>

namespace wsprrypico::network {
namespace {
using wtp::json::quote;
std::string number(std::uint64_t value) {
    return quote(std::to_string(value));
}
std::string optional_number(std::optional<std::uint64_t> value) {
    return value ? number(*value) : "null";
}
std::string boolean(bool value) {
    return value ? "true" : "false";
}
bool integer(wtp::json::Value value, std::uint64_t& out) {
    if (value.raw.empty() || value.raw.size() > 20)
        return false;
    std::string raw(value.raw);
    if ((raw.size() > 1 && raw[0] == '0') || raw.find_first_not_of("0123456789") != raw.npos)
        return false;
    const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), out);
    return parsed.ec == std::errc{} && parsed.ptr == raw.data() + raw.size();
}
std::string realization(const application::TestToneReview& r) {
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
           ",\"nominal_sample_hz\":" + std::to_string(rf::sample_rate) +
           ",\"quantization_bound_nhz\":" +
           (f.programmed_nhz ? number(r.quantization_bound_nhz) : "null") +
           ",\"correction\":" + correction + "}";
}
std::string record_json(const application::TestToneRecord& r) {
    const char* phase = r.terminal                       ? "terminal"
                        : r.state == wtp::State::Running ? "running"
                                                         : "accepted";
    const char* outcome = r.state == wtp::State::Complete  ? "completed"
                          : r.state == wtp::State::Aborted ? "stopped"
                          : r.state == wtp::State::Missed  ? "missed"
                                                           : "failed";
    const auto& pad = r.pad;
    const bool verified_pad = pad.epoch && pad.rf_pin == int(r.rf_pin) &&
                              pad.drive_ma == int(r.proposal.proposed_drive_ma);
    return "{\"request_id\":" + quote(r.request_id) + ",\"job_id\":" + quote(r.job_id) +
           ",\"phase\":" + quote(phase) + ",\"native_state\":" + quote(wtp::state_name(r.state)) +
           ",\"outcome\":" + (r.terminal ? quote(outcome) : "null") +
           ",\"carrier_hz\":" + std::to_string(r.proposal.carrier_hz) +
           ",\"duration_ms\":" + std::to_string(r.proposal.duration_ms) +
           ",\"engine\":\"pio-dma-gp2\",\"rf_pin\":" + std::to_string(r.rf_pin) +
           ",\"boot_drive_ma\":" + std::to_string(r.proposal.proposed_drive_ma) +
           ",\"admission_revision\":" + quote(r.admission_revision) +
           ",\"control_revision\":" + quote(r.control_revision) +
           ",\"accepted_monotonic_ns\":" + number(r.accepted_ns) +
           ",\"scheduled_utc_ns\":" + optional_number(r.assessment.launch_utc_ns) +
           ",\"scheduled_monotonic_ns\":" + optional_number(r.assessment.launch_monotonic_ns) +
           ",\"launch_monotonic_ns\":" + optional_number(r.launch_ns) +
           ",\"ended_monotonic_ns\":" + (r.terminal ? number(r.ended_ns) : "null") +
           ",\"realization\":" + realization(r.assessment) +
           ",\"pad_readback\":{\"epoch\":" + (pad.epoch ? number(pad.epoch) : "null") +
           ",\"observed_monotonic_ns\":" +
           (pad.drive_ma != -1 ? number(pad.observed_monotonic_ns) : "null") +
           ",\"rf_pin\":" + (pad.rf_pin >= 0 ? std::to_string(pad.rf_pin) : "null") +
           ",\"drive_ma\":" + (pad.drive_ma > 0 ? std::to_string(pad.drive_ma) : "null") +
           ",\"stage\":" +
           quote(verified_pad         ? "verified"
                 : pad.drive_ma != -1 ? "failed"
                                      : "unavailable") +
           "},\"output_inactive_confirmed\":" + boolean(r.output_inactive_confirmed) +
           ",\"recovery_required\":" + boolean(r.recovery_required) + ",\"native_error\":" +
           (r.error == wtp::ErrorCode::None ? "null" : wtp::error_json(r.error)) + "}";
}
} // namespace
std::string BrowserApi::test_tone_capability() const {
    auto descriptor = std::string(control_descriptor("test_tone"));
    descriptor.pop_back();
    const auto limit = std::min({application::test_tone_maximum_duration_ms,
                                 service_.config().max_job_duration_ns / 1'000'000,
                                 rf::max_duration_ns / 1'000'000});
    return descriptor + ",\"available\":" +
           boolean(test_tone_.supported() && service_.config().capability_engine == "pio-dma-gp2") +
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
    const auto saved_drive = saved_config ? std::to_string(saved_config->gpio_drive_ma) : "null";
    if (!test_tone_.supported())
        return http_error(409, "test_tone_unavailable");
    if (!wtp::memory_admitted(16'384))
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
            if (result.native_error != wtp::ErrorCode::None)
                failure.body = "{\"error\":" + quote(result.error) +
                               ",\"native_error\":" + wtp::error_json(result.native_error) + "}";
            return failure;
        }
        const auto current = service_.activity();
        response.status = result.record ? code : 404;
        response.body =
            "{\"schema\":\"test-tone-status\",\"target\":" + application::target(device_, boot) +
            ",\"receipt\":" + quote(result.record ? "known" : "receipt_unavailable") +
            ",\"job\":" + (result.record ? record_json(*result.record) : "null") +
            ",\"observation_monotonic_ns\":" + number(service_.clock_snapshot().monotonic_now_ns) +
            ",\"current\":{\"saved_drive_ma\":" + saved_drive +
            ",\"boot_drive_ma\":" + std::to_string(scheduler_.active_gpio_drive_ma()) +
            ",\"output_active\":" + boolean(current.output_active) +
            ",\"owned\":" + boolean(current.owned) +
            ",\"native_state\":" + quote(wtp::state_name(current.state)) + "}}";
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
    const auto root = wtp::json::parse(request.body_view());
    if (!root || root->type() != '{')
        return http_error(400, "invalid_test_tone_request");
    using wtp::json::fields;
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
        if (!wtp::json::identifier(*root->get("job_id")))
            return http_error(400, "invalid_job_id");
        return status_response(
            test_tone_.stop(authority, root->get("job_id")->string(), request.header("if-match")),
            200);
    }
    const auto tone = *root->get("tone");
    const auto drive_key = review ? "proposed_drive_ma" : "expected_drive_ma";
    if (!fields(tone, {"carrier_hz", "duration_ms", drive_key}))
        return http_error(400, "invalid_tone");
    application::TestToneProposal proposal;
    std::uint64_t drive;
    if (!integer(*tone.get("carrier_hz"), proposal.carrier_hz) ||
        !integer(*tone.get("duration_ms"), proposal.duration_ms) ||
        !integer(*tone.get(drive_key), drive) || drive > UINT_MAX)
        return http_error(400, "invalid_tone_integer");
    proposal.proposed_drive_ma = static_cast<unsigned>(drive);
    if (start) {
        if (!wtp::json::identifier(*root->get("request_id")))
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
    const auto& pins = scheduler_.active_pins();
    const auto clock = service_.clock_snapshot();
    response.body =
        "{\"schema\":\"test-tone-review\",\"target\":" + application::target(device_, boot) +
        ",\"assessment_revision\":" + quote(revision()) + ",\"admission\":" + quote(admission) +
        ",\"reasons\":" + reasons +
        ",\"maximum_duration_ms\":" + std::to_string(assessed.maximum_duration_ms) +
        ",\"proposed_drive_ma\":" + std::to_string(proposal.proposed_drive_ma) +
        ",\"saved_drive_ma\":" + saved_drive +
        ",\"boot_drive_ma\":" + std::to_string(scheduler_.active_gpio_drive_ma()) +
        ",\"requires_restart\":" +
        boolean(scheduler_.reboot_required() ||
                proposal.proposed_drive_ma != scheduler_.active_gpio_drive_ma()) +
        ",\"rf_pin\":" + (pins.rf ? std::to_string(*pins.rf) : "null") +
        ",\"engine\":\"pio-dma-gp2\",\"realization\":" + realization(assessed) +
        ",\"clock_assumptions\":{\"state\":" +
        quote(clock.state == wtp::ClockState::Synchronized ? "synchronized"
              : clock.state == wtp::ClockState::Holdover   ? "holdover"
                                                           : "unsynchronized") +
        ",\"observed_monotonic_ns\":" + number(clock.monotonic_now_ns) +
        ",\"uncertainty_ns\":" + number(clock.uncertainty_ns) +
        ",\"maximum_uncertainty_ns\":" + number(service_.config().maximum_arm_uncertainty_ns) +
        "}" + ",\"prospective_utc_ns\":" + optional_number(assessed.launch_utc_ns) +
        ",\"clock_error\":" +
        (assessed.clock_error == wtp::ErrorCode::None ? "null"
                                                      : wtp::error_json(assessed.clock_error)) +
        "}";
    response.etag = revision();
    return response;
}
} // namespace wsprrypico::network
