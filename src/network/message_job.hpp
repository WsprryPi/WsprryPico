#pragma once
#include "encoding/message_wire.hpp"
namespace wsprrypico::network {
inline std::optional<encoding::MorseMessage> decode_message_job(wtp::json::Value body) {
    return encoding::decode_message(body);
}
} // namespace wsprrypico::network
