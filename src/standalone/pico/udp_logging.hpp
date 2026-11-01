// SPDX-License-Identifier: MIT
#pragma once
#include "logging/udp_sender.hpp"
#include "lwip/udp.h"
namespace wsprrypico::standalone {
class PicoUdpLogging {
  public:
    void poll(logging::UdpSender& sender, std::uint64_t now, bool permitted,
              std::uint64_t profile_generation = 0);

  private:
    udp_pcb* pcb_ = nullptr;
    std::array<std::uint32_t, 4> context_{};
    std::uint64_t generation_ = 0, profile_generation_ = UINT64_MAX;
};
} // namespace wsprrypico::standalone
