#pragma once
#include "lwip/udp.h"
#include "network/api.hpp"
#include "standalone/storage.hpp"
#include "time/sntp.hpp"

namespace wsprrypico::standalone {
class PicoFlash final : public Flash {
  public:
    bool read(std::size_t offset, std::span<std::uint8_t> data) override;
    bool erase(std::size_t sector_offset) override;
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override;
};
class PicoNetwork : public network::NetworkControl {
  public:
    explicit PicoNetwork(time::UtcDiscipline& clock) : sntp_(clock) {}
    bool start(const Config& config);
    void poll();
    bool set_enabled(bool enabled) override;
    bool request_enabled(bool enabled) override;
    void finish_request(bool idle) override;
    std::string status() const override;
    bool link_up() const;
    std::string ipv4() const;
    bool initialized() const {
        return initialized_;
    }
    void listener_status(bool configured, bool listening) {
        configured_ = configured;
        listening_ = listening;
    }

  private:
    static void receive(void* context, udp_pcb*, pbuf* packet, const ip_addr_t* address,
                        u16_t port);
    time::Sntp sntp_;
    time::SntpPollSchedule poll_schedule_;
    udp_pcb* pcb_ = nullptr;
    ip_addr_t server_{};
    std::string ssid_, password_;
    std::uint64_t next_connect_us_ = 0;
    bool initialized_ = false, enabled_ = true;
    std::optional<bool> pending_enabled_;
    bool configured_ = false, listening_ = false;
    std::uint32_t queries_ = 0, accepted_ = 0, rejected_ = 0;
};
} // namespace wsprrypico::standalone
