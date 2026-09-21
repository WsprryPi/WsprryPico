#pragma once

#include "provisioning/manager.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::provisioning {
inline constexpr std::size_t max_command_bytes = 512;
inline constexpr std::size_t max_notification_bytes = 256;
inline constexpr std::size_t max_fragment_bytes = 64;
inline constexpr std::uint64_t max_wire_integer = 2147483647;

struct CommandReply {
    Code code = Code::InvalidRequest;
    std::string notification;
    bool notify() const {
        return !notification.empty();
    }
};

// Strict transport-neutral decoder for the repository-owned Bluefy command
// vocabulary. Authentication remains the responsibility of the target adapter.
class CommandAdapter {
  public:
    CommandAdapter(Manager& manager, std::string device_id, Transport transport)
        : manager_(manager), device_id_(std::move(device_id)), transport_(transport) {}
    std::string identity() const;
    CommandReply handle(std::string_view command, const Authorization& authorization,
                        const Activity& activity, std::uint64_t now_ms);

  private:
    CommandReply reply(std::string_view request_id, Result result) const;
    Manager& manager_;
    std::string device_id_;
    Transport transport_;
};

std::string_view code_name(Code code);
} // namespace wsprrypico::provisioning
