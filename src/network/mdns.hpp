#pragma once
#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::network {
// Portable owner of one certified hostname. All adapter calls run on core 0.
class MdnsAdapter {
  public:
    virtual ~MdnsAdapter() = default;
    virtual bool initialize() = 0;
    virtual bool add(std::string_view label) = 0;
    virtual void remove(bool goodbye) = 0;
};
class Mdns {
  public:
    Mdns(MdnsAdapter& adapter, std::string_view hostname);
    void poll(bool enabled, std::uint32_t address, std::uint64_t now_us);
    void name_result(bool success);
    void disable(bool link_usable);
    void retry();
    void identity_failure();
    void network_changed() {
        restart_ = true;
    }
    std::string_view state() const;
    const std::string& reason() const {
        return reason_;
    }
    const std::string& hostname() const {
        return hostname_;
    }
    std::string_view advertised() const;
    std::uint32_t registrations() const {
        return registrations_;
    }
    std::uint32_t conflicts() const {
        return conflicts_;
    }
    std::uint32_t failures() const {
        return failures_;
    }
    std::uint32_t address_changes() const {
        return address_changes_;
    }

  private:
    enum class State { Unconfigured, Waiting, Probing, Active, Conflict, Failed };
    void stop(bool goodbye);
    void fail(std::string_view reason);
    MdnsAdapter& adapter_;
    std::string hostname_, label_, reason_;
    State state_ = State::Unconfigured;
    bool initialized_ = false, registered_ = false, permanent_failure_ = false;
    bool pending_conflict_ = false;
    bool restart_ = false;
    std::uint32_t address_ = 0;
    std::uint64_t probe_started_us_ = 0;
    std::uint32_t registrations_ = 0, conflicts_ = 0, failures_ = 0, address_changes_ = 0;
};
} // namespace wsprrypico::network
