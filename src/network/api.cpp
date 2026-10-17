#include "network/api.hpp"

#include "application/config_update.hpp"
#include "application/resources.hpp"
#include "encoding/wspr.hpp"
#include "hardware/pins.hpp"
#include "network/assets.hpp"
#include "network/identity.hpp"
#include "network/message_job.hpp"
#include "rf/calibration.hpp"
#include "wtp/codec.hpp"
#include "wtp/frame_parser.hpp"
#include "wtp/memory_budget.hpp"

namespace wsprrypico::network {
using namespace wtp;
namespace {
std::string hex(std::span<const std::uint8_t> bytes) {
    std::string result;
    for (auto b : bytes) {
        result += "0123456789abcdef"[b >> 4];
        result += "0123456789abcdef"[b & 15];
    }
    return result;
}
HttpResponse ok(std::string body) {
    return {200, std::move(body), "application/json", {}};
}
void append(std::string& output, InputView input) {
    for (std::size_t offset = 0; offset < input.size();) {
        const auto part = input.at(offset);
        output.append(reinterpret_cast<const char*>(part.data()), part.size());
        offset += part.size();
    }
}
} // namespace
std::optional<standalone::Config> BrowserApi::effective_config() const {
    if (!store_.healthy())
        return {};
    if (consumer_runtime_ && consumer_runtime_->consumer_profile()) {
        // A USB profile can save a name/network before a complete runnable
        // station exists. Do not manufacture an empty station or generation 0.
        if (consumer_runtime_->consumer_profile()->usb_managed && !store_.config())
            return {};
        return consumer_runtime_->overlay(store_.config().value_or(standalone::Config{}));
    }
    return store_.config();
}
std::string BrowserApi::revision() const {
    const auto config = effective_config();
    const auto data =
        device_ + ":" + service_.status().boot_id + ":" + std::to_string(network_revision_) + ":" +
        std::to_string(store_.config_sequence()) + ":" +
        (config ? standalone::serialize_config(*config) : "null") +
        (hostname_settings_ ? hostname_settings_->revision_context() : "") +
        (local_settings_ ? local_settings_->revision_context() : "") +
        (progress_ ? ":progress:" + std::to_string(progress_->sequence()) + ":profile:" +
                         std::to_string(consumer_runtime_ ? consumer_runtime_->generation() : 0)
                   : "") +
        (consumer_runtime_ && consumer_runtime_->consumer_profile()
             ? ":consumer:" + std::to_string(consumer_runtime_->generation())
             : "");
    const auto digest =
        sha256(std::span(reinterpret_cast<const std::uint8_t*>(data.data()), data.size()));
    return '"' + hex(digest) + '"';
}
std::string BrowserApi::saved_station_json() const {
    const auto saved = effective_config();
    return saved && encoding::valid_station_details(saved->callsign, saved->locator,
                                                    saved->power_dbm)
               ? application::station(*saved)
               : "null";
}
HttpResponse BrowserApi::progress_readback(bool station_only, bool drive, bool amplifier) const {
    if (!progress_)
        return http_error(404, "not_found");
    if (!store_.healthy() || !progress_->healthy())
        return http_error(503, "storage_fault");
    if (!station_only && !amplifier && progress_->amplifier_view_required())
        return http_error(409, "amplifier_view_required");
    const auto applied = station_only && consumer_runtime_ && !consumer_runtime_->consumer_profile()
                             ? std::optional<standalone::Config>{}
                             : effective_config();
    const auto candidate = progress_->candidate(applied, "all", drive, amplifier);
    const auto station = progress_->station_candidate(applied);
    // Keep the backing scheduler status string alive while reading its views.
    const auto status_text = scheduler_.status();
    const auto status = json::parse(status_text);
    auto result =
        ok("{\"schema\":" +
           json::quote(amplifier ? "transmitter-progress/3"
                       : drive   ? "transmitter-progress/2"
                                 : "transmitter-progress/1") +
           ",\"target\":" + application::target(device_, service_.status().boot_id) +
           ",\"draft_revision\":" + json::quote(std::to_string(progress_->sequence())) +
           ",\"config_revision\":" + json::quote(std::to_string(store_.config_sequence())) +
           ",\"profile_revision\":" +
           json::quote(std::to_string(consumer_runtime_ ? consumer_runtime_->generation() : 0)) +
           ",\"fields\":" + progress_->fields(true, station_only, drive, amplifier) +
           ",\"last_receipt\":" + (station_only ? std::string("null") : progress_->receipt()) +
           ",\"last_outcomes\":" + progress_->outcomes(station_only, drive) +
           ",\"applied_station\":" + (applied ? application::station(*applied) : "null") +
           ",\"station\":" + progress_->station_fields(applied) +
           ",\"station_complete\":" + (station ? "true" : "false") +
           ",\"complete\":" + (candidate ? "true" : "false") + ",\"apply_domains\":{\"station\":" +
           (progress_->candidate(applied, "station") ? "true" : "false") + ",\"network\":" +
           (progress_->candidate(applied, "network") ? "true" : "false") + ",\"radio\":" +
           (progress_->candidate(applied, "radio", drive, amplifier) ? "true" : "false") +
           (drive ? ",\"drive\":" +
                        std::string(progress_->candidate(applied, "drive", true) ? "true" : "false")
                  : "") +
           ",\"all\":" + (candidate ? "true}" : "false}") + ",\"wspr_plan\":" +
           (station ? application::wspr_plan(*station) : "null") + ",\"schedule_enabled\":" +
           (station_only ? std::string("null") : std::string(status->get("enabled")->raw)) +
           ",\"schedule_suspended\":" +
           (station_only ? std::string("null") : std::string(status->get("suspended")->raw)) +
           ",\"matches_applied\":" +
           (candidate && applied && *candidate == *applied &&
                    (!drive || progress_->drive_matches(applied->gpio_drive_ma))
                ? "true}"
                : "false}"));
    result.etag = revision();
    return result;
}
bool BrowserApi::progress_station_matches(std::string_view call, std::string_view locator,
                                          unsigned power) const {
    if (!progress_ || !store_.healthy())
        return false;
    const auto applied = consumer_runtime_ && !consumer_runtime_->consumer_profile()
                             ? std::optional<standalone::Config>{}
                             : effective_config();
    const auto station = progress_->station_candidate(applied);
    return station && station->callsign == call && station->locator == locator &&
           station->power_dbm == power;
}
HttpResponse BrowserApi::save_progress(const HttpRequest& r, bool station_only, bool drive,
                                       bool amplifier) {
    if (!progress_)
        return http_error(404, "not_found");
    if (r.body_view().size() > 2048)
        return http_error(413, "resource_body_too_large");
    if (!store_.healthy() || !progress_->healthy())
        return http_error(503, "storage_fault");
    if (!station_only && !amplifier && progress_->amplifier_view_required())
        return http_error(409, "amplifier_view_required");
    if (r.header("if-match").empty())
        return http_error(428, "revision_required");
    if (r.header("if-match") != revision())
        return http_error(412, "revision_conflict");
    if (!scheduler_.idle() || pending_transaction_)
        return http_error(409, "busy");
    const auto root = json::parse(r.body_view());
    if (!root || !json::fields(*root, {"schema", "target", "request_id", "fields"}) ||
        root->get("schema")->type() != '"' ||
        root->get("schema")->string() != (amplifier ? "transmitter-progress/3"
                                          : drive   ? "transmitter-progress/2"
                                                    : "transmitter-progress/1") ||
        !json::identifier(*root->get("request_id")) ||
        !json::fields(*root->get("target"), {"scope", "device_id", "boot_id"}))
        return http_error(400, "invalid_progress");
    const auto target = *root->get("target");
    for (const auto field : {"scope", "device_id", "boot_id"})
        if (target.get(field)->type() != '"')
            return http_error(400, "invalid_progress");
    if (target.get("scope")->string() != "member" || target.get("device_id")->string() != device_ ||
        target.get("boot_id")->string() != service_.status().boot_id)
        return http_error(409, "target_mismatch");
    auto fields = *root->get("fields");
    std::string normalized_pins;
    if (const auto pins = fields.get("pins"); pins && pins->raw != "null") {
        auto plan = hardware::parse_plan(std::string(pins->raw));
        // Pins/polarity form one atomic unit. Malformed amplifier data must
        // never advance a journal or save otherwise-valid sibling fields.
        if (!plan || !hardware::operational(*plan) ||
            (!amplifier &&
             (pins->get("amplifier_active_high") || hardware::requires_amplifier_view(*plan))))
            return http_error(400, "invalid_pin_plan");
        if (amplifier && !pins->get("amplifier_active_high")) {
            const auto previous_text = progress_->fields(false);
            const auto previous = json::parse(previous_text);
            const auto draft = previous->get("pins");
            if (draft && draft->raw != "null")
                plan->amplifier_active_high =
                    hardware::parse_plan(std::string(draft->raw))->amplifier_active_high;
            else if (const auto applied = effective_config())
                plan->amplifier_active_high = applied->pins.amplifier_active_high;
            normalized_pins = std::string(fields.raw);
            normalized_pins.replace(pins->raw.offset() - fields.raw.offset(), pins->raw.size(),
                                    hardware::serialize_plan(*plan, true));
            fields = *json::parse(normalized_pins);
        }
    }
    if (const auto value = fields.get("gpio_drive_ma");
        value && (!drive || !standalone::valid_gpio_drive_token(*value)))
        return http_error(400, "invalid_gpio_drive");
    if (!json::fields(
            fields, {},
            station_only
                ? std::initializer_list<std::string_view>{"callsign", "locator", "power_dbm"}
                : std::initializer_list<std::string_view>{"callsign", "locator", "power_dbm",
                                                          "enabled", "schedules", "expires_utc_s",
                                                          "pins", "frequency_policy", "wifi",
                                                          "ntp_ipv4", "gpio_drive_ma"}) ||
        json::fields(fields, {}))
        return http_error(400, "invalid_progress");
    const auto receipt_text = std::string(r.body_view());
    const auto digest = sha256(
        std::span(reinterpret_cast<const std::uint8_t*>(receipt_text.data()), receipt_text.size()));
    std::string resolved;
    if (!station_only) {
        const auto wifi = fields.get("wifi");
        const auto applied = effective_config();
        const auto draft_text = progress_->fields(false);
        const auto draft = json::parse(draft_text);
        const auto saved_wifi = draft->get("wifi");
        const auto password = saved_wifi && saved_wifi->raw != "null"
                                  ? std::optional{saved_wifi->get("password")->string()}
                              : !saved_wifi && applied ? std::optional{applied->password}
                                                       : std::nullopt;
        if (wifi && password && json::fields(*wifi, {"ssid", "password"}) &&
            wifi->get("password")->raw == "null") {
            resolved = std::string(fields.raw);
            const auto secret = wifi->get("password")->raw;
            resolved.replace(secret.offset() - fields.raw.offset(), secret.size(),
                             json::quote(*password));
            const auto parsed = json::parse(resolved);
            if (!parsed)
                return http_error(400, "invalid_progress");
            fields = *parsed;
        }
    }
    const auto outcomes = progress_->save(fields, hex(digest));
    if (!outcomes)
        return http_error(progress_->healthy() ? 413 : 503,
                          progress_->healthy() ? "progress_too_large" : "storage_fault");
    auto result = progress_readback(station_only, drive, amplifier);
    if (result.status != 200)
        return result;
    result.body.pop_back();
    result.body += ",\"outcomes\":" + *outcomes +
                   ",\"request_id\":" + std::string(root->get("request_id")->raw) + '}';
    return result;
}
HttpResponse BrowserApi::config(bool drive, bool amplifier) const {
    std::string body = "null";
    if (const auto config = effective_config()) {
        auto redacted = *config;
        if (!amplifier)
            redacted.pins.amplifier_active_high =
                true; // Closed legacy projection, no polarity authority.
        redacted.password.clear();
        redacted.manual_correction_ppb = 0;
        redacted.ntp_rf_calibration = false;
        redacted.wspr_base_frequency_hz.reset();
        if (!drive)
            redacted.gpio_drive_ma = 4;
        body = standalone::serialize_config(redacted, amplifier);
        if (drive && redacted.gpio_drive_ma == 4) {
            body.pop_back();
            body += ",\"gpio_drive_ma\":4}";
        }
        const auto pos = body.find("\"password\":\"\"");
        body.replace(pos, 13, "\"password\":null");
    }
    auto result = ok("{\"config\":" + body + "}");
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::station_config(bool extended) const {
    const auto config = effective_config();
    if (!extended && config) {
        const auto plan = encoding::wspr_plan(config->callsign, config->locator, config->power_dbm);
        if (config->callsign.starts_with('<') ||
            (plan && plan->frames[0].type != encoding::WsprType::Type1))
            return http_error(409, "unsupported_station_encoding");
    }
    const bool saved = config.has_value();
    auto result = ok("{\"schema\":" +
                     json::quote(extended ? "transmitter-station/2" : application::station_schema) +
                     ",\"target\":" + application::target(device_, service_.status().boot_id) +
                     ",\"station\":" + (saved ? application::station(*config) : "null") +
                     ",\"saved_generation\":" +
                     (saved ? json::quote(std::to_string(store_.config_sequence())) : "null") +
                     ",\"storage_healthy\":" + (store_.healthy() ? "true}" : "false}"));
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::standalone_frequency() const {
    const auto config = effective_config();
    auto result = ok(
        "{\"schema\":\"transmitter-standalone-frequency/1\",\"target\":" +
        application::target(device_, service_.status().boot_id) + ",\"frequency_hz\":" +
        (config && config->wspr_base_frequency_hz ? std::to_string(*config->wspr_base_frequency_hz)
                                                  : "null") +
        ",\"configured\":" + (config && config->wspr_base_frequency_hz ? "true" : "false") +
        ",\"allowed\":" +
        (config && standalone::wspr_frequency_allowed(*config,
                                                      service_.config().minimum_frequency_nhz,
                                                      service_.config().maximum_frequency_nhz)
             ? "true"
             : "false") +
        ",\"storage_healthy\":" + (store_.healthy() ? "true" : "false") + "}");
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::rf_calibration() const {
    const auto config = effective_config();
    auto result = ok(
        "{\"schema\":\"transmitter-rf-calibration/1\",\"target\":" +
        application::target(device_, service_.status().boot_id) + ",\"saved\":" +
        (config
             ? "{\"manual_ppm\":" + json::quote(rf::format_ppm(config->manual_correction_ppb)) +
                   ",\"mode\":" + json::quote(config->ntp_rf_calibration ? "ntp" : "manual") + "}"
             : "null") +
        ",\"selection\":" + service_.calibration_status() +
        ",\"execution_engine\":" + json::quote(service_.config().capability_engine) +
        ",\"storage_healthy\":" + (store_.healthy() ? "true" : "false") + "}");
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::gpio_drive() const {
    const auto config = effective_config();
    const int pad = drive_observer_ ? drive_observer_() : -1;
    auto result =
        ok("{\"schema\":\"transmitter-gpio-drive/1\",\"target\":" +
           application::target(device_, service_.status().boot_id) + ",\"saved\":" +
           (config ? std::to_string(config->gpio_drive_ma) : "null") + ",\"boot_active\":" +
           (store_.healthy() ? std::to_string(scheduler_.active_gpio_drive_ma()) : "null") +
           ",\"pad_readback\":" + (pad > 0 ? std::to_string(pad) : "null") +
           ",\"pending_restart\":" + (scheduler_.hardware_restart_required() ? "true" : "false") +
           ",\"application_error\":" +
           (scheduler_.hardware_application_failed() ? "\"output_disable_failed\""
            : pad == -2                              ? "\"pad_application_failed\""
                                                     : "null") +
           ",\"rf_gp\":" +
           (scheduler_.active_pins().rf ? std::to_string(*scheduler_.active_pins().rf) : "null") +
           ",\"execution_engine\":" + json::quote(service_.config().capability_engine) +
           ",\"storage_healthy\":" + (store_.healthy() ? "true}" : "false}"));
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::hardware_config(bool drive, bool amplifier) const {
    const bool saved = store_.healthy() && store_.config().has_value();
    auto active_plan = scheduler_.active_pins();
    auto saved_plan = saved ? store_.config()->pins : hardware::PinPlan{};
    const bool legacy_unavailable = !amplifier && (hardware::requires_amplifier_view(active_plan) ||
                                                   hardware::requires_amplifier_view(saved_plan));
    if (legacy_unavailable)
        return http_error(409, "amplifier_view_required");
    if (!amplifier) {
        active_plan.amplifier_active_high = true;
        saved_plan.amplifier_active_high = true;
    }
    const auto active = hardware::serialize_plan(active_plan, amplifier);
    const auto boot = service_.status().boot_id;
    const auto data = device_ + ':' + boot + ":hardware:" + active +
                      (drive ? ":drive:" + std::to_string(scheduler_.active_gpio_drive_ma()) : "");
    const auto digest =
        sha256(std::span(reinterpret_cast<const std::uint8_t*>(data.data()), data.size()));
    auto result =
        ok("{\"schema\":" +
           json::quote(amplifier ? "transmitter-hardware/3"
                       : drive   ? "transmitter-hardware/2"
                                 : application::hardware_schema) +
           ",\"target\":" + application::target(device_, boot) +
           ",\"saved\":" + (saved ? hardware::serialize_plan(saved_plan, amplifier) : "null") +
           ",\"saved_generation\":" +
           (saved ? json::quote(std::to_string(store_.config_sequence())) : "null") +
           ",\"active\":" + (scheduler_.boot_configured() ? active : "null") +
           ",\"active_revision\":" +
           (scheduler_.boot_configured() ? json::quote(hex(digest)) : "null") +
           ",\"pending_restart\":" + (scheduler_.hardware_restart_required() ? "true" : "false") +
           ",\"application_error\":" +
           (scheduler_.hardware_application_failed() ? "\"output_disable_failed\"" : "null") +
           ",\"execution_engine\":" + json::quote(service_.config().capability_engine) +
           ",\"storage_healthy\":" + (store_.healthy() ? "true}" : "false}"));
    if (drive) {
        result.body.pop_back();
        result.body += ",\"gpio_drive\":" + gpio_drive().body + "}";
    }
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::application_config(bool extended, bool usb_management, bool drive,
                                            bool amplifier) const {
    auto station = station_config(extended);
    if (station.status != 200)
        return station;
    auto hardware = hardware_config(drive, amplifier);
    if (hardware.status != 200)
        return hardware;
    const auto status = scheduler_.status();
    const auto value = json::parse(status);
    if (!value)
        return http_error(503, "resource_exhausted");
    std::string recurrence = "{\"authority\":\"member\"";
    for (const auto field : {"enabled", "suspended", "schedules"})
        recurrence += ',' + json::quote(field) + ':' + std::string(value->get(field)->raw);
    // Legacy application resources require a decimal string. Zero means
    // unconfigured; the independent frequency resource reports explicit null.
    recurrence += ",\"schedule_base_frequency_nhz\":" +
                  (value->get("schedule_base_frequency_nhz")->raw == "null"
                       ? std::string("\"0\"")
                       : std::string(value->get("schedule_base_frequency_nhz")->raw));
    recurrence +=
        ",\"expires_utc_s\":" + json::quote(std::string(value->get("expires_utc_s")->raw));
    recurrence += '}';
    auto caps = application::capabilities(usb_management);
    if (amplifier) {
        const auto at = caps.find("\"amplifier\",");
        caps.erase(at, std::string_view("\"amplifier\",").size());
    }
    if (extended) {
        const auto at = caps.find("wspr_type1\"");
        caps.replace(at, 11, "wspr_type123_auto\"");
    }
    auto result = ok(
        "{\"schema\":" +
        json::quote(amplifier  ? "transmitter-application/4"
                    : drive    ? "transmitter-application/3"
                    : extended ? "transmitter-application/2"
                               : application::application_schema) +
        ",\"target\":" + application::target(device_, service_.status().boot_id) +
        ",\"station\":" + station.body + ",\"hardware\":" + hardware.body +
        ",\"recurrence\":" + recurrence + ",\"capabilities\":" + caps +
        (extended ? ",\"wspr_plan\":" +
                        (effective_config() ? application::wspr_plan(*effective_config()) : "null")
                  : "") +
        ",\"reboot_required\":" + (scheduler_.reboot_required() ? "true}" : "false}"));
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::job(const HttpRequest& r, std::string_view principal) {
    auto body = json::parse(r.body_view());
    if (!body || !json::fields(*body, {"session_id", "request_id", "operation", "body"}))
        return http_error(400, "invalid_job_request");
    auto operation = body->get("operation")->string();
    const auto abort_prefix = std::string_view("/api/v1/jobs/");
    if (r.path != "/api/v1/jobs") {
        auto id = std::string_view(r.path).substr(abort_prefix.size());
        if (!id.ends_with("/abort"))
            return http_error(404, "not_found");
        id.remove_suffix(6);
        auto job_id = body->get("body")->get("job_id");
        if (operation != "ABORT" || !job_id || job_id->string() != id)
            return http_error(400, "job_id_mismatch");
    }
    if (operation != "HELLO" && operation != "CLAIM" && operation != "RENEW" &&
        operation != "RELEASE" && operation != "LOAD" && operation != "LOAD_MESSAGE" &&
        operation != "ARM" && operation != "ABORT")
        return http_error(400, "unsupported_operation");
    const bool message_job = operation == "LOAD_MESSAGE";
    // Browser schema is versioned by the URL. WTP envelope/codec stays internal.
    std::string payload;
    payload.reserve(body->get("session_id")->raw.size() + body->get("request_id")->raw.size() +
                    body->get("operation")->raw.size() + body->get("body")->raw.size() + 128);
    // Append paged views into the reserved destination.  A chained string
    // expression builds a geometrically grown full-size temporary alongside
    // the HTTP body and destination; fragmented target heaps can reject that
    // unnecessary contiguous allocation even when the admission total passes.
    payload += "{\"type\":\"request\",\"protocol\":\"WTP/1\",\"session_id\":";
    append(payload, body->get("session_id")->raw);
    payload += ",\"request_id\":";
    append(payload, body->get("request_id")->raw);
    payload += ",\"op\":";
    if (message_job)
        payload += "\"PING\"";
    else
        append(payload, body->get("operation")->raw);
    payload += ",\"body\":";
    if (message_job)
        payload += "{}";
    else
        append(payload, body->get("body")->raw);
    payload += '}';
    if (payload.size() > kMaximumPayloadBytes)
        return http_error(413, "job_too_large");
    auto root = json::parse(payload);
    if (!root)
        return http_error(400, "invalid_job_request");
    auto request = decode_request(
        *root, principal,
        std::span(reinterpret_cast<const std::uint8_t*>(payload.data()), payload.size()));
    service_.poll();
    if (!request)
        return http_error(400, "invalid_job_request");
    if (message_job) {
        const auto message = decode_message_job(*body->get("body"));
        if (!message)
            return http_error(400, "invalid_message_job");
        const auto response_for = [&](const encoding::MorseResult& result) {
            auto response = http_error(result.error == "resource_exhausted" ? 503 : 400,
                                       std::string(result.error));
            response.body.pop_back();
            response.body +=
                ",\"calculated_duration_ns\":" +
                json::quote(std::to_string(result.calculated_duration_ns)) +
                ",\"max_job_duration_ns\":" +
                json::quote(std::to_string(std::min(service_.config().max_job_duration_ns,
                                                    encoding::max_message_duration_ns))) +
                ",\"calculated_events\":" + std::to_string(result.calculated_events) +
                ",\"max_events\":" +
                std::to_string(std::min<std::size_t>(service_.config().max_events, 512)) + "}";
            return response;
        };
        const auto measured = encoding::measure_message(*message, service_.config().max_events,
                                                        service_.config().max_job_duration_ns);
        if (!measured.error.empty())
            return response_for(measured);
        const auto event_pages =
            (measured.calculated_events + EventList::page_events - 1) / EventList::page_events;
        const auto event_bytes = event_pages * EventList::page_events * sizeof(RfEvent);
        if (!memory_admitted(event_bytes + 16384))
            return http_error(503, "resource_exhausted");
        auto compiled = encoding::compile_message(*message, service_.config().max_events,
                                                  service_.config().max_job_duration_ns);
        if (!compiled.job)
            return response_for(compiled);
        request->operation = "LOAD";
        request->body = std::move(*compiled.job);
        // Replay identity binds the complete original compact browser request,
        // including operation, message, timing and repeat inputs.
        Sha256 digest;
        const auto original = r.body_view();
        for (std::size_t offset = 0; offset < original.size();) {
            const auto part = original.at(offset);
            digest.update(part);
            offset += part.size();
        }
        request->payload_digest = digest.finish();
    }
    // All decoded fields own their storage; the internal envelope need not
    // coexist with RF preparation and a maximum adjustment response.
    root.reset();
    std::string{}.swap(payload);
    auto response = service_.handle(std::move(*request));
    request->body = std::monostate{};
    if (response.ok && request->operation == "LOAD") {
        auto encoded = encode_load_response_buffer(*request, response, true);
        if (encoded.empty())
            return http_error(503, "resource_exhausted");
        return {200, {}, "application/json", {}, std::move(encoded)};
    }

    auto encoded = encode_response(*request, response, service_.config(), device_, firmware_);
    const auto result = json::parse(encoded);
    const auto value = result->get(response.ok ? "body" : "error")->raw;
    const auto offset = value.offset();
    const auto length = value.size();
    const auto prefix = "{\"ok\":" + std::string(response.ok ? "true" : "false") +
                        ",\"request_id\":" + json::quote(request->request_id) +
                        (response.ok ? ",\"result\":" : ",\"error\":");
    // The browser prefix is shorter than the WTP envelope. Reuse its storage
    // rather than retaining several full adjustment-response string copies.
    encoded.resize(offset + length);
    encoded.replace(0, offset, prefix);
    encoded += '}';
    return {response.ok ? 200U : 409U, std::move(encoded), "application/json", {}};
}
HttpResponse BrowserApi::handle(const HttpRequest& r, std::string_view principal,
                                std::string_view authority, std::uint64_t transaction,
                                ManagementCarrier carrier) {
    // The parser already owns the complete HTTP body. Outer JSON whitespace
    // neither enters the internal envelope nor creates decoded fields; account
    // for additional working storage without reserving that padding twice.
    const auto body = r.body_view();
    const auto whitespace = [](char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; };
    std::size_t first = 0, last = body.size();
    while (first < last && whitespace(body[first]))
        ++first;
    while (last > first && whitespace(body[last - 1]))
        --last;
    const auto working_bytes = last - first;
    // Status is the browser's read-only authority view during RF. Its empty
    // request body and bounded response do not need the mutation/parser scratch
    // reserved by other endpoints. Keep the independent 32 KiB authority/RF
    // reserve unchanged while avoiding a false 503 under an established TLS
    // observer and a resident RF plan.
    const bool status_read =
        r.method == "GET" && (r.path == "/api/v1/status" || r.path == "/api/v1/jobs");
    const auto request_scratch = status_read ? 8192 : working_bytes * 2 + 16384;
    if (!wtp::memory_admitted(request_scratch))
        return http_error(503, "resource_exhausted");
    if (body.size() > max_http_body)
        return http_error(413, "body_too_large");
    if (principal.empty())
        return http_error(401, "authentication_required");
    const bool local_usb = carrier == ManagementCarrier::UsbPhysical;
    if (!local_usb) {
        const auto host = canonical_authority(r.header("host"));
        const auto current = canonical_authority(authority);
        const auto named = canonical_authority(hostname_authority_);
        const auto allowed = [&](const std::optional<std::string>& value) {
            return value && ((current && *value == *current) || (named && *value == *named));
        };
        if (!allowed(host))
            return http_error(403, "invalid_host");
        const bool mutation = r.method != "GET";
        const auto origin = r.header("origin");
        if (mutation || r.headers.contains("origin")) {
            const auto origin_authority = origin.starts_with("https://")
                                              ? canonical_authority(origin.substr(8))
                                              : std::nullopt;
            if (!allowed(origin_authority) || *origin_authority != *host)
                return http_error(403, "origin_or_content_type");
        }
        if (mutation && (r.header("x-wsprrypico-request") != "1" ||
                         r.header("content-type") != "application/json"))
            return http_error(403, "origin_or_content_type");
        if (!r.header("sec-fetch-site").empty() && r.header("sec-fetch-site") != "same-origin" &&
            r.header("sec-fetch-site") != "none")
            return http_error(403, "cross_site_request");
    }
    service_.poll();
    if (local_usb && local_settings_ && r.path == "/api/usb/v1/wifi") {
        if (!local_settings_->healthy())
            return http_error(503, "storage_fault");
        if (r.method == "GET") {
            auto result = ok(local_settings_->wifi_readback(service_.status().boot_id));
            result.etag = revision();
            return result;
        }
        if (r.method != "PUT" && r.method != "DELETE")
            return http_error(404, "not_found");
        if (r.body_view().size() > 1024)
            return http_error(413, "resource_body_too_large");
        if (r.header("if-match").empty())
            return http_error(428, "revision_required");
        if (r.header("if-match") != revision())
            return http_error(412, "revision_conflict");
        if (!scheduler_.idle() || pending_transaction_)
            return http_error(409, "busy");
        const auto root = json::parse(r.body_view());
        if (!root)
            return http_error(400, "invalid_json");
        const auto envelope = application::validate_envelope(*root, "transmitter-wifi/1", "wifi",
                                                             device_, service_.status().boot_id);
        if (envelope != application::Envelope::Valid)
            return http_error(envelope == application::Envelope::TargetMismatch ? 409 : 400,
                              envelope == application::Envelope::TargetMismatch
                                  ? "target_mismatch"
                                  : "invalid_resource");
        const auto wifi = *root->get("wifi");
        if ((r.method == "DELETE") != (wifi.raw == "null"))
            return http_error(400, "invalid_wifi");
        const auto error = local_settings_->wifi_save(wifi);
        if (!error.empty())
            return http_error(error == "invalid_wifi" || error == "password_required" ? 400 : 503,
                              error);
        scheduler_.require_network_restart();
        auto result = ok(local_settings_->wifi_readback(service_.status().boot_id));
        result.etag = revision();
        return result;
    }
    if (r.method == "GET") {
        if (auto asset = web_asset(r.path)) {
            // Generated assets live in flash for the process lifetime. Stream
            // the immutable bytes directly rather than copying a full page
            // into heap while WTP and RF state are resident. Preserve bounded
            // transport/header scratch plus the independent authority reserve.
            if (!memory_admitted(4096))
                return http_error(503, "resource_exhausted");
            return {200, {}, std::string(asset->type), {}, {}, asset->body, asset->parts};
        }
        if (r.path == "/api/v1/management")
            return ok(
                management_contract(management_, carrier, device_, service_.status().boot_id));
        if (r.path == "/api/v1/capabilities") {
            Request request;
            request.operation = "CAPS";
            Response response;
            response.ok = true;
            const auto caps =
                encode_response(request, response, service_.config(), device_, firmware_);
            auto value = json::parse(caps);
            return ok(
                "{\"ntp_observations\":{\"schema\":\"transmitter-ntp-observations/1\","
                "\"path\":\"/api/v1/ntp-observations\"},"
                "\"standalone_frequency\":{\"schema\":\"transmitter-standalone-frequency/1\","
                "\"path\":\"/api/v1/standalone-frequency\",\"method\":\"PUT\",\"units\":\"Hz\","
                "\"activation\":\"next_job\",\"default\":null},"
                "\"rf_calibration\":{\"schema\":\"transmitter-rf-calibration/1\","
                "\"path\":\"/api/v1/rf-calibration\",\"method\":\"PUT\","
                "\"units\":\"ppm\",\"precision\":3,\"minimum\":\"-100.000\","
                "\"maximum\":\"100.000\",\"default_mode\":\"manual\",\"activation\":\"next_"
                "preparation\"},"
                "\"amplifier_enable\":" +
                application::amplifier_capabilities(service_.config().capability_engine ==
                                                    "pio-dma-gp2") +
                ",\"gpio_drive\":" + application::gpio_drive_capabilities() +
                ",\"api_version\":1,\"wtp\":" + std::string(value->get("body")->raw) +
                ",\"message_jobs\":{\"operation\":\"LOAD_MESSAGE\",\"max_characters\":32,"
                "\"tail_ns\":\"1000\",\"max_repeat_count\":512,\"modes\":[\"qrss\",\"fskcw\","
                "\"dfcw\"]}"
                ",\"features\":{\"config\":true,\"schedules\":true,\"jobs\":true,\"network\":true,"
                "\"application\":true,\"station\":true,\"hardware\":true,\"consumer_setup_"
                "identity\":" +
                (consumer_runtime_ && consumer_runtime_->consumer_profile() ? "true" : "false") +
                ","
                "\"softap\":true,\"ble\":true,\"restart\":" +
                (restart_ ? "true" : "false") +
                "},\"application_resources_v2\":{\"schema\":\"transmitter-application/2\","
                "\"read\":\"/api/v1/application/2\",\"station\":\"/api/v1/station/2\","
                "\"config\":\"/api/v1/config/2\",\"update\":\"/api/v1/config/update/2\","
                "\"hardware\":\"/api/v1/hardware\",\"management_carrier\":" +
                json::quote(local_usb ? "usb_physical" : "authenticated_https") +
                "},"
                "\"application_resources\":{\"schema\":\"transmitter-application/1\","
                "\"read\":\"/api/v1/application\",\"station\":\"/api/v1/station\","
                "\"hardware\":\"/api/v1/hardware\",\"management_carrier\":" +
                json::quote(local_usb ? "usb_physical" : "authenticated_https") +
                "},"
                "\"configuration_updates\":" +
                application::config_update_capabilities() +
                ",\"management_carriers\":{\"schema\":" +
                json::quote(local_usb ? "transmitter-management/3" : "transmitter-management/2") +
                ",\"path\":\"/api/"
                "v1/management\"}"
                ",\"active_job_connections\":" +
                (active_job_connections_ ? "true" : "false") +
                (progress_ ? ",\"saved_progress\":{\"schema\":\"transmitter-progress/"
                             "1\",\"read\":\"/api/v1/progress\",\"save\":\"/api/v1/progress/"
                             "update\",\"apply\":\"/api/v1/progress/apply\",\"max_bytes\":2048}"
                           : "") +
                ",\"max_network_connections\":2,\"max_wtp_connections\":1,\"max_pending_"
                "connections\":1,\"max_handshakes\":1,\"max_body_bytes\":32768}");
        }
        if (r.path == "/api/v1/status" || r.path == "/api/v1/jobs")
            return ok(
                "{\"job\":" + status_json(service_.status()) +
                ",\"standalone\":" + scheduler_.status() + ",\"network\":" + network_.status() +
                ",\"transport\":" + (transport_ ? transport_(transport_context_) : "null") + "}");
        if (r.path == "/api/v1/ntp-observations") {
            const auto clock = service_.clock_snapshot();
            const auto active =
                time_arbiter_ ? time_arbiter_->status() : time::ControllerTimeStatus{};
            const char* sources[] = {"none", "sntp", "controller", "browser", "disagreement"};
            return ok(
                "{\"schema\":\"transmitter-ntp-observations/1\",\"target\":" +
                application::target(device_, service_.status().boot_id) +
                ",\"firmware\":" + json::quote(firmware_) +
                ",\"active_source\":" + json::quote(sources[static_cast<unsigned>(active.source)]) +
                ",\"source_disagreement\":" + (active.disagreement ? "true" : "false") +
                ",\"source_revision\":" + json::quote(source_revision_) +
                ",\"nominal_sample_hz\":" + std::to_string(nominal_sample_hz_) +
                ",\"image_hash_binding\":\"external_manifest\"" + ",\"clock_generation\":\"" +
                std::to_string(clock.model_generation) +
                "\",\"utc_rate_ppb\":" + std::to_string(clock.rate_ppb) + ",\"sync_age_ns\":\"" +
                std::to_string(clock.sync_age_ns) + "\",\"network\":" + network_.status() + "}");
        }
        if (r.path == "/api/v1/rf-calibration")
            return rf_calibration();
        if (r.path == "/api/v1/standalone-frequency")
            return standalone_frequency();
        if (r.path == "/api/v1/gpio-drive")
            return gpio_drive();
        if (r.path == "/api/v1/config/4")
            return config(true, true);
        if (r.path == "/api/v1/hardware/3")
            return hardware_config(true, true);
        if (r.path == "/api/v1/application/4")
            return application_config(true, local_usb, true, true);
        if (r.path == "/api/v1/progress/3")
            return progress_readback(false, true, true);
        if (r.path == "/api/v1/config/3")
            return config(true);
        if (r.path == "/api/v1/hardware/2")
            return hardware_config(true);
        if (r.path == "/api/v1/application/3")
            return application_config(true, local_usb, true);
        if (r.path == "/api/v1/progress/2")
            return progress_readback(false, true);
        if (r.path == "/api/v1/pins" || r.path == "/api/v1/pins/2") {
            const bool amplifier = r.path.ends_with("/2");
            auto active = scheduler_.active_pins();
            if (!amplifier && hardware::requires_amplifier_view(active))
                return http_error(409, "amplifier_view_required");
            return ok("{\"choices\":" + hardware::choices(amplifier) +
                      ",\"active\":" + hardware::serialize_plan(active, amplifier) + "}");
        }
        if (r.path == "/api/v1/config" || r.path == "/api/v1/config/2")
            return config();
        if (r.path == "/api/v1/progress")
            return progress_readback();
        if (r.path == "/api/v1/application")
            return application_config(false, local_usb);
        if (r.path == "/api/v1/application/2")
            return application_config(true, local_usb);
        if (r.path == "/api/v1/station")
            return station_config();
        if (r.path == "/api/v1/station/2")
            return station_config(true);
        if (r.path == "/api/v1/hardware")
            return hardware_config();
        if (r.path == "/api/v1/network") {
            auto result = ok(network_.status());
            result.etag = revision();
            return result;
        }
        if (r.path == "/api/v1/hostname" && hostname_settings_) {
            auto result = ok(hostname_settings_->readback(service_.status().boot_id, local_usb));
            result.etag = revision();
            return result;
        }
        if (r.path == "/api/v1/schedules") {
            const auto status = scheduler_.status();
            auto value = json::parse(status);
            auto result = ok("{\"schedules\":" + std::string(value->get("schedules")->raw) + "}");
            result.etag = revision();
            return result;
        }
        return http_error(404, "not_found");
    }
    // Side-effect-free authoritative WSPR planning, under normal carrier auth.
    if (r.path == "/api/v1/progress/update/3" && r.method == "POST")
        return save_progress(r, false, true, true);
    if (r.path == "/api/v1/progress/update/2" && r.method == "POST")
        return save_progress(r, false, true);
    if (r.path == "/api/v1/progress/update" && r.method == "POST")
        return save_progress(r);
    if ((r.path == "/api/v1/progress/apply" || r.path == "/api/v1/progress/apply/2" ||
         r.path == "/api/v1/progress/apply/3") &&
        r.method == "POST") {
        const bool amplifier = r.path.ends_with("/3");
        const bool drive = amplifier || r.path.ends_with("/2");
        if (!progress_)
            return http_error(404, "not_found");
        if (r.body_view().size() > 512)
            return http_error(413, "resource_body_too_large");
        if (r.header("if-match").empty())
            return http_error(428, "revision_required");
        if (r.header("if-match") != revision())
            return http_error(412, "revision_conflict");
        const auto root = json::parse(r.body_view());
        if (!root ||
            application::validate_envelope(*root,
                                           amplifier ? "transmitter-progress/3"
                                           : drive   ? "transmitter-progress/2"
                                                     : "transmitter-progress/1",
                                           "application", device_, service_.status().boot_id) !=
                application::Envelope::Valid ||
            !json::fields(*root->get("application"), {"draft_revision", "domain"}) ||
            root->get("application")->get("domain")->type() != '"' ||
            root->get("application")->get("draft_revision")->type() != '"' ||
            root->get("application")->get("draft_revision")->string() !=
                std::to_string(progress_->sequence()) ||
            !progress_->sequence())
            return http_error(400, "invalid_progress_application");
        const auto candidate = progress_->candidate(
            effective_config(), root->get("application")->get("domain")->string(), drive,
            amplifier);
        if (!candidate)
            return http_error(409, "incomplete_progress");
        const auto domain = root->get("application")->get("domain")->string();
        if (!amplifier && progress_->amplifier_view_required() &&
            (domain == "radio" || domain == "all"))
            return http_error(409, "amplifier_view_required");
        // Re-enter complete idle/profile/encoding/restart authority. The scheduler
        // and legacy CONFIG/PUT never read this draft or implicitly promote it.
        auto apply = r;
        apply.method = "PUT";
        apply.path = amplifier ? "/api/v1/config/4"
                     : drive   ? "/api/v1/config/3"
                               : "/api/v1/config/2";
        auto compatible = *candidate;
        // Progress has no calibration authority. The recursive legacy save
        // preserves these omitted settings through the central config merger.
        compatible.manual_correction_ppb = 0;
        compatible.ntp_rf_calibration = false;
        compatible.wspr_base_frequency_hz.reset();
        // Legacy apply has no drive authority. Omit the extension on its old
        // config route; ordinary candidate merge preserves the saved value and
        // the response retains its original closed configuration shape.
        if (!drive)
            compatible.gpio_drive_ma = 4;
        // Legacy progress has no amplifier authority. Project only those two
        // fields to the legacy pin shape; config_candidate restores them while
        // retaining intentional changes to the other pin roles.
        if (!amplifier) {
            auto encoded = standalone::serialize_config(compatible);
            auto parsed = json::parse(encoded);
            if (const auto pins = parsed->get("pins");
                pins && hardware::requires_amplifier_view(compatible.pins)) {
                auto legacy_pins = compatible.pins;
                legacy_pins.amplifier.reset();
                legacy_pins.amplifier_active_high = true;
                encoded.replace(pins->raw.offset(), pins->raw.size(),
                                hardware::serialize_plan(legacy_pins));
            }
            apply.body = std::move(encoded);
        } else
            apply.body = standalone::serialize_config(compatible, true);
        apply.buffered_body.reset();
        apply.selected_body = {};
        return handle(apply, principal, authority, transaction, carrier);
    }
    if (r.path == "/api/v1/wspr-plan" && r.method == "POST") {
        if (r.body_view().size() > application::max_update_bytes)
            return http_error(413, "resource_body_too_large");
        const auto value = json::parse(r.body_view());
        if (!value || !json::fields(*value, {"callsign", "locator", "power_dbm"}) ||
            value->get("callsign")->type() != '"' || value->get("locator")->type() != '"')
            return http_error(400, "invalid_station");
        const auto power_text = std::string(value->get("power_dbm")->raw);
        if (power_text.empty() || power_text.size() > 2 ||
            power_text.find_first_not_of("0123456789") != std::string::npos)
            return http_error(400, "invalid_station");
        const auto power = value->get("power_dbm")->integer();
        standalone::Config config;
        config.callsign = value->get("callsign")->string();
        config.locator = value->get("locator")->string();
        config.power_dbm = static_cast<unsigned>(power);
        if (!encoding::valid_station_details(config.callsign, config.locator, config.power_dbm))
            return http_error(400, "invalid_station");
        return ok(application::wspr_plan(config));
    }
    // Review candidates without changing Store, scheduler, engine or GPIO state.
    if ((r.path == "/api/v1/pins/validate" || r.path == "/api/v1/pins/validate/2") &&
        r.method == "POST") {
        const auto plan = hardware::parse_plan(std::string(r.body_view()));
        if (!plan)
            return http_error(400, "invalid_pin_plan");
        if (!r.path.ends_with("/2") && (hardware::requires_amplifier_view(*plan) ||
                                        json::parse(r.body_view())->get("amplifier_active_high")))
            return http_error(400, "unsupported_pin_adapter");
        return ok(hardware::describe(*plan));
    }
    if (r.method == "POST" && (r.path == "/api/v1/jobs" || r.path.starts_with("/api/v1/jobs/")))
        return job(r, principal);
    const bool restart = r.method == "POST" && r.path == "/api/v1/restart";
    const bool amplifier_config =
        r.path == "/api/v1/config/4" || r.path == "/api/v1/config/update/4";
    const bool drive_config =
        amplifier_config || r.path == "/api/v1/config/3" || r.path == "/api/v1/config/update/3";
    const bool calibration_resource = r.path == "/api/v1/rf-calibration";
    const bool frequency_resource = r.path == "/api/v1/standalone-frequency";
    const bool drive_resource = r.path == "/api/v1/gpio-drive";
    const bool extended_config =
        drive_config || r.path == "/api/v1/config/2" || r.path == "/api/v1/config/update/2";
    const bool config_update =
        r.method == "POST" &&
        (r.path == "/api/v1/config/update" || r.path == "/api/v1/config/update/2" ||
         r.path == "/api/v1/config/update/3" || r.path == "/api/v1/config/update/4");
    const bool extended_station = r.path == "/api/v1/station/2";
    const bool station_resource = r.path == "/api/v1/station" || extended_station;
    const bool amplifier_resource = r.path == "/api/v1/hardware/3";
    const bool hardware_resource = amplifier_resource || r.path == "/api/v1/hardware";
    const bool scoped_resource = station_resource || hardware_resource;
    const bool hostname = r.path == "/api/v1/hostname" && r.method == "PUT";
    if (!restart && !config_update && !hostname &&
        (r.method != "PUT" ||
         (r.path != "/api/v1/config" && r.path != "/api/v1/config/2" &&
          r.path != "/api/v1/config/3" && r.path != "/api/v1/config/4" && !drive_resource &&
          !calibration_resource && !frequency_resource && r.path != "/api/v1/schedules" &&
          r.path != "/api/v1/network" && !scoped_resource)))
        return http_error(404, "not_found");
    if ((scoped_resource || drive_resource || calibration_resource || frequency_resource) &&
        r.body_view().size() > application::max_update_bytes)
        return http_error(413, "resource_body_too_large");
    if (config_update && r.body_view().size() > application::max_config_update_bytes)
        return http_error(413, "resource_body_too_large");
    if ((r.path == "/api/v1/config" || r.path == "/api/v1/config/2" ||
         r.path == "/api/v1/config/3" || r.path == "/api/v1/config/4") &&
        r.body_view().size() > standalone::max_config_bytes)
        return http_error(400, "invalid_config");
    if (r.header("if-match").empty())
        return http_error(428, "revision_required");
    if (r.header("if-match") != revision())
        return http_error(412, "revision_conflict");
    if (!scheduler_.idle())
        return http_error(409, "busy");
    auto root = json::parse(r.body_view());
    if (!root)
        return http_error(400, "invalid_json");
    if (pending_transaction_)
        return http_error(409, "network_change_pending");
    if (hostname) {
        if (!hostname_settings_)
            return http_error(404, "not_found");
        if (r.body_view().size() > 512)
            return http_error(413, "resource_body_too_large");
        switch (application::validate_envelope(*root, "transmitter-hostname/1", "hostname", device_,
                                               service_.status().boot_id)) {
        case application::Envelope::Invalid:
            return http_error(400, "invalid_resource");
        case application::Envelope::UnsupportedSchema:
            return http_error(400, "unsupported_resource_schema");
        case application::Envelope::TargetMismatch:
            return http_error(409, "target_mismatch");
        case application::Envelope::Valid:
            break;
        }
        const auto field = root->get("hostname");
        if (field->type() != '"' && field->raw != "null")
            return http_error(400, "invalid_hostname");
        if (field->type() == '"' && !canonical_local_hostname(field->string()))
            return http_error(400, "invalid_hostname");
        if (local_usb && local_settings_) {
            const auto error = local_settings_->ensure_local_profile();
            if (!error.empty())
                return http_error(error == "credential_bound_deployment" ? 409 : 503, error);
        }
        const auto error = hostname_settings_->save(
            field->type() == '"' ? std::optional{field->string()} : std::nullopt, local_usb);
        if (!error.empty())
            return http_error(error == "invalid_hostname" ? 400
                              : error == "storage_fault" || error == "hostname_reconcile_required"
                                  ? 503
                                  : 409,
                              error);
        auto result = ok(hostname_settings_->readback(service_.status().boot_id, local_usb));
        result.etag = revision();
        return result;
    }
    if (restart) {
        if (!json::fields(*root, {}))
            return http_error(400, "invalid_restart");
        if (!restart_)
            return http_error(503, "restart_unavailable");
        pending_restart_ = true;
        pending_transaction_ = transaction;
        ++network_revision_; // Consume the revision; never replay an ambiguous reset.
        auto result = ok("{\"restart_requested\":true}");
        result.status = 202;
        result.etag = revision();
        return result;
    }
    if (r.path == "/api/v1/network") {
        if (!json::fields(*root, {"enabled"}) ||
            (root->get("enabled")->raw != "true" && root->get("enabled")->raw != "false"))
            return http_error(400, "invalid_network");
        if (!network_.request_enabled(root->get("enabled")->boolean()))
            return http_error(503, "network_unavailable");
        pending_transaction_ = transaction;
        ++network_revision_;
        auto result = ok(network_.status());
        result.etag = revision();
        return result;
    }
    std::string candidate;
    if (frequency_resource) {
        const auto checked =
            application::validate_envelope(*root, "transmitter-standalone-frequency/1",
                                           "frequency_hz", device_, service_.status().boot_id);
        if (checked != application::Envelope::Valid)
            return http_error(checked == application::Envelope::TargetMismatch ? 409 : 400,
                              "invalid_frequency_resource");
        if (!standalone::valid_wspr_frequency_token(*root->get("frequency_hz")))
            return http_error(400, "invalid_wspr_frequency");
        if (!effective_config())
            return http_error(409, "not_configured");
        auto updated = *effective_config();
        if (!updated.wspr_base_frequency_hz)
            updated.enabled = false; // A first selection cannot resume an inherited schedule.
        updated.wspr_base_frequency_hz = std::uint32_t(root->get("frequency_hz")->integer());
        if (!standalone::wspr_frequency_allowed(updated, service_.config().minimum_frequency_nhz,
                                                service_.config().maximum_frequency_nhz))
            return http_error(400, "frequency_not_allowed");
        candidate = standalone::serialize_config(updated);
    } else if (calibration_resource) {
        const auto checked =
            application::validate_envelope(*root, "transmitter-rf-calibration/1", "calibration",
                                           device_, service_.status().boot_id);
        if (checked != application::Envelope::Valid)
            return http_error(checked == application::Envelope::TargetMismatch ? 409 : 400,
                              "invalid_calibration_resource");
        const auto value = *root->get("calibration");
        if (!json::fields(value, {"manual_ppm", "mode"}) ||
            value.get("manual_ppm")->type() != '\"' || value.get("mode")->type() != '\"')
            return http_error(400, "invalid_calibration");
        const auto ppb = rf::parse_ppm(value.get("manual_ppm")->string());
        const auto mode = value.get("mode")->string();
        if (!ppb || (mode != "manual" && mode != "ntp"))
            return http_error(400, "invalid_calibration");
        if (!effective_config())
            return http_error(409, "not_configured");
        auto updated = *effective_config();
        // Explicit fields distinguish a deliberate zero/manual from omission.
        updated.manual_correction_ppb = 0;
        updated.ntp_rf_calibration = false;
        candidate = standalone::serialize_config(updated);
        candidate.pop_back();
        candidate += ",\"manual_correction_ppb\":" + std::to_string(*ppb) +
                     ",\"ntp_rf_calibration\":" + (mode == "ntp" ? "true}" : "false}");
    } else if (drive_resource) {
        const auto checked = application::validate_envelope(
            *root, "transmitter-gpio-drive/1", "gpio_drive_ma", device_, service_.status().boot_id);
        if (checked != application::Envelope::Valid)
            return http_error(checked == application::Envelope::TargetMismatch ? 409 : 400,
                              "invalid_drive_resource");
        if (!standalone::valid_gpio_drive_token(*root->get("gpio_drive_ma")))
            return http_error(400, "invalid_gpio_drive");
        if (!effective_config())
            return http_error(409, "not_configured");
        auto updated = *effective_config();
        updated.gpio_drive_ma = unsigned(root->get("gpio_drive_ma")->integer());
        candidate = standalone::serialize_config(updated);
    } else if (scoped_resource) {
        const auto field = station_resource ? "station" : "pins";
        const auto schema = station_resource     ? (extended_station ? "transmitter-station/2"
                                                                     : application::station_schema)
                            : amplifier_resource ? "transmitter-hardware/3"
                                                 : application::hardware_schema;
        switch (application::validate_envelope(*root, schema, field, device_,
                                               service_.status().boot_id)) {
        case application::Envelope::Invalid:
            return http_error(400, "invalid_resource");
        case application::Envelope::UnsupportedSchema:
            return http_error(400, "unsupported_resource_schema");
        case application::Envelope::TargetMismatch:
            return http_error(409, "target_mismatch");
        case application::Envelope::Valid:
            break;
        }
        if (!store_.healthy())
            return http_error(503, "storage_fault");
        if (!store_.config())
            return http_error(409, "not_configured");
        auto updated = *effective_config();
        if (hardware_resource) {
            if (!amplifier_resource && hardware::requires_amplifier_view(updated.pins))
                return http_error(409, "amplifier_view_required");
            const auto pins = hardware::parse_plan(std::string(root->get(field)->raw));
            if (!pins)
                return http_error(400, "invalid_pin_plan");
            if (!amplifier_resource && (hardware::requires_amplifier_view(*pins) ||
                                        root->get(field)->get("amplifier_active_high")))
                return http_error(400, "unsupported_pin_adapter");
            if (!hardware::validate(*pins).valid())
                return {400, hardware::describe(*pins), "application/json", {}};
            if (!hardware::operational(*pins))
                return http_error(400, "unsupported_pin_adapter");
            updated.pins = *pins;
            if (!amplifier_resource)
                updated.pins.amplifier = effective_config()->pins.amplifier;
            if (!root->get(field)->get("amplifier_active_high"))
                updated.pins.amplifier_active_high = effective_config()->pins.amplifier_active_high;
        }
        candidate = standalone::serialize_config(updated);
        if (station_resource) {
            const auto current = json::parse(candidate);
            const auto station = current->get("station")->raw;
            candidate.replace(station.offset(), station.size(), std::string(root->get(field)->raw));
        }
    } else if (r.path == "/api/v1/config" || r.path == "/api/v1/config/2" || drive_config ||
               config_update) {
        if (!store_.healthy())
            return http_error(503, "storage_fault");
        auto supplied = *root;
        auto mode = application::ConfigWrite::Legacy;
        if (config_update) {
            switch (application::validate_config_update(*root, device_, service_.status().boot_id,
                                                        drive_config, amplifier_config)) {
            case application::Envelope::Invalid:
                return http_error(400, "invalid_resource");
            case application::Envelope::UnsupportedSchema:
                return http_error(400, "unsupported_resource_schema");
            case application::Envelope::TargetMismatch:
                return http_error(409, "target_mismatch");
            case application::Envelope::Valid:
                break;
            }
            if (!store_.config())
                return http_error(409, "not_configured");
            supplied = *root->get("config");
            mode = root->get("mode")->string() == "merge" ? application::ConfigWrite::Merge
                                                          : application::ConfigWrite::Replace;
        }
        auto wifi = supplied.get("wifi");
        auto password = wifi ? wifi->get("password") : std::nullopt;
        const auto current_config = effective_config();
        if (password && password->raw == "null" && !current_config)
            return http_error(400, "password_required");
        const auto built = application::config_candidate(supplied, current_config, mode,
                                                         drive_config, amplifier_config);
        if (!built)
            return http_error(400, "invalid_config");
        candidate = *built;
    } else {
        if (!store_.config() || !json::fields(*root, {"schedules"}))
            return http_error(400, "invalid_schedules");
        candidate = standalone::serialize_config(*effective_config());
        auto current = json::parse(candidate);
        auto schedules = current->get("schedules")->raw;
        candidate.replace(schedules.offset(), schedules.size(),
                          static_cast<std::string>(root->get("schedules")->raw));
    }
    if (const auto config_root = json::parse(candidate)) {
        if (const auto pins = config_root->get("pins")) {
            auto plan = hardware::parse_plan(std::string(pins->raw));
            if (!plan)
                return http_error(400, "invalid_pin_plan");
            if (!hardware::validate(*plan).valid())
                return {400, hardware::describe(*plan), "application/json", {}};
            if (!hardware::operational(*plan))
                return http_error(400, "unsupported_pin_adapter");
        }
    }
    const auto validated = standalone::parse_config(candidate);
    if (!validated)
        return http_error(400, "invalid_config");
    if (validated->enabled && !validated->wspr_base_frequency_hz)
        return http_error(400, "standalone_frequency_required");
    const auto existing = effective_config();
    const bool station_changed = !existing || existing->callsign != validated->callsign ||
                                 existing->locator != validated->locator ||
                                 existing->power_dbm != validated->power_dbm;
    if (station_changed &&
        !encoding::wspr_plan(validated->callsign, validated->locator, validated->power_dbm))
        return http_error(400, "unsupported_station_encoding");
    if (station_changed && !extended_config && !extended_station &&
        !encoding::wspr_type1_from_station(validated->callsign, validated->locator,
                                           validated->power_dbm))
        return http_error(400, "unsupported_station_encoding");
    if (local_usb && local_settings_ && consumer_runtime_ && !consumer_runtime_->profile() &&
        consumer_runtime_->source() != provisioning::RuntimeSource::Factory) {
        const auto error = local_settings_->ensure_local_profile();
        if (!error.empty())
            return http_error(503, error);
    }
    if (!local_usb && station_changed && consumer_runtime_ && consumer_runtime_->consumer_profile())
        return http_error(409, "consumer_setup_identity_required");
    if (local_usb && local_settings_ && consumer_runtime_ &&
        consumer_runtime_->consumer_profile()) {
        // Network credentials use the explicit USB Wi-Fi resource, so station
        // promotion cannot silently overwrite the profile-owned network.
        const auto* profile = consumer_runtime_->consumer_profile();
        if (validated->ssid != profile->ssid || validated->password != profile->password ||
            validated->ntp_ipv4 != profile->time_server)
            return http_error(409, "use_usb_wifi_resource");
        const auto error = local_settings_->station_save(*validated);
        if (!error.empty())
            return http_error(503, error);
    }
    if (consumer_runtime_ && consumer_runtime_->consumer_profile()) {
        const auto effective = consumer_runtime_->overlay(*validated);
        if (!effective || effective->ssid != validated->ssid ||
            effective->password != validated->password ||
            effective->ntp_ipv4 != validated->ntp_ipv4 ||
            effective->callsign != validated->callsign ||
            effective->locator != validated->locator ||
            effective->power_dbm != validated->power_dbm)
            return http_error(409, "consumer_setup_identity_required");
    }
    if (station_resource &&
        (extended_station
             ? !encoding::wspr_plan(validated->callsign, validated->locator, validated->power_dbm)
             : !encoding::wspr_type1_from_station(validated->callsign, validated->locator,
                                                  validated->power_dbm)))
        return http_error(400, "unsupported_station_encoding");
    auto response = scheduler_.command("CONFIG " + candidate);
    auto value = json::parse(response);
    if (!value || value->get("ok")->raw != "true") {
        if (value && value->get("error") &&
            value->get("error")->string() == "output_disable_failed")
            return http_error(503, "output_disable_failed");
        return http_error(503, "storage_fault");
    }
    if (calibration_resource)
        return rf_calibration();
    if (frequency_resource)
        return standalone_frequency();
    if (drive_resource)
        return gpio_drive();
    if (station_resource)
        return station_config(extended_station);
    if (hardware_resource)
        return hardware_config(amplifier_resource, amplifier_resource);
    auto result = config(drive_config, amplifier_config);
    result.body.pop_back();
    result.body +=
        std::string(",\"reboot_required\":") + (scheduler_.reboot_required() ? "true}" : "false}");
    return result;
}
} // namespace wsprrypico::network
