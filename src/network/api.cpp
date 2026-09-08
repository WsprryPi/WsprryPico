#include "network/api.hpp"

#include "network/assets.hpp"
#include "wtp/codec.hpp"
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
} // namespace
std::string BrowserApi::revision() const {
    const auto data = service_.status().boot_id + ":" + std::to_string(network_revision_) + ":" +
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
HttpResponse BrowserApi::job(const HttpRequest& r, std::string_view principal) {
    auto body = json::parse(r.body);
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
        operation != "RELEASE" && operation != "LOAD" && operation != "ARM" && operation != "ABORT")
        return http_error(400, "unsupported_operation");
    // Browser schema is versioned by the URL. WTP envelope/codec stays internal.
    std::string payload;
    payload.reserve(r.body.size() + 128);
    payload = "{\"type\":\"request\",\"protocol\":\"WTP/1\",\"session_id\":" +
              std::string(body->get("session_id")->raw) +
              ",\"request_id\":" + std::string(body->get("request_id")->raw) +
              ",\"op\":" + std::string(body->get("operation")->raw) +
              ",\"body\":" + std::string(body->get("body")->raw) + "}";
    if (payload.size() > max_http_body)
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
    auto response = service_.handle(*request);
    const auto encoded = encode_response(*request, response, service_.config(), device_, firmware_);
    const auto result = json::parse(encoded);
    return {response.ok ? 200U : 409U,
            "{\"ok\":" + std::string(response.ok ? "true" : "false") +
                ",\"request_id\":" + json::quote(request->request_id) +
                (response.ok ? ",\"result\":" + std::string(result->get("body")->raw)
                             : ",\"error\":" + std::string(result->get("error")->raw)) +
                "}",
            "application/json",
            {}};
}
HttpResponse BrowserApi::handle(const HttpRequest& r, std::string_view principal,
                                std::string_view authority, std::uint64_t transaction) {
    if (!wtp::memory_admitted(r.body.size() * 2 + 16384))
        return http_error(503, "resource_exhausted");
    if (r.body.size() > max_http_body)
        return http_error(413, "body_too_large");
    if (principal.empty())
        return http_error(401, "authentication_required");
    if (authority.empty() || r.header("host") != authority)
        return http_error(403, "invalid_host");
    const bool mutation = r.method != "GET";
    if (mutation &&
        (r.header("origin") != "https://" + std::string(authority) ||
         r.header("x-wsprrypico-request") != "1" || r.header("content-type") != "application/json"))
        return http_error(403, "origin_or_content_type");
    if (!r.header("sec-fetch-site").empty() && r.header("sec-fetch-site") != "same-origin" &&
        r.header("sec-fetch-site") != "none")
        return http_error(403, "cross_site_request");
    service_.poll();
    if (r.method == "GET") {
        if (auto asset = web_asset(r.path)) {
            if (!memory_admitted(asset->body.size() * 3))
                return http_error(503, "resource_exhausted");
            return {200, std::string(asset->body), std::string(asset->type), {}};
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
                ",\"features\":{\"config\":true,\"schedules\":true,\"jobs\":true,\"network\":true,"
                "\"softap\":false,\"ble\":false},\"active_job_connections\":" +
                (active_job_connections_ ? "true" : "false") +
                ",\"max_network_connections\":2,\"max_wtp_connections\":1,\"max_pending_"
                "connections\":1,\"max_handshakes\":1,\"max_body_bytes\":32768}");
        }
        if (r.path == "/api/v1/status" || r.path == "/api/v1/jobs")
            return ok(
                "{\"job\":" + status_json(service_.status()) +
                ",\"standalone\":" + scheduler_.status() + ",\"network\":" + network_.status() +
                ",\"transport\":" + (transport_ ? transport_(transport_context_) : "null") + "}");
        if (r.path == "/api/v1/config")
            return config();
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
    if (r.method == "POST" && (r.path == "/api/v1/jobs" || r.path.starts_with("/api/v1/jobs/")))
        return job(r, principal);
    if (r.method != "PUT" || (r.path != "/api/v1/config" && r.path != "/api/v1/schedules" &&
                              r.path != "/api/v1/network"))
        return http_error(404, "not_found");
    if (r.header("if-match").empty())
        return http_error(428, "revision_required");
    if (r.header("if-match") != revision())
        return http_error(412, "revision_conflict");
    if (!scheduler_.idle())
        return http_error(409, "busy");
    auto root = json::parse(r.body);
    if (!root)
        return http_error(400, "invalid_json");
    if (r.path == "/api/v1/network") {
        if (!json::fields(*root, {"enabled"}) ||
            (root->get("enabled")->raw != "true" && root->get("enabled")->raw != "false"))
            return http_error(400, "invalid_network");
        if (pending_transaction_)
            return http_error(409, "network_change_pending");
        if (!network_.request_enabled(root->get("enabled")->boolean()))
            return http_error(503, "network_unavailable");
        pending_transaction_ = transaction;
        ++network_revision_;
        auto result = ok(network_.status());
        result.etag = revision();
        return result;
    }
    std::string candidate;
    if (r.path == "/api/v1/config") {
        auto wifi = root->get("wifi");
        auto password = wifi ? wifi->get("password") : std::nullopt;
        candidate = r.body;
        if (password && password->raw == "null") {
            if (!store_.config())
                return http_error(400, "password_required");
            const auto offset = static_cast<std::size_t>(password->raw.data() - r.body.data());
            candidate.replace(offset, 4, json::quote(store_.config()->password));
        }
    } else {
        if (!store_.config() || !json::fields(*root, {"schedules"}))
            return http_error(400, "invalid_schedules");
        candidate = standalone::serialize_config(*store_.config());
        auto current = json::parse(candidate);
        auto schedules = current->get("schedules")->raw;
        candidate.replace(static_cast<std::size_t>(schedules.data() - candidate.data()),
                          schedules.size(), root->get("schedules")->raw);
    }
    if (!standalone::parse_config(candidate))
        return http_error(400, "invalid_config");
    auto response = scheduler_.command("CONFIG " + candidate);
    auto value = json::parse(response);
    if (!value || value->get("ok")->raw != "true")
        return http_error(503, "storage_fault");
    auto result = config();
    result.body.pop_back();
    result.body += ",\"reboot_required\":true}";
    return result;
}
} // namespace wsprrypico::network
