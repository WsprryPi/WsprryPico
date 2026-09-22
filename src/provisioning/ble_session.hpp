#pragma once

#include "provisioning/command.hpp"
#include "provisioning/local_access.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
class BleCommandSession {
  public:
    using ActivitySource = Activity (*)(void*);
    BleCommandSession(LocalAccessController& access, CommandAdapter& command, Manager& manager,
                      std::string device_id, ActivitySource activity, void* context)
        : access_(access), command_(command), manager_(manager), device_id_(std::move(device_id)),
          activity_(activity), context_(context) {}
    bool connected(std::uint64_t peer, bool encrypted, bool new_pairing,
                   std::string link_session, std::uint64_t now_ms);
    void disconnected();
    CommandReply handle(std::string_view command, std::uint64_t now_ms);
    void response_delivered(std::uint64_t now_ms);
    void poll(std::uint64_t now_ms);
    bool authorized() const;
    bool available() const {
        return access_.ble_available();
    }
    bool pairing_allowed(std::uint64_t now_ms) const {
        return access_.enrollment_open(now_ms);
    }

  private:
    CommandReply authorize(std::string_view command, std::uint64_t now_ms);
    LocalAccessController& access_;
    CommandAdapter& command_;
    Manager& manager_;
    std::string device_id_;
    ActivitySource activity_;
    void* context_;
    std::string pending_apply_request_;
    std::uint64_t pending_apply_generation_ = 0;
    bool connected_ = false;
    bool delivery_confirmed_ = false;
};
} // namespace wsprrypico::provisioning
