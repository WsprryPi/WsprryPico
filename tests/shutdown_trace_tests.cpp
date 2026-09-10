#include "hardware/structs/watchdog.h"
#include "lwip/dhcp.h"
#include "lwip/igmp.h"
#include "pico/cyw43_arch.h"

#include <cassert>
#include <iostream>

static watchdog_hw_t hw{};
watchdog_hw_t* watchdog_hw = &hw;
static cyw43_t wifi{};
static netif station{};
static std::uint8_t address[6]{};
static bool observing;
static unsigned calls;
extern "C" {
void __wrap_cyw43_cb_tcpip_deinit(cyw43_t*, int);
void __wrap_dhcp_stop(netif*);
void __wrap_netif_remove(netif*);
err_t __wrap_igmp_stop(netif*);
int __wrap_cyw43_wifi_update_multicast_filter(cyw43_t*, std::uint8_t*, bool);
int __wrap_cyw43_wifi_leave(cyw43_t*, int);
void __real_dhcp_stop(netif* n) {
    assert(n == &station && hw.scratch[1] == (observing ? 21U : 13U));
    ++calls;
}
int __real_cyw43_wifi_update_multicast_filter(cyw43_t* self, std::uint8_t* mac, bool add) {
    assert(self == &wifi && mac == address && !add);
    assert(hw.scratch[1] == (observing ? 24U : 13U));
    ++calls;
    return -7;
}
err_t __real_igmp_stop(netif* n) {
    assert(n == &station && hw.scratch[1] == (observing ? 23U : 13U));
    assert(__wrap_cyw43_wifi_update_multicast_filter(&wifi, address, false) == -7);
    assert(hw.scratch[1] == (observing ? 23U : 13U));
    ++calls;
    return ERR_IF;
}
void __real_netif_remove(netif* n) {
    assert(n == &station && hw.scratch[1] == (observing ? 22U : 13U));
    assert(__wrap_igmp_stop(n) == ERR_IF);
    assert(hw.scratch[1] == (observing ? 22U : 13U));
    ++calls;
}
void __real_cyw43_cb_tcpip_deinit(cyw43_t* self, int itf) {
    assert(self == &wifi && itf == 0 && hw.scratch[1] == (observing ? 20U : 13U));
    __wrap_dhcp_stop(&station);
    assert(hw.scratch[1] == (observing ? 20U : 13U));
    __wrap_netif_remove(&station);
    assert(hw.scratch[1] == (observing ? 20U : 13U));
    ++calls;
}
int __real_cyw43_wifi_leave(cyw43_t* self, int itf) {
    assert(self == &wifi && itf == 0 && hw.scratch[1] == (observing ? 25U : 13U));
    ++calls;
    return -8;
}
}
int main() {
    for (bool active : {false, true}) {
        observing = active;
        hw.scratch[1] = active ? 16 : 13;
        __wrap_cyw43_cb_tcpip_deinit(&wifi, 0);
        assert(hw.scratch[1] == (active ? 16U : 13U));
        assert(__wrap_cyw43_wifi_leave(&wifi, 0) == -8);
        assert(hw.scratch[1] == (active ? 16U : 13U));
    }
    assert(calls == 12);
    std::cout << "Nested shutdown markers, arguments, results and enclosing restoration passed\n";
}
