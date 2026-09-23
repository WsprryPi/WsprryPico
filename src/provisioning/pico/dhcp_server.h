/*
 * This file is derived from the MicroPython DHCP server carried by
 * raspberrypi/pico-examples.
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2018-2019 Damien P. George
 * Copyright (c) 2026 WsprryPico contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
#pragma once

#include "lwip/ip_addr.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WSPRRY_DHCPS_BASE_IP 16U
#define WSPRRY_DHCPS_MAX_IP 8U
#define WSPRRY_DHCPS_PACKET_CAPACITY 548U

typedef struct {
    uint8_t mac[6];
    uint32_t expiry_ms;
} wsprry_dhcp_lease_t;

typedef struct {
    ip_addr_t ip;
    ip_addr_t netmask;
    wsprry_dhcp_lease_t lease[WSPRRY_DHCPS_MAX_IP];
    struct udp_pcb* udp;
} wsprry_dhcp_server_t;

bool wsprry_dhcp_server_init(wsprry_dhcp_server_t* server, struct netif* interface,
                             const ip_addr_t* ip, const ip_addr_t* netmask);
void wsprry_dhcp_server_deinit(wsprry_dhcp_server_t* server);
bool wsprry_dhcp_server_ready(const wsprry_dhcp_server_t* server);

/* Packet-level entry point retained for deterministic hardware-free tests. */
size_t wsprry_dhcp_server_reply(wsprry_dhcp_server_t* server, const uint8_t* request,
                                size_t request_size, uint8_t* reply, size_t reply_capacity,
                                uint32_t now_ms);

#ifdef __cplusplus
}
#endif
