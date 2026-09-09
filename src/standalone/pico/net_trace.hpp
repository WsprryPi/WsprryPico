#pragma once
#include "lwip/netif.h"

#include <array>
#include <cstdint>
#include <string>

namespace wsprrypico::standalone {
// Single core, NO_SYS polling only. No allocation or pbuf retention in callbacks.
class NetTrace {
  public:
    static constexpr std::size_t capacity = 256;
    bool install(netif* interface);
    void mark(unsigned code);
    bool intact() const;
    std::string page(std::uint64_t after) const;

  private:
    struct Event {
        std::uint64_t sequence{}, us{}, end_us{};
        std::uint32_t generation{}, hash{};
        std::uint16_t length{};
        std::uint8_t kind{}, count{}, interface{};
        std::int16_t result{};
        std::array<std::uint8_t, 66> header{};
    };
    static err_t input(pbuf*, netif*);
    static err_t output(netif*, pbuf*);
    Event packet(pbuf*, unsigned kind) const;
    void append(Event event);
    static NetTrace* owner_;
    netif* interface_{};
    netif_input_fn input_{};
    netif_linkoutput_fn output_{};
    std::array<Event, capacity> events_{};
    std::uint64_t sequence_{};
    std::uint32_t generation_{}, install_errors_{};
};
} // namespace wsprrypico::standalone
