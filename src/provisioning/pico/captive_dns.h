#pragma once

#include "lwip/ip_addr.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

struct netif;
struct udp_pcb;

typedef struct {
    ip_addr_t address;
    struct netif* interface;
    struct udp_pcb* udp;
} wsprry_captive_dns_t;

/* Used only by the blank, read-only SoftAP. Never bind this to the station netif. */
bool wsprry_captive_dns_init(wsprry_captive_dns_t* server, struct netif* interface,
                             const ip_addr_t* address);
void wsprry_captive_dns_deinit(wsprry_captive_dns_t* server);
bool wsprry_captive_dns_ready(const wsprry_captive_dns_t* server);

/* Packet-level entry point for deterministic parser and isolation tests. */
size_t wsprry_captive_dns_reply(const uint8_t* request, size_t request_size,
                                const ip_addr_t* address, uint8_t* reply, size_t reply_capacity);

#ifdef __cplusplus
}
#endif
