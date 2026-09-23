#include "network/softap_api.hpp"

#include "network/assets.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <charconv>

namespace wsprrypico::network {
namespace {
using provisioning::AccessCode;
using provisioning::SoftApOperation;
using provisioning::SoftApSurface;

std::string_view controller_code(time::ControllerTimeCode code) {
    using time::ControllerTimeCode;
    switch (code) {
    case ControllerTimeCode::Ok:
        return "ok";
    case ControllerTimeCode::Invalid:
        return "invalid_request";
    case ControllerTimeCode::WrongDevice:
        return "wrong_device";
    case ControllerTimeCode::AuthenticationRequired:
        return "authentication_required";
    case ControllerTimeCode::Replay:
        return "replay";
    case ControllerTimeCode::Timeout:
        return "timeout";
    case ControllerTimeCode::SourceBusy:
        return "time_source_busy";
    case ControllerTimeCode::Disagreement:
        return "time_disagreement";
    case ControllerTimeCode::Uncertainty:
        return "time_uncertainty";
    }
    return "invalid_request";
}

std::string_view source_name(time::ActiveTimeSource source) {
    using time::ActiveTimeSource;
    switch (source) {
    case ActiveTimeSource::None:
        return "none";
    case ActiveTimeSource::Sntp:
        return "sntp";
    case ActiveTimeSource::Controller:
        return "controller";
    case ActiveTimeSource::Disagreement:
        return "disagreement";
    }
    return "none";
}

bool exact_fields(const wtp::json::Value& root, std::initializer_list<std::string_view> fields) {
    return wtp::json::fields(root, fields);
}
} // namespace

provisioning::Activity SoftApApi::activity() const {
    const auto current = service_.activity();
    return {current.owned,
            true,
            current.output_active,
            current.state == wtp::State::Armed,
            current.state == wtp::State::Running,
            current.state == wtp::State::Failed};
}

std::string_view SoftApApi::surface_name(SoftApSurface surface) {
    switch (surface) {
    case SoftApSurface::BlankReadOnly:
        return "blank_read_only";
    case SoftApSurface::ProvisionedPreClock:
        return "provisioned_preclock";
    case SoftApSurface::Normal:
        return "normal";
    }
    return "blank_read_only";
}

HttpResponse SoftApApi::access_error(AccessCode code) {
    switch (code) {
    case AccessCode::AuthenticationRequired:
    case AccessCode::Expired:
        return http_error(401, "authentication_required");
    case AccessCode::WrongDevice:
    case AccessCode::ConfirmationRequired:
        return http_error(403, "forbidden");
    case AccessCode::Busy:
    case AccessCode::Capacity:
    case AccessCode::Conflict:
        return http_error(409, "busy");
    case AccessCode::StorageFault:
    case AccessCode::BondEraseFault:
        return http_error(503, "access_unavailable");
    case AccessCode::Invalid:
        return http_error(400, "invalid_request");
    case AccessCode::Ok:
        break;
    }
    return http_error(400, "invalid_request");
}

HttpResponse SoftApApi::identity(SoftApSurface surface) const {
    const auto status = time_.status();
    return {200,
            "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                ",\"firmware\":" + wtp::json::quote(firmware_) +
                ",\"surface\":" + wtp::json::quote(surface_name(surface)) +
                ",\"authenticated\":false,\"time_source\":" +
                wtp::json::quote(source_name(status.source)) + "}",
            "application/json",
            {}};
}

HttpResponse SoftApApi::local_status(std::string_view principal, std::string_view wtp_session,
                                     SoftApSurface surface) const {
    const auto status = time_.status();
    return {200,
            "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                ",\"firmware\":" + wtp::json::quote(firmware_) +
                ",\"surface\":" + wtp::json::quote(surface_name(surface)) +
                ",\"principal\":" + wtp::json::quote(principal) + ",\"wtp_session\":" +
                (wtp_session.empty() ? "null" : wtp::json::quote(wtp_session)) +
                ",\"default_password\":" +
                std::string(access_.default_password_active() ? "true" : "false") +
                ",\"time_source\":" + wtp::json::quote(source_name(status.source)) +
                ",\"time_age_ns\":\"" + std::to_string(status.age_ns) +
                "\",\"time_uncertainty_ns\":\"" + std::to_string(status.uncertainty_ns) +
                "\",\"time_disagreement\":" + (status.disagreement ? "true}" : "false}"),
            "application/json",
            {}};
}

SoftApOperation SoftApApi::operation(const HttpRequest& request, std::string& session,
                                     bool& valid) {
    valid = true;
    if (request.method == "GET") {
        if (request.path == "/api/v1/status" || request.path == "/api/v1/jobs")
            return SoftApOperation::Status;
        if (request.path == "/api/v1/capabilities")
            return SoftApOperation::Hello;
        if (request.path == "/api/v1/config" || request.path == "/api/v1/schedules" ||
            request.path == "/api/v1/network")
            return SoftApOperation::Configure;
        valid = false;
        return SoftApOperation::Status;
    }
    if (request.method == "POST" &&
        (request.path == "/api/v1/jobs" || request.path.starts_with("/api/v1/jobs/"))) {
        const auto root = wtp::json::parse(request.body_view());
        if (!root || !exact_fields(*root, {"session_id", "request_id", "operation", "body"})) {
            valid = false;
            return SoftApOperation::Status;
        }
        const auto id = root->get("session_id");
        const auto name = root->get("operation");
        if (!id || !wtp::json::identifier(*id) || !name || name->type() != '"') {
            valid = false;
            return SoftApOperation::Status;
        }
        session = id->string();
        const auto op = name->string();
        if (op == "HELLO")
            return SoftApOperation::Hello;
        if (op == "ABORT")
            return SoftApOperation::Abort;
        if (op == "LOAD" || op == "LOAD_MESSAGE")
            return SoftApOperation::Load;
        if (op == "ARM")
            return SoftApOperation::Arm;
        if (op == "CLAIM" || op == "RENEW" || op == "RELEASE")
            return SoftApOperation::Load;
        valid = false;
        return SoftApOperation::Status;
    }
    if ((request.method == "PUT" &&
         (request.path == "/api/v1/config" || request.path == "/api/v1/schedules" ||
          request.path == "/api/v1/network")) ||
        (request.method == "POST" && request.path == "/api/v1/restart"))
        return SoftApOperation::Configure;
    valid = false;
    return SoftApOperation::Status;
}

HttpResponse SoftApApi::challenge(const HttpRequest& request, std::string_view principal,
                                  std::string_view session, std::uint64_t transaction) {
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !exact_fields(*root, {"version", "device_id", "session_id", "nonce"}))
        return http_error(400, "invalid_request");
    const auto version = root->get("version");
    const auto requested_device = root->get("device_id");
    const auto requested_session = root->get("session_id");
    const auto nonce = root->get("nonce");
    if (!version || version->type() != '1' || version->integer() != 1 || !requested_device ||
        !wtp::json::identifier(*requested_device) || !requested_session ||
        !wtp::json::identifier(*requested_session) || !nonce || nonce->type() != '"' ||
        requested_session->string() != session)
        return http_error(400, "invalid_request");
    auto result = time_.challenge(principal, session, requested_device->string(), nonce->string());
    if (result.code != time::ControllerTimeCode::Ok)
        return http_error(result.code == time::ControllerTimeCode::WrongDevice ? 403 : 409,
                          controller_code(result.code));
    if (!time_.challenge_response_started(principal, session, requested_device->string(),
                                          result.nonce)) {
        time_.cancel_challenge(principal, session);
        return http_error(503, "time_unavailable");
    }
    // A newly accepted challenge proves the arbiter has no prior live challenge:
    // it either completed, was cancelled, or was reaped after its bounded lifetime.
    // Retire the response-delivery bookkeeping before reserving the one slot needed
    // to roll the new challenge back if this response is not delivered.
    for (auto& pending : pending_time_)
        pending = {};
    auto slot = std::find_if(pending_time_.begin(), pending_time_.end(),
                             [](const PendingTime& item) { return !item.live; });
    if (slot == pending_time_.end()) {
        time_.cancel_challenge(principal, session);
        return http_error(503, "resource_exhausted");
    }
    *slot = {transaction, std::string(principal), std::string(session), true};
    return {200,
            "{\"ok\":true,\"device_id\":" + wtp::json::quote(device_) +
                ",\"session_id\":" + wtp::json::quote(session) +
                ",\"nonce\":" + wtp::json::quote(result.nonce) + ",\"sampled_monotonic_ns\":\"" +
                std::to_string(result.sampled_monotonic_ns) + "\"}",
            "application/json",
            {}};
}

HttpResponse SoftApApi::submit_time(const HttpRequest& request, std::string_view principal,
                                    std::string_view session) {
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !exact_fields(*root, {"version", "device_id", "session_id", "nonce", "utc_ns"}))
        return http_error(400, "invalid_request");
    const auto version = root->get("version");
    const auto requested_device = root->get("device_id");
    const auto requested_session = root->get("session_id");
    const auto nonce = root->get("nonce");
    const auto utc = root->get("utc_ns");
    if (!version || version->type() != '1' || version->integer() != 1 || !requested_device ||
        !wtp::json::identifier(*requested_device) || !requested_session ||
        !wtp::json::identifier(*requested_session) || !nonce || nonce->type() != '"' || !utc ||
        utc->type() != '"' || requested_session->string() != session)
        return http_error(400, "invalid_request");
    std::uint64_t utc_ns = 0;
    const auto text = utc->string();
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), utc_ns);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size())
        return http_error(400, "invalid_request");
    const auto result =
        time_.submit(principal, session, requested_device->string(), nonce->string(), utc_ns);
    if (result != time::ControllerTimeCode::Ok)
        return http_error(result == time::ControllerTimeCode::WrongDevice ? 403 : 409,
                          controller_code(result));
    for (auto& pending : pending_time_)
        if (pending.live && pending.principal == principal && pending.session == session)
            pending = {};
    return {200, "{\"ok\":true}", "application/json", {}};
}

HttpResponse SoftApApi::handle(const HttpRequest& request, SoftApSurface surface,
                               std::string_view authority, std::uint64_t now_ms,
                               std::uint64_t transaction) {
    if (request.method == "GET" && request.path == "/local/v1/identity")
        return identity(surface);
    if (request.method == "GET") {
        if (auto asset = web_asset(request.path)) {
            if (surface == SoftApSurface::BlankReadOnly && request.path != "/")
                return http_error(404, "not_found");
            if (surface == SoftApSurface::BlankReadOnly) {
                const auto state = identity(surface).body;
                return {200,
                        "<!doctype html><meta charset=utf-8><meta name=viewport "
                        "content=\"width=device-width,initial-scale=1\"><title>WsprryPico</title>"
                        "<h1>WsprryPico recovery</h1><p>This device has no authenticated server "
                        "identity. This page is read-only. Provision it over encrypted BLE or "
                        "USB before entering any credential.</p><pre>" +
                            state + "</pre>",
                        "text/html; charset=utf-8",
                        {}};
            }
            return {200, {}, std::string(asset->type), {}, {}, asset->body};
        }
    }
    if (surface == SoftApSurface::BlankReadOnly)
        return http_error(401, "authentication_required");
    if (request.path == "/local/v1/login") {
        auto admitted = admission_.login(request, surface, service_.owner_session_id(), now_ms);
        admitted.response.set_cookie = admitted.set_cookie;
        return std::move(admitted.response);
    }
    std::string session(request.header("x-wsprrypico-session"));
    if (session.empty() || session.size() > 64)
        return http_error(400, "invalid_session");
    if (request.path == "/local/v1/logout") {
        const auto result = admission_.logout(request, surface, session,
                                              service_.owner_session_id(), activity(), now_ms);
        auto response = result == AccessCode::Ok
                            ? HttpResponse{200, "{\"ok\":true}", "application/json", {}}
                            : access_error(result);
        if (result == AccessCode::Ok)
            response.set_cookie =
                "__Host-wsprrypico=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Strict";
        return response;
    }
    SoftApOperation selected = SoftApOperation::Status;
    bool valid = true;
    std::string body_session;
    if (request.path == "/local/v1/status")
        selected = SoftApOperation::Status;
    else if (request.path == "/local/v1/time/challenge" || request.path == "/local/v1/time/submit")
        selected = SoftApOperation::Time;
    else if (request.path.starts_with("/api/v1/")) {
        selected = operation(request, body_session, valid);
        if (!valid || (!body_session.empty() && body_session != session))
            return http_error(400, "invalid_request");
    } else
        return http_error(404, "not_found");
    const auto requested_session =
        request.path == "/local/v1/status" ? std::string_view{} : std::string_view(session);
    const auto authorized =
        admission_.authorize(request, surface, selected, requested_session, activity(), now_ms,
                             service_.owner_session_id(), false);
    if (authorized.code != AccessCode::Ok)
        return access_error(authorized.code);
    if (request.path == "/local/v1/status")
        return local_status(authorized.authorization.principal, authorized.wtp_session, surface);
    if (request.path == "/local/v1/time/challenge")
        return challenge(request, authorized.authorization.principal, session, transaction);
    if (request.path == "/local/v1/time/submit")
        return submit_time(request, authorized.authorization.principal, session);
    auto response =
        browser_.handle(request, authorized.authorization.principal, authority, transaction);
    if (selected == SoftApOperation::Hello && request.method == "POST" && response.status >= 200 &&
        response.status < 300) {
        const auto bound = admission_.authorize(request, surface, selected, session, activity(),
                                                now_ms, service_.owner_session_id(), true);
        if (bound.code != AccessCode::Ok)
            return access_error(bound.code);
    }
    return response;
}

void SoftApApi::finish_request(std::uint64_t transaction, bool apply) {
    browser_.finish_request(transaction, apply);
    if (apply)
        return;
    for (auto& pending : pending_time_) {
        if (!pending.live || pending.transaction != transaction)
            continue;
        time_.cancel_challenge(pending.principal, pending.session);
        pending = {};
    }
}

} // namespace wsprrypico::network
