#pragma once
#include "lwip/netif.h"

#include <cstdint>
struct cyw43_t {
    struct netif netif[1];
};
extern cyw43_t cyw43_state;
constexpr int CYW43_ITF_STA = 0, CYW43_LINK_UP = 3, CYW43_AUTH_WPA2_AES_PSK = 1;
constexpr int CYW43_NONE_PM = 0, CYW43_NO_POWERSAVE_MODE = 0;
int cyw43_arch_init();
void cyw43_arch_deinit();
void cyw43_arch_enable_sta_mode();
void cyw43_arch_disable_sta_mode();
void cyw43_arch_poll();
int cyw43_tcpip_link_status(cyw43_t*, int);
int cyw43_arch_wifi_connect_async(const char*, const char*, int);
int cyw43_wifi_pm(cyw43_t*, std::uint32_t);
int cyw43_wifi_get_pm(cyw43_t*, std::uint32_t*);
int cyw43_wifi_get_mac(cyw43_t*, int, std::uint8_t*);
int cyw43_wifi_get_bssid(cyw43_t*, std::uint8_t*);
