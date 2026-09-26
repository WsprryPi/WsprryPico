#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/udp.h"
#include "provisioning/pico/captive_dns.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

u32_t sys_now(void) {
    return 0;
}

static size_t question(uint8_t* bytes, uint16_t type) {
    static const uint8_t prefix[] = {0x12, 0x34, 1,   0,   0,   1,   0,   0,   0,   0, 0,
                                     0,    7,    'e', 'x', 'a', 'm', 'p', 'l', 'e', 0};
    memcpy(bytes, prefix, sizeof(prefix));
    bytes[sizeof(prefix)] = (uint8_t)(type >> 8);
    bytes[sizeof(prefix) + 1] = (uint8_t)type;
    bytes[sizeof(prefix) + 2] = 0;
    bytes[sizeof(prefix) + 3] = 1;
    return sizeof(prefix) + 4;
}

int main(void) {
    uint8_t request[512] = {0};
    uint8_t reply[512] = {0};
    ip_addr_t address;
    IP4_ADDR(ip_2_ip4(&address), 192, 168, 4, 1);
    size_t request_size = question(request, 1);
    size_t reply_size =
        wsprry_captive_dns_reply(request, request_size, &address, reply, sizeof(reply));
    assert(reply_size == request_size + 16);
    assert(reply[0] == 0x12 && reply[1] == 0x34);
    assert(reply[2] == 0x85 && reply[3] == 0);
    assert(reply[4] == 0 && reply[5] == 1 && reply[6] == 0 && reply[7] == 1);
    assert(memcmp(reply + request_size + 12, "\xc0\xa8\x04\x01", 4) == 0);

    request_size = question(request, 28);
    reply_size = wsprry_captive_dns_reply(request, request_size, &address, reply, sizeof(reply));
    assert(reply_size == request_size && reply[7] == 0);
    request[2] = 0x81;
    assert(wsprry_captive_dns_reply(request, request_size, &address, reply, sizeof(reply)) == 0);
    request_size = question(request, 1);
    request[12] = 0xc0; /* Do not follow compressed or cyclic question names. */
    assert(wsprry_captive_dns_reply(request, request_size, &address, reply, sizeof(reply)) == 0);
    request_size = question(request, 1);
    assert(wsprry_captive_dns_reply(request, request_size - 1, &address, reply, sizeof(reply)) ==
           0);
    assert(wsprry_captive_dns_reply(request, request_size, &address, reply, request_size) == 0);

    lwip_init();
    struct netif interface = {0};
    wsprry_captive_dns_t server = {0};
    assert(wsprry_captive_dns_init(&server, &interface, &address));
    assert(wsprry_captive_dns_ready(&server));
    wsprry_captive_dns_deinit(&server);
    assert(!wsprry_captive_dns_ready(&server));
    puts("captive DNS tests passed");
    return 0;
}
