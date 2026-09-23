#include "provisioning/ble_session.hpp"

#include "wtp/json.hpp"

#include <charconv>
#include <optional>

namespace wsprrypico::provisioning {
namespace {
void secure_clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}

std::string_view access_name(AccessCode code) {
    switch (code) {
    case AccessCode::Ok: return "ok";
    case AccessCode::Invalid: return "invalid_request";
    case AccessCode::AuthenticationRequired: return "authentication_required";
    case AccessCode::ConfirmationRequired: return "confirmation_required";
    case AccessCode::WrongDevice: return "wrong_device";
    case AccessCode::Busy: return "busy";
    case AccessCode::Capacity: return "capacity";
    case AccessCode::Expired: return "expired";
    case AccessCode::Conflict: return "conflict";
    case AccessCode::StorageFault: return "storage_fault";
    case AccessCode::BondEraseFault: return "bond_erase_fault";
    }
    return "invalid_request";
}

Code manager_code(AccessCode code) {
    switch (code) {
    case AccessCode::Ok: return Code::Ok;
    case AccessCode::Invalid: return Code::InvalidRequest;
    case AccessCode::AuthenticationRequired:
    case AccessCode::ConfirmationRequired: return Code::AuthenticationRequired;
    case AccessCode::WrongDevice: return Code::WrongDevice;
    case AccessCode::Busy: return Code::Busy;
    case AccessCode::Capacity: return Code::SessionBusy;
    case AccessCode::Expired: return Code::Timeout;
    case AccessCode::Conflict: return Code::Conflict;
    case AccessCode::StorageFault:
    case AccessCode::BondEraseFault: return Code::StorageFault;
    }
    return Code::InvalidRequest;
}

CommandReply reply(std::string_view request_id, AccessCode code, std::uint64_t generation) {
    if (request_id.size() != 32)
        return {};
    std::string notification = "{\"version\":1,\"request_id\":" +
                               wtp::json::quote(request_id) + ",\"ok\":" +
                               (code == AccessCode::Ok ? "true" : "false");
    if (code != AccessCode::Ok)
        notification += ",\"error\":" + wtp::json::quote(access_name(code));
    notification += ",\"generation\":" + std::to_string(generation) + "}";
    return {manager_code(code), std::move(notification)};
}

CommandReply field_reply(std::string_view request_id, Code code, std::string body = {}) {
    if (request_id.size() != 32)
        return {};
    std::string notification = "{\"version\":1,\"request_id\":" +
                               wtp::json::quote(request_id) + ",\"ok\":" +
                               (code == Code::Ok ? "true" : "false");
    if (code != Code::Ok)
        notification += ",\"error\":" + wtp::json::quote(code_name(code));
    else if (!body.empty())
        notification += "," + body;
    notification += '}';
    if (notification.size() > max_notification_bytes)
        return {};
    return {code, std::move(notification)};
}

Code time_code(time::ControllerTimeCode code) {
    using time::ControllerTimeCode;
    switch (code) {
    case ControllerTimeCode::Ok: return Code::Ok;
    case ControllerTimeCode::Invalid: return Code::InvalidRequest;
    case ControllerTimeCode::WrongDevice: return Code::WrongDevice;
    case ControllerTimeCode::AuthenticationRequired: return Code::AuthenticationRequired;
    case ControllerTimeCode::Replay: return Code::Replay;
    case ControllerTimeCode::Timeout: return Code::Timeout;
    case ControllerTimeCode::SourceBusy: return Code::Busy;
    case ControllerTimeCode::Disagreement: return Code::Conflict;
    case ControllerTimeCode::Uncertainty: return Code::InvalidRequest;
    }
    return Code::InvalidRequest;
}

std::string_view source_name(time::ActiveTimeSource source) {
    switch (source) {
    case time::ActiveTimeSource::None: return "none";
    case time::ActiveTimeSource::Sntp: return "sntp";
    case time::ActiveTimeSource::Controller: return "controller";
    case time::ActiveTimeSource::Disagreement: return "disagreement";
    }
    return "none";
}

std::string_view pattern_name(IndicatorPattern pattern) {
    switch (pattern) {
    case IndicatorPattern::Off: return "off";
    case IndicatorPattern::SoftApReady: return "softap_ready";
    case IndicatorPattern::Identify: return "identify";
    }
    return "off";
}

bool decimal(std::string_view value, std::uint64_t& output) {
    if (value.empty() || (value.size() > 1 && value.front() == '0'))
        return false;
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), output);
    return parsed.ec == std::errc{} && parsed.ptr == value.data() + value.size();
}
} // namespace

bool BleCommandSession::connected(std::uint64_t peer, bool encrypted, bool new_pairing,
                                  std::string link_session, std::uint64_t now_ms) {
    const auto admitted = access_.ble_connect(peer, encrypted, new_pairing,
                                              std::move(link_session), now_ms);
    connected_ = admitted.code == AccessCode::Ok;
    return connected_;
}

void BleCommandSession::disconnected() {
    if (connected_) {
        if (controller_time_ && !pending_time_nonce_.empty())
            controller_time_->cancel_challenge(principal(), field_session_);
        (void)access_.ble_disconnect();
    }
    connected_ = false;
    secure_clear(field_session_);
    secure_clear(pending_time_nonce_);
    secure_clear(pending_apply_request_);
    pending_apply_generation_ = 0;
    delivery_confirmed_ = false;
}

bool BleCommandSession::authorized() const {
    return connected_ && access_.ble_authorization().authenticated;
}

std::string BleCommandSession::principal() const {
    return connected_ ? access_.ble_authorization().principal : std::string{};
}

CommandReply BleCommandSession::authorize(std::string_view command, std::uint64_t now_ms) {
    const auto root = wtp::json::parse(command);
    if (!root || !wtp::json::fields(*root, {"version", "operation", "request_id", "session_id",
                                            "device_id", "password"}))
        return {};
    const auto version = root->get("version");
    const auto operation = root->get("operation");
    const auto request = root->get("request_id");
    const auto session = root->get("session_id");
    const auto device = root->get("device_id");
    const auto password_value = root->get("password");
    if (!version || version->type() != '1' || version->integer() != 1 || !operation ||
        operation->string() != "authorize" || !request || !wtp::json::identifier(*request) ||
        !session || !wtp::json::identifier(*session) || !device ||
        !wtp::json::identifier(*device) || !password_value || password_value->type() != '"')
        return {};
    const auto request_id = request->string();
    if (device->string() != device_id_)
        return reply(request_id, AccessCode::WrongDevice, manager_.status().generation);
    auto password = password_value->string();
    const auto code = authorized()
                          ? AccessCode::Ok
                          : (valid_local_password(password)
                                 ? access_.ble_authorize(password, now_ms).code
                                 : AccessCode::AuthenticationRequired);
    secure_clear(password);
    if (code == AccessCode::Ok)
        field_session_ = session->string();
    return reply(request_id, code, manager_.status().generation);
}

CommandReply BleCommandSession::field_command(std::string_view command,
                                              std::uint64_t now_ms) {
    const auto root = wtp::json::parse(command);
    if (!root)
        return {};
    const auto version = root->get("version");
    const auto operation = root->get("operation");
    const auto request = root->get("request_id");
    const auto session = root->get("session_id");
    const auto device = root->get("device_id");
    if (!version || version->type() != '1' || version->integer() != 1 || !operation ||
        operation->type() != '"' || !request || !wtp::json::identifier(*request) || !session ||
        !wtp::json::identifier(*session) || !device || !wtp::json::identifier(*device))
        return {};
    const auto request_id = request->string();
    if (device->string() != device_id_)
        return field_reply(request_id, Code::WrongDevice);
    const auto authorization = access_.ble_authorization();
    if (!authorization.authenticated || !authorization.confidential ||
        !authorization.local || authorization.principal.empty() || field_session_.empty() ||
        session->string() != field_session_)
        return field_reply(request_id, Code::AuthenticationRequired);

    const auto name = operation->string();
    if (name == "identify") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id",
                                "device_id"}) ||
            !indicator_)
            return field_reply(request_id, Code::InvalidRequest);
        const auto code = indicator_->identify(request_id, device_id_, true, true, now_ms);
        if (code == IndicatorCode::Ok)
            return field_reply(request_id, Code::Ok, "\"identified\":true");
        if (code == IndicatorCode::Busy)
            return field_reply(request_id, Code::Busy);
        if (code == IndicatorCode::OutputFault)
            return field_reply(request_id, Code::ActivationFault);
        return field_reply(request_id, Code::InvalidRequest);
    }
    if (name == "field_status") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id",
                                "device_id"}) ||
            !controller_time_ || !indicator_)
            return field_reply(request_id, Code::InvalidRequest);
        const auto time_status = controller_time_->status();
        const auto indicator_status = indicator_->status(now_ms);
        return field_reply(
            request_id, Code::Ok,
            "\"time_source\":" + wtp::json::quote(source_name(time_status.source)) +
                ",\"time_age_ns\":\"" + std::to_string(time_status.age_ns) +
                "\",\"time_uncertainty_ns\":\"" +
                std::to_string(time_status.uncertainty_ns) +
                "\",\"time_disagreement\":" +
                (time_status.disagreement ? "true" : "false") +
                ",\"indicator\":" + wtp::json::quote(pattern_name(indicator_status.pattern)) +
                ",\"indicator_fault\":" +
                (indicator_status.output_fault ? "true" : "false"));
    }
    if (name == "time_challenge") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id",
                                "device_id", "nonce"}) ||
            !controller_time_)
            return field_reply(request_id, Code::InvalidRequest);
        const auto nonce = root->get("nonce");
        if (!nonce || nonce->type() != '"')
            return field_reply(request_id, Code::InvalidRequest);
        auto result = controller_time_->challenge(authorization.principal, session->string(),
                                                  device_id_, nonce->string());
        const auto code = time_code(result.code);
        if (code != Code::Ok)
            return field_reply(request_id, code);
        pending_time_nonce_ = result.nonce;
        return field_reply(request_id, Code::Ok,
                           "\"nonce\":" + wtp::json::quote(result.nonce) +
                               ",\"sampled_monotonic_ns\":\"" +
                               std::to_string(result.sampled_monotonic_ns) + "\"");
    }
    if (name == "time_submit") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id",
                                "device_id", "nonce", "utc_ns"}) ||
            !controller_time_)
            return field_reply(request_id, Code::InvalidRequest);
        const auto nonce = root->get("nonce");
        const auto utc = root->get("utc_ns");
        std::uint64_t utc_ns = 0;
        if (!nonce || nonce->type() != '"' || !utc || utc->type() != '"' ||
            !decimal(utc->string(), utc_ns))
            return field_reply(request_id, Code::InvalidRequest);
        const auto code = time_code(controller_time_->submit(
            authorization.principal, session->string(), device_id_, nonce->string(), utc_ns));
        return field_reply(request_id, code, code == Code::Ok ? "\"accepted\":true" : "");
    }
    return {};
}

CommandReply BleCommandSession::handle(std::string_view command, std::uint64_t now_ms) {
    if (!connected_ || command.empty() || command.size() > max_command_bytes)
        return {};
    const auto parsed = wtp::json::parse(command);
    const auto operation = parsed ? parsed->get("operation") : std::nullopt;
    if (operation && operation->type() == '"' && operation->string() == "authorize")
        return authorize(command, now_ms);
    if (operation && operation->type() == '"' &&
        (operation->string() == "identify" || operation->string() == "field_status" ||
         operation->string() == "time_challenge" || operation->string() == "time_submit"))
        return field_command(command, now_ms);
    const auto authorization = access_.ble_authorization();
    const auto activity = activity_ ? activity_(context_) : Activity{};
    auto response = command_.handle(command, authorization, activity, now_ms);
    if (response.code == Code::Ok && operation && operation->type() == '"' &&
        operation->string() == "apply" && parsed) {
        const auto request = parsed->get("request_id");
        if (request && wtp::json::identifier(*request)) {
            pending_apply_request_ = request->string();
            pending_apply_generation_ = manager_.status().generation;
        }
    }
    return response;
}

void BleCommandSession::response_delivered(std::uint64_t now_ms) {
    (void)now_ms;
    if (!pending_time_nonce_.empty()) {
        if (controller_time_)
            (void)controller_time_->challenge_delivered(
                principal(), field_session_, device_id_, pending_time_nonce_);
        secure_clear(pending_time_nonce_);
    }
    if (pending_apply_request_.empty())
        return;
    delivery_confirmed_ = true;
}

void BleCommandSession::poll(std::uint64_t now_ms) {
    if (delivery_confirmed_) {
        delivery_confirmed_ = false;
        (void)manager_.release_activation(pending_apply_request_, pending_apply_generation_, now_ms);
    }
    manager_.poll(now_ms);
    if (!pending_apply_request_.empty() &&
        manager_.status().activation.state != ActivationState::PendingDelivery) {
        secure_clear(pending_apply_request_);
        pending_apply_generation_ = 0;
    }
}
} // namespace wsprrypico::provisioning
