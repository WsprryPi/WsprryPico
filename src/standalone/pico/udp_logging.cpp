// SPDX-License-Identifier: MIT
#include "standalone/pico/udp_logging.hpp"

#include "lwip/ip4_addr.h"
#include "lwip/netif.h"
#include "lwip/pbuf.h"
#include "pico/cyw43_arch.h"
namespace wsprrypico::standalone {
void PicoUdpLogging::poll(logging::UdpSender& sender, std::uint64_t now, bool permitted,
                          std::uint64_t profile_generation) {
    auto* station = &cyw43_state.netif[CYW43_ITF_STA];
    const bool up = permitted && netif_is_up(station) && netif_is_link_up(station) &&
                    !ip4_addr_isany_val(*netif_ip4_addr(station));
    const std::array<std::uint32_t, 4> current = {netif_ip4_addr(station)->addr,
                                                  netif_ip4_netmask(station)->addr,
                                                  netif_ip4_gw(station)->addr, up ? 1U : 0U};
    if (context_ != current || profile_generation_ != profile_generation) {
        profile_generation_ = profile_generation;
        context_ = current;
        ++generation_;
        if (pcb_) {
            udp_remove(pcb_);
            pcb_ = nullptr;
        }
    }
    ip_addr_t destination{};
    const auto& settings = sender.settings();
    bool valid =
        up && settings.enabled && ipaddr_aton(settings.destination_ipv4.bytes.data(), &destination);
    if (valid) {
        for (auto* interface = netif_list; interface; interface = interface->next) {
            const auto ip = netif_ip4_addr(interface)->addr,
                       mask = netif_ip4_netmask(interface)->addr;
            const auto candidate = ip_2_ip4(&destination)->addr;
            if (candidate == ip || (ip && mask && candidate == (ip | ~mask)))
                valid = false;
        }
        // A link-local destination may not escape this station's own link.
        const auto value = lwip_ntohl(ip_2_ip4(&destination)->addr);
        if ((value & 0xffff0000U) == 0xa9fe0000U &&
            !ip4_addr_netcmp(ip_2_ip4(&destination), netif_ip4_addr(station),
                             netif_ip4_netmask(station)))
            valid = false;
    }
    sender.network(generation_, up, valid);
    if ((!valid || !settings.enabled) && pcb_) {
        udp_remove(pcb_);
        pcb_ = nullptr;
    }
    if (valid && !pcb_) {
        pcb_ = udp_new_ip_type(IPADDR_TYPE_V4);
        if (pcb_)
            udp_bind_netif(pcb_, station);
    }
    if (valid && !pcb_)
        sender.resource_unavailable();
    sender.poll(now, [&](std::string_view data) {
        if (!valid || !pcb_ || data.size() + 28 > station->mtu)
            return false;
        auto* packet = pbuf_alloc(PBUF_TRANSPORT, static_cast<u16_t>(data.size()), PBUF_POOL);
        if (!packet)
            return false;
        const bool copied =
            pbuf_take(packet, data.data(), static_cast<u16_t>(data.size())) == ERR_OK;
        const bool sent = copied && udp_sendto_if(pcb_, packet, &destination,
                                                  static_cast<u16_t>(settings.destination_port),
                                                  station) == ERR_OK;
        pbuf_free(packet);
        return sent;
    });
}
} // namespace wsprrypico::standalone
