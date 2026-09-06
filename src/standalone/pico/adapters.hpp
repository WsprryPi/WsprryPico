#pragma once
#include "lwip/udp.h"
#include "standalone/storage.hpp"
#include "time/sntp.hpp"

namespace wsprrypico::standalone {
class PicoFlash final : public Flash {
  public:
    bool read(std::size_t offset, std::span<std::uint8_t> data) override;
    bool erase(std::size_t sector_offset) override;
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override;
};
class PicoNetwork {
  public:
    explicit PicoNetwork(time::UtcDiscipline& clock) : sntp_(clock) {}
    bool start(const Config& config);
    void poll();

  private:
    static void receive(void* context, udp_pcb*, pbuf* packet, const ip_addr_t* address,
                        u16_t port);
    time::Sntp sntp_;
    udp_pcb* pcb_ = nullptr;
    ip_addr_t server_{};
    std::string ssid_, password_;
    std::uint64_t next_connect_us_ = 0, next_query_us_ = 0;
    bool initialized_ = false;
};
} // namespace wsprrypico::standalone
