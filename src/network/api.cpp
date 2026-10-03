#include "network/api.hpp"

#include "application/resources.hpp"
#include "encoding/wspr.hpp"
#include "hardware/pins.hpp"
#include "network/assets.hpp"
#include "network/identity.hpp"
#include "network/message_job.hpp"
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
std::string BrowserApi::revision() const {
    const auto data = device_ + ":" + service_.status().boot_id + ":" +
                      std::to_string(network_revision_) + ":" +
                      std::to_string(store_.config_sequence()) + ":" +
                      (store_.config() ? standalone::serialize_config(*store_.config()) : "null");
    const auto digest =
        sha256(std::span(reinterpret_cast<const std::uint8_t*>(data.data()), data.size()));
    return '"' + hex(digest) + '"';
}
HttpResponse BrowserApi::config() const {
    std::string body = "null";
    if (store_.config()) {
        auto redacted = *store_.config();
        redacted.password.clear();
        body = standalone::serialize_config(redacted);
        const auto pos = body.find("\"password\":\"\"");
        body.replace(pos, 13, "\"password\":null");
    }
    auto result = ok("{\"config\":" + body + "}");
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::station_config() const {
    const bool saved = store_.healthy() && store_.config().has_value();
    auto result = ok("{\"schema\":" + json::quote(application::station_schema) +
                     ",\"target\":" + application::target(device_, service_.status().boot_id) +
                     ",\"station\":" + (saved ? application::station(*store_.config()) : "null") +
                     ",\"saved_generation\":" +
                     (saved ? json::quote(std::to_string(store_.config_sequence())) : "null") +
                     ",\"storage_healthy\":" + (store_.healthy() ? "true}" : "false}"));
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::hardware_config() const {
    const bool saved = store_.healthy() && store_.config().has_value();
    const auto active = hardware::serialize_plan(scheduler_.active_pins());
    const auto boot = service_.status().boot_id;
    const auto data = device_ + ':' + boot + ":hardware:" + active;
    const auto digest =
        sha256(std::span(reinterpret_cast<const std::uint8_t*>(data.data()), data.size()));
    auto result =
        ok("{\"schema\":" + json::quote(application::hardware_schema) +
           ",\"target\":" + application::target(device_, boot) +
           ",\"saved\":" + (saved ? hardware::serialize_plan(store_.config()->pins) : "null") +
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
    result.etag = revision();
    return result;
}
HttpResponse BrowserApi::application_config() const {
    const auto status = scheduler_.status();
    const auto value = json::parse(status);
    if (!value)
        return http_error(503, "resource_exhausted");
    std::string recurrence = "{\"authority\":\"member\"";
    for (const auto field : {"enabled", "suspended", "schedules", "schedule_base_frequency_nhz"})
        recurrence += ',' + json::quote(field) + ':' + std::string(value->get(field)->raw);
    recurrence +=
        ",\"expires_utc_s\":" + json::quote(std::string(value->get("expires_utc_s")->raw));
    recurrence += '}';
    auto result =
        ok("{\"schema\":" + json::quote(application::application_schema) +
           ",\"target\":" + application::target(device_, service_.status().boot_id) +
           ",\"station\":" + station_config().body + ",\"hardware\":" + hardware_config().body +
           ",\"recurrence\":" + recurrence + ",\"capabilities\":" + application::capabilities() +
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
                                std::string_view authority, std::uint64_t transaction) {
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
        const auto origin_authority =
            origin.starts_with("https://") ? canonical_authority(origin.substr(8)) : std::nullopt;
        if (!allowed(origin_authority) || *origin_authority != *host)
            return http_error(403, "origin_or_content_type");
    }
    if (mutation &&
        (r.header("x-wsprrypico-request") != "1" || r.header("content-type") != "application/json"))
        return http_error(403, "origin_or_content_type");
    if (!r.header("sec-fetch-site").empty() && r.header("sec-fetch-site") != "same-origin" &&
        r.header("sec-fetch-site") != "none")
        return http_error(403, "cross_site_request");
    service_.poll();
    if (r.method == "GET") {
        if (auto asset = web_asset(r.path)) {
            // Generated assets live in flash for the process lifetime. Stream
            // the immutable bytes directly rather than copying a full page
            // into heap while WTP and RF state are resident. Preserve bounded
            // transport/header scratch plus the independent authority reserve.
            if (!memory_admitted(4096))
                return http_error(503, "resource_exhausted");
            return {200, {}, std::string(asset->type), {}, {}, asset->body};
        }
        if (r.path == "/api/v1/capabilities") {
            Request request;
            request.operation = "CAPS";
            Response response;
            response.ok = true;
            const auto caps =
                encode_response(request, response, service_.config(), device_, firmware_);
            auto value = json::parse(caps);
            return ok(
                "{\"api_version\":1,\"wtp\":" + std::string(value->get("body")->raw) +
                ",\"message_jobs\":{\"operation\":\"LOAD_MESSAGE\",\"max_characters\":32,"
                "\"tail_ns\":\"1000\",\"max_repeat_count\":512,\"modes\":[\"qrss\",\"fskcw\","
                "\"dfcw\"]}"
                ",\"features\":{\"config\":true,\"schedules\":true,\"jobs\":true,\"network\":true,"
                "\"application\":true,\"station\":true,\"hardware\":true,"
                "\"softap\":true,\"ble\":true,\"restart\":" +
                (restart_ ? "true" : "false") +
                "},\"application_resources\":{\"schema\":\"transmitter-application/1\","
                "\"read\":\"/api/v1/application\",\"station\":\"/api/v1/station\","
                "\"hardware\":\"/api/v1/hardware\",\"management_carrier\":\"authenticated_https\"},"
                "\"active_job_connections\":" +
                (active_job_connections_ ? "true" : "false") +
                ",\"max_network_connections\":2,\"max_wtp_connections\":1,\"max_pending_"
                "connections\":1,\"max_handshakes\":1,\"max_body_bytes\":32768}");
        }
        if (r.path == "/api/v1/status" || r.path == "/api/v1/jobs")
            return ok(
                "{\"job\":" + status_json(service_.status()) +
                ",\"standalone\":" + scheduler_.status() + ",\"network\":" + network_.status() +
                ",\"transport\":" + (transport_ ? transport_(transport_context_) : "null") + "}");
        if (r.path == "/api/v1/pins")
            return ok("{\"choices\":" + hardware::choices() +
                      ",\"active\":" + hardware::serialize_plan(scheduler_.active_pins()) + "}");
        if (r.path == "/api/v1/config")
            return config();
        if (r.path == "/api/v1/application")
            return application_config();
        if (r.path == "/api/v1/station")
            return station_config();
        if (r.path == "/api/v1/hardware")
            return hardware_config();
        if (r.path == "/api/v1/network") {
            auto result = ok(network_.status());
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
    // Review candidates without changing Store, scheduler, engine or GPIO state.
    if (r.path == "/api/v1/pins/validate" && r.method == "POST") {
        const auto plan = hardware::parse_plan(std::string(r.body_view()));
        if (!plan)
            return http_error(400, "invalid_pin_plan");
        return ok(hardware::describe(*plan));
    }
    if (r.method == "POST" && (r.path == "/api/v1/jobs" || r.path.starts_with("/api/v1/jobs/")))
        return job(r, principal);
    const bool restart = r.method == "POST" && r.path == "/api/v1/restart";
    const bool station_resource = r.path == "/api/v1/station";
    const bool hardware_resource = r.path == "/api/v1/hardware";
    const bool scoped_resource = station_resource || hardware_resource;
    if (!restart &&
        (r.method != "PUT" || (r.path != "/api/v1/config" && r.path != "/api/v1/schedules" &&
                               r.path != "/api/v1/network" && !scoped_resource)))
        return http_error(404, "not_found");
    if (scoped_resource && r.body_view().size() > application::max_update_bytes)
        return http_error(413, "resource_body_too_large");
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
    if (scoped_resource) {
        const auto field = station_resource ? "station" : "pins";
        const auto schema =
            station_resource ? application::station_schema : application::hardware_schema;
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
        auto updated = *store_.config();
        if (hardware_resource) {
            const auto pins = hardware::parse_plan(std::string(root->get(field)->raw));
            if (!pins)
                return http_error(400, "invalid_pin_plan");
            if (!hardware::validate(*pins).valid())
                return {400, hardware::describe(*pins), "application/json", {}};
            if (!hardware::operational(*pins))
                return http_error(400, "unsupported_pin_adapter");
            updated.pins = *pins;
        }
        candidate = standalone::serialize_config(updated);
        if (station_resource) {
            const auto current = json::parse(candidate);
            const auto station = current->get("station")->raw;
            candidate.replace(station.offset(), station.size(), std::string(root->get(field)->raw));
        }
    } else if (r.path == "/api/v1/config") {
        auto wifi = root->get("wifi");
        auto password = wifi ? wifi->get("password") : std::nullopt;
        candidate = std::string(r.body_view());
        if (password && password->raw == "null") {
            if (!store_.config())
                return http_error(400, "password_required");
            const auto offset = password->raw.offset();
            candidate.replace(offset, 4, json::quote(store_.config()->password));
        }
    } else {
        if (!store_.config() || !json::fields(*root, {"schedules"}))
            return http_error(400, "invalid_schedules");
        candidate = standalone::serialize_config(*store_.config());
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
    if (station_resource && !encoding::wspr_type1_from_station(
                                validated->callsign, validated->locator, validated->power_dbm))
        return http_error(400, "unsupported_station_encoding");
    auto response = scheduler_.command("CONFIG " + candidate);
    auto value = json::parse(response);
    if (!value || value->get("ok")->raw != "true") {
        if (scoped_resource && value && value->get("error") &&
            value->get("error")->string() == "output_disable_failed")
            return http_error(503, "output_disable_failed");
        return http_error(503, "storage_fault");
    }
    if (station_resource)
        return station_config();
    if (hardware_resource)
        return hardware_config();
    auto result = config();
    result.body.pop_back();
    result.body +=
        std::string(",\"reboot_required\":") + (scheduler_.reboot_required() ? "true}" : "false}");
    return result;
}
} // namespace wsprrypico::network
