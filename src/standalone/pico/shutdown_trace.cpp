// Link-time wrappers around immutable SDK/lwIP shutdown calls. Standard inhibited
// image only; single-core polling. Scratch markers survive watchdog reset.
#include "hardware/structs/watchdog.h"
#include "lwip/dhcp.h"
#include "lwip/igmp.h"
#include "lwip/netif.h"
#include "pico/cyw43_arch.h"

#include <cstdint>

namespace {
class Marker {
  public:
    explicit Marker(unsigned stage) : saved_(watchdog_hw->scratch[1]) {
        active_ = saved_ == 16 || (saved_ >= 20 && saved_ <= 25);
        if (active_)
            watchdog_hw->scratch[1] = stage;
    }
    ~Marker() {
        if (active_)
            watchdog_hw->scratch[1] = saved_;
    }

  private:
    unsigned saved_;
    bool active_;
};
} // namespace
extern "C" {
void __real_cyw43_cb_tcpip_deinit(cyw43_t*, int);
void __real_dhcp_stop(netif*);
void __real_netif_remove(netif*);
err_t __real_igmp_stop(netif*);
int __real_cyw43_wifi_update_multicast_filter(cyw43_t*, std::uint8_t*, bool);
int __real_cyw43_wifi_leave(cyw43_t*, int);

void __wrap_cyw43_cb_tcpip_deinit(cyw43_t* self, int interface) {
    Marker marker(20);
    __real_cyw43_cb_tcpip_deinit(self, interface);
}
void __wrap_dhcp_stop(netif* interface) {
    Marker marker(21);
    __real_dhcp_stop(interface);
}
void __wrap_netif_remove(netif* interface) {
    Marker marker(22);
    __real_netif_remove(interface);
}
err_t __wrap_igmp_stop(netif* interface) {
    Marker marker(23);
    return __real_igmp_stop(interface);
}
int __wrap_cyw43_wifi_update_multicast_filter(cyw43_t* self, std::uint8_t* address, bool add) {
    Marker marker(24);
    return __real_cyw43_wifi_update_multicast_filter(self, address, add);
}
int __wrap_cyw43_wifi_leave(cyw43_t* self, int interface) {
    Marker marker(25);
    return __real_cyw43_wifi_leave(self, interface);
}
}
