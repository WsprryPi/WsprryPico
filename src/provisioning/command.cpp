#include "provisioning/command.hpp"

#include "network/identity.hpp"
#include "wtp/json.hpp"

#include <limits>
#include <optional>
#include <vector>

namespace wsprrypico::provisioning {
namespace {
using wtp::json::Value;

void secure_clear(std::vector<std::uint8_t>& value) {
    volatile std::uint8_t* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::vector<std::uint8_t>().swap(value);
}

void secure_clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string().swap(value);
}

std::optional<std::vector<std::uint8_t>> reject_fragment(std::vector<std::uint8_t>& partial) {
    secure_clear(partial);
    return {};
}

bool integer(Value value, std::uint64_t& output) {
    if (value.type() < '0' || value.type() > '9')
        return false;
    const auto parsed = value.integer();
    if (parsed < 0 || static_cast<std::uint64_t>(parsed) > max_wire_integer)
        return false;
    output = static_cast<std::uint64_t>(parsed);
    return true;
}

int base64_digit(char value) {
    if (value >= 'A' && value <= 'Z')
        return value - 'A';
    if (value >= 'a' && value <= 'z')
        return value - 'a' + 26;
    if (value >= '0' && value <= '9')
        return value - '0' + 52;
    if (value == '+')
        return 62;
    if (value == '/')
        return 63;
    return -1;
}

std::optional<std::vector<std::uint8_t>> decode_fragment(std::string_view input) {
    if (input.empty() || input.size() % 4 || input.size() > 88)
        return {};
    std::vector<std::uint8_t> output;
    output.reserve(input.size() / 4 * 3);
    for (std::size_t offset = 0; offset < input.size(); offset += 4) {
        const bool last = offset + 4 == input.size();
        const int a = base64_digit(input[offset]);
        const int b = base64_digit(input[offset + 1]);
        const int c = input[offset + 2] == '=' ? -2 : base64_digit(input[offset + 2]);
        const int d = input[offset + 3] == '=' ? -2 : base64_digit(input[offset + 3]);
        if (a < 0 || b < 0 || c == -1 || d == -1 || (!last && (c == -2 || d == -2)) ||
            (c == -2 && d != -2) || (c == -2 && (b & 15)) || (d == -2 && c >= 0 && (c & 3)))
            return reject_fragment(output);
        output.push_back(static_cast<std::uint8_t>((a << 2) | (b >> 4)));
        if (c >= 0) {
            output.push_back(static_cast<std::uint8_t>((b << 4) | (c >> 2)));
            if (d >= 0)
                output.push_back(static_cast<std::uint8_t>((c << 6) | d));
        }
    }
    if (output.empty() || output.size() > max_fragment_bytes)
        return reject_fragment(output);
    return output;
}

bool identifier(const std::optional<Value>& value) {
    return value && value->raw.size() == 34 && wtp::json::identifier(*value);
}

bool boolean(const std::optional<Value>& value) {
    return value && (value->type() == 't' || value->type() == 'f');
}

Result invalid(const Manager& manager, Code code = Code::InvalidRequest) {
    return {code, manager.status().generation};
}
} // namespace

std::string_view code_name(Code code) {
    switch (code) {
    case Code::Ok:
        return "ok";
    case Code::InvalidRequest:
        return "invalid_request";
    case Code::AuthenticationRequired:
        return "authentication_required";
    case Code::WrongDevice:
        return "wrong_device";
    case Code::SessionBusy:
        return "session_busy";
    case Code::SessionNotFound:
        return "session_not_found";
    case Code::OutOfOrder:
        return "out_of_order";
    case Code::Incomplete:
        return "incomplete";
    case Code::Oversize:
        return "oversize";
    case Code::Malformed:
        return "malformed";
    case Code::CredentialInvalid:
        return "credential_invalid";
    case Code::Conflict:
        return "conflict";
    case Code::Busy:
        return "busy";
    case Code::Replay:
        return "replay";
    case Code::Timeout:
        return "timeout";
    case Code::StorageFault:
        return "storage_fault";
    case Code::ActivationFault:
        return "activation_fault";
    }
    return "invalid_request";
}

std::string CommandAdapter::identity() const {
    const auto generation = manager_.status().generation;
    if (!network::valid_device_id(device_id_) || generation > max_wire_integer)
        return {};
    return "{\"device_id\":" + wtp::json::quote(device_id_) +
           ",\"generation\":" + std::to_string(generation) + "}";
}

CommandReply CommandAdapter::reply(std::string_view request_id, Result result) const {
    std::string notification = "{\"version\":1,\"request_id\":" + wtp::json::quote(request_id) +
                               ",\"ok\":" + (result.ok() ? "true" : "false");
    if (!result.ok())
        notification += ",\"error\":" + wtp::json::quote(code_name(result.code));
    notification += ",\"generation\":" + std::to_string(result.generation) +
                    ",\"accepted_bytes\":" + std::to_string(result.accepted_bytes) +
                    ",\"replayed\":" + (result.replayed ? "true" : "false") + "}";
    return {result.code, std::move(notification)};
}

CommandReply CommandAdapter::handle(std::string_view command, const Authorization& authorization,
                                    const Activity& activity, std::uint64_t now_ms) {
    if (command.empty() || command.size() > max_command_bytes)
        return {};
    const auto root = wtp::json::parse(command);
    if (!root)
        return {};
    const auto request_value = root->get("request_id");
    if (!identifier(request_value))
        return {};
    const auto request_id = request_value->string();
    if (command.find(static_cast<char>(92)) != std::string_view::npos)
        return reply(request_id, invalid(manager_));
    const auto version_value = root->get("version");
    const auto operation_value = root->get("operation");
    const auto session_value = root->get("session_id");
    const auto device_value = root->get("device_id");
    const auto common_valid = version_value && version_value->type() == '1' &&
                              version_value->integer() == 1 && operation_value &&
                              operation_value->type() == '"' && identifier(session_value) &&
                              identifier(device_value);
    if (!common_valid)
        return reply(request_id, invalid(manager_));
    const auto operation = operation_value->string();
    const auto session_id = session_value->string();
    const auto requested_device = device_value->string();
    if (requested_device != device_id_ || !network::valid_device_id(device_id_))
        return reply(request_id, invalid(manager_, Code::WrongDevice));

    Result result;
    if (operation == "open") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id", "device_id"}))
            result = invalid(manager_);
        else
            result = manager_.open(request_id, session_id, requested_device, transport_,
                                   authorization, now_ms);
    } else if (operation == "write") {
        const auto offset_value = root->get("offset");
        const auto final_value = root->get("final");
        const auto payload_value = root->get("payload");
        std::uint64_t offset = 0;
        if (!wtp::json::fields(*root, {"version", "operation", "request_id", "session_id",
                                       "device_id", "offset", "final", "payload"}) ||
            !offset_value || !integer(*offset_value, offset) ||
            offset > std::numeric_limits<std::size_t>::max() || !boolean(final_value) ||
            !payload_value || payload_value->type() != '"') {
            result = invalid(manager_);
        } else {
            auto encoded = payload_value->string();
            auto decoded = decode_fragment(encoded);
            secure_clear(encoded);
            if (!decoded)
                result = invalid(manager_);
            else {
                result = manager_.write(request_id, session_id, static_cast<std::size_t>(offset),
                                        *decoded, final_value->boolean(), transport_, authorization,
                                        now_ms);
                secure_clear(*decoded);
            }
        }
    } else if (operation == "apply") {
        const auto generation_value = root->get("expected_generation");
        std::uint64_t generation = 0;
        if (!wtp::json::fields(*root, {"version", "operation", "request_id", "session_id",
                                       "device_id", "expected_generation"}) ||
            !generation_value || !integer(*generation_value, generation))
            result = invalid(manager_);
        else
            result = manager_.apply(request_id, session_id, generation, activity, transport_,
                                    authorization, now_ms);
    } else if (operation == "cancel") {
        if (!wtp::json::fields(*root,
                               {"version", "operation", "request_id", "session_id", "device_id"}))
            result = invalid(manager_);
        else
            result = manager_.cancel(request_id, session_id, transport_, authorization, now_ms);
    } else
        result = invalid(manager_);
    return reply(request_id, result);
}
} // namespace wsprrypico::provisioning
