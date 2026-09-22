#include "provisioning/ble_session.hpp"

#include "wtp/json.hpp"

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
} // namespace

bool BleCommandSession::connected(std::uint64_t peer, bool encrypted, bool new_pairing,
                                  std::string link_session, std::uint64_t now_ms) {
    const auto admitted = access_.ble_connect(peer, encrypted, new_pairing,
                                              std::move(link_session), now_ms);
    connected_ = admitted.code == AccessCode::Ok;
    return connected_;
}

void BleCommandSession::disconnected() {
    if (connected_)
        (void)access_.ble_disconnect();
    connected_ = false;
    secure_clear(pending_apply_request_);
    pending_apply_generation_ = 0;
}

bool BleCommandSession::authorized() const {
    return connected_ && access_.ble_authorization().authenticated;
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
    const auto code = valid_local_password(password)
                          ? access_.ble_authorize(password, now_ms).code
                          : AccessCode::AuthenticationRequired;
    secure_clear(password);
    return reply(request_id, code, manager_.status().generation);
}

CommandReply BleCommandSession::handle(std::string_view command, std::uint64_t now_ms) {
    if (!connected_ || command.empty() || command.size() > max_command_bytes)
        return {};
    const auto parsed = wtp::json::parse(command);
    const auto operation = parsed ? parsed->get("operation") : std::nullopt;
    if (operation && operation->type() == '"' && operation->string() == "authorize")
        return authorize(command, now_ms);
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
    if (pending_apply_request_.empty())
        return;
    (void)manager_.release_activation(pending_apply_request_, pending_apply_generation_, now_ms);
    secure_clear(pending_apply_request_);
    pending_apply_generation_ = 0;
}
} // namespace wsprrypico::provisioning
