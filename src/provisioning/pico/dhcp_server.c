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

#include "provisioning/pico/dhcp_server.h"

#include "lwip/netif.h"
#include "lwip/sys.h"
#include "lwip/timeouts.h"
#include "lwip/udp.h"

#include <errno.h>
#include <stddef.h>
#include <string.h>

enum {
    boot_request = 1,
    boot_reply = 2,
    dhcp_discover = 1,
    dhcp_offer = 2,
    dhcp_request = 3,
    dhcp_ack = 5,
    dhcp_option_pad = 0,
    dhcp_option_subnet_mask = 1,
    dhcp_option_router = 3,
    dhcp_option_requested_ip = 50,
    dhcp_option_lease_time = 51,
    dhcp_option_message_type = 53,
    dhcp_option_server_id = 54,
    dhcp_option_end = 255,
    dhcp_server_port = 67,
    dhcp_client_port = 68,
    dhcp_minimum_size = 243,
    dhcp_offer_hold_ms = 60 * 1000,
    dhcp_lease_seconds = 24 * 60 * 60,
    ethernet_hardware_type = 1,
    ethernet_address_size = 6,
};

static const uint8_t dhcp_magic_cookie[4] = {99, 130, 83, 99};

typedef struct {
    uint8_t op;
    uint8_t hardware_type;
    uint8_t hardware_length;
    uint8_t hops;
    uint32_t transaction_id;
    uint16_t seconds;
    uint16_t flags;
    uint8_t client_ip[4];
    uint8_t offered_ip[4];
    uint8_t server_ip[4];
    uint8_t relay_ip[4];
    uint8_t client_hardware[16];
    uint8_t server_name[64];
    uint8_t boot_file[128];
    uint8_t options[312];
} dhcp_message_t;

typedef struct {
    const uint8_t* data;
    size_t size;
} option_value_t;

static bool elapsed(uint32_t now_ms, uint32_t expiry_ms) {
    return expiry_ms != 0U && (int32_t)(now_ms - expiry_ms) >= 0;
}

static option_value_t find_option(const uint8_t* options, size_t size, uint8_t code) {
    size_t offset = 0;
    while (offset < size) {
        const uint8_t current = options[offset++];
        if (current == dhcp_option_end)
            break;
        if (current == dhcp_option_pad)
            continue;
        if (offset >= size)
            return (option_value_t){0};
        const size_t length = options[offset++];
        if (length > size - offset)
            return (option_value_t){0};
        if (current == code)
            return (option_value_t){options + offset, length};
        offset += length;
    }
    return (option_value_t){0};
}

static bool append_option(uint8_t** output, const uint8_t* end, uint8_t code, const void* value,
                          size_t size) {
    if (size > 255U || (size_t)(end - *output) < size + 2U)
        return false;
    *(*output)++ = code;
    *(*output)++ = (uint8_t)size;
    memcpy(*output, value, size);
    *output += size;
    return true;
}

static bool append_u8(uint8_t** output, const uint8_t* end, uint8_t code, uint8_t value) {
    return append_option(output, end, code, &value, sizeof(value));
}

static bool append_u32(uint8_t** output, const uint8_t* end, uint8_t code, uint32_t value) {
    const uint8_t bytes[4] = {(uint8_t)(value >> 24), (uint8_t)(value >> 16), (uint8_t)(value >> 8),
                              (uint8_t)value};
    return append_option(output, end, code, bytes, sizeof(bytes));
}

static int select_lease(wsprry_dhcp_server_t* server, const uint8_t* mac, uint32_t now_ms) {
    int available = -1;
    static const uint8_t empty[ethernet_address_size] = {0};
    for (unsigned index = 0; index < WSPRRY_DHCPS_MAX_IP; ++index) {
        wsprry_dhcp_lease_t* lease = &server->lease[index];
        if (memcmp(lease->mac, mac, sizeof(lease->mac)) == 0 &&
            memcmp(lease->mac, empty, sizeof(lease->mac)) != 0)
            return (int)index;
        if (elapsed(now_ms, lease->expiry_ms)) {
            memset(lease, 0, sizeof(*lease));
        }
        if (available < 0 && memcmp(lease->mac, empty, sizeof(lease->mac)) == 0)
            available = (int)index;
    }
    return available;
}

size_t wsprry_dhcp_server_reply(wsprry_dhcp_server_t* server, const uint8_t* request,
                                size_t request_size, uint8_t* reply, size_t reply_capacity,
                                uint32_t now_ms) {
    if (server == NULL || request == NULL || reply == NULL || request_size < dhcp_minimum_size ||
        request_size > sizeof(dhcp_message_t) || reply_capacity < sizeof(dhcp_message_t))
        return 0;

    dhcp_message_t input = {0};
    memcpy(&input, request, request_size);
    const size_t options_size = request_size - offsetof(dhcp_message_t, options);
    if (input.op != boot_request || input.hardware_type != ethernet_hardware_type ||
        input.hardware_length != ethernet_address_size || options_size < 7U ||
        memcmp(input.options, dhcp_magic_cookie, sizeof(dhcp_magic_cookie)) != 0)
        return 0;

    const uint8_t* options = input.options + sizeof(dhcp_magic_cookie);
    const size_t option_bytes = options_size - sizeof(dhcp_magic_cookie);
    const option_value_t message_type =
        find_option(options, option_bytes, dhcp_option_message_type);
    if (message_type.size != 1U)
        return 0;

    const int lease_index = select_lease(server, input.client_hardware, now_ms);
    if (lease_index < 0)
        return 0;

    uint8_t response_type = 0;
    if (message_type.data[0] == dhcp_discover) {
        memcpy(server->lease[lease_index].mac, input.client_hardware,
               sizeof(server->lease[lease_index].mac));
        server->lease[lease_index].expiry_ms = now_ms + dhcp_offer_hold_ms;
        response_type = dhcp_offer;
    } else if (message_type.data[0] == dhcp_request) {
        const option_value_t requested =
            find_option(options, option_bytes, dhcp_option_requested_ip);
        const option_value_t requested_server =
            find_option(options, option_bytes, dhcp_option_server_id);
        const uint8_t* server_bytes = (const uint8_t*)&ip4_addr_get_u32(ip_2_ip4(&server->ip));
        const uint8_t* requested_ip = requested.data;
        if (requested.size == 0U && memcmp(input.client_ip, "\0\0\0\0", 4U) != 0) {
            requested_ip = input.client_ip;
        } else if (requested.size != 4U) {
            return 0;
        }
        if (requested_server.size != 0U &&
            (requested_server.size != 4U || memcmp(requested_server.data, server_bytes, 4U) != 0))
            return 0;
        const uint8_t expected_host = (uint8_t)(WSPRRY_DHCPS_BASE_IP + (unsigned)lease_index);
        if (memcmp(requested_ip, server_bytes, 3U) != 0 || requested_ip[3] != expected_host)
            return 0;
        memcpy(server->lease[lease_index].mac, input.client_hardware,
               sizeof(server->lease[lease_index].mac));
        server->lease[lease_index].expiry_ms = now_ms + dhcp_lease_seconds * 1000U;
        response_type = dhcp_ack;
    } else {
        return 0;
    }

    dhcp_message_t output = {0};
    output.op = boot_reply;
    output.hardware_type = input.hardware_type;
    output.hardware_length = input.hardware_length;
    output.transaction_id = input.transaction_id;
    output.seconds = input.seconds;
    output.flags = input.flags;
    memcpy(output.client_hardware, input.client_hardware, sizeof(output.client_hardware));
    memcpy(output.offered_ip, &ip4_addr_get_u32(ip_2_ip4(&server->ip)), 4U);
    output.offered_ip[3] = (uint8_t)(WSPRRY_DHCPS_BASE_IP + (unsigned)lease_index);
    memcpy(output.options, dhcp_magic_cookie, sizeof(dhcp_magic_cookie));

    uint8_t* option = output.options + sizeof(dhcp_magic_cookie);
    const uint8_t* const end = (const uint8_t*)&output + sizeof(output);
    if (!append_u8(&option, end, dhcp_option_message_type, response_type) ||
        !append_option(&option, end, dhcp_option_server_id,
                       &ip4_addr_get_u32(ip_2_ip4(&server->ip)), 4U) ||
        !append_option(&option, end, dhcp_option_subnet_mask,
                       &ip4_addr_get_u32(ip_2_ip4(&server->netmask)), 4U) ||
        !append_option(&option, end, dhcp_option_router, &ip4_addr_get_u32(ip_2_ip4(&server->ip)),
                       4U) ||
        !append_u32(&option, end, dhcp_option_lease_time, dhcp_lease_seconds) || option >= end)
        return 0;
    *option++ = dhcp_option_end;
    const size_t reply_size = (size_t)(option - (uint8_t*)&output);
    memcpy(reply, &output, reply_size);
    return reply_size;
}

static void receive(void* argument, struct udp_pcb* pcb, struct pbuf* packet,
                    const ip_addr_t* source, u16_t source_port) {
    (void)pcb;
    (void)source;
    (void)source_port;
    wsprry_dhcp_server_t* server = argument;
    uint8_t request[WSPRRY_DHCPS_PACKET_CAPACITY];
    uint8_t reply[WSPRRY_DHCPS_PACKET_CAPACITY];
    if (packet->tot_len <= sizeof(request)) {
        const size_t copied = pbuf_copy_partial(packet, request, packet->tot_len, 0);
        const size_t reply_size =
            wsprry_dhcp_server_reply(server, request, copied, reply, sizeof(reply), sys_now());
        if (reply_size != 0U) {
            struct pbuf* response = pbuf_alloc(PBUF_TRANSPORT, (u16_t)reply_size, PBUF_RAM);
            if (response != NULL) {
                if (pbuf_take(response, reply, reply_size) == ERR_OK) {
                    const ip_addr_t broadcast = IPADDR4_INIT(PP_HTONL(IPADDR_BROADCAST));
                    struct netif* interface = ip_current_input_netif();
                    if (interface != NULL)
                        (void)udp_sendto_if(server->udp, response, &broadcast, dhcp_client_port,
                                            interface);
                }
                pbuf_free(response);
            }
        }
    }
    pbuf_free(packet);
}

bool wsprry_dhcp_server_init(wsprry_dhcp_server_t* server, struct netif* interface,
                             const ip_addr_t* ip, const ip_addr_t* netmask) {
    if (server == NULL || interface == NULL || ip == NULL || netmask == NULL || server->udp != NULL)
        return false;
    ip_addr_copy(server->ip, *ip);
    ip_addr_copy(server->netmask, *netmask);
    memset(server->lease, 0, sizeof(server->lease));
    server->udp = udp_new();
    if (server->udp == NULL)
        return false;
    if (udp_bind(server->udp, IP_ANY_TYPE, dhcp_server_port) != ERR_OK) {
        udp_remove(server->udp);
        server->udp = NULL;
        return false;
    }
    udp_bind_netif(server->udp, interface);
    udp_recv(server->udp, receive, server);
    return true;
}

void wsprry_dhcp_server_deinit(wsprry_dhcp_server_t* server) {
    if (server != NULL && server->udp != NULL) {
        udp_remove(server->udp);
        server->udp = NULL;
    }
}

bool wsprry_dhcp_server_ready(const wsprry_dhcp_server_t* server) {
    return server != NULL && server->udp != NULL;
}
