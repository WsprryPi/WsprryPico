#include "provisioning/pico/captive_dns.h"

#include "lwip/netif.h"
#include "lwip/udp.h"

#include <string.h>

enum { dns_header_size = 12, dns_port = 53, dns_packet_capacity = 512 };

size_t wsprry_captive_dns_reply(const uint8_t* request, size_t request_size,
                                const ip_addr_t* address, uint8_t* reply, size_t reply_capacity) {
    if (request == NULL || address == NULL || reply == NULL || !IP_IS_V4(address) ||
        request_size < dns_header_size + 5U || request_size > dns_packet_capacity)
        return 0;
    /* One ordinary uncompressed question, no response, opcode or truncation bits. */
    if ((request[2] & 0xfaU) != 0U || request[4] != 0U || request[5] != 1U)
        return 0;
    size_t offset = dns_header_size;
    size_t name_size = 0;
    for (;;) {
        if (offset >= request_size)
            return 0;
        const uint8_t label_size = request[offset++];
        if (label_size == 0U)
            break;
        if (label_size > 63U || label_size > request_size - offset ||
            name_size + label_size + 1U > 253U)
            return 0;
        offset += label_size;
        name_size += label_size + 1U;
    }
    if (name_size == 0U || request_size - offset < 4U)
        return 0;
    const size_t question_end = offset + 4U;
    const bool answer_a = request[offset] == 0U && request[offset + 1U] == 1U &&
                          request[offset + 2U] == 0U && request[offset + 3U] == 1U;
    const size_t response_size = question_end + (answer_a ? 16U : 0U);
    if (response_size > reply_capacity)
        return 0;
    memcpy(reply, request, question_end);
    reply[2] = (uint8_t)(0x84U | (request[2] & 1U)); /* response, authoritative, RD echo */
    reply[3] = 0U;
    reply[6] = 0U;
    reply[7] = answer_a ? 1U : 0U;
    memset(reply + 8U, 0, 4U); /* authority and additional sections omitted */
    if (answer_a) {
        uint8_t* answer = reply + question_end;
        const uint8_t header[12] = {0xc0, 0x0c, 0, 1, 0, 1, 0, 0, 0, 2, 0, 4};
        memcpy(answer, header, sizeof(header));
        memcpy(answer + sizeof(header), &ip4_addr_get_u32(ip_2_ip4(address)), 4U);
    }
    return response_size;
}

static void receive(void* argument, struct udp_pcb* pcb, struct pbuf* packet,
                    const ip_addr_t* source, u16_t source_port) {
    wsprry_captive_dns_t* server = argument;
    uint8_t request[dns_packet_capacity];
    uint8_t reply[dns_packet_capacity];
    if (packet != NULL && ip_current_input_netif() == server->interface &&
        packet->tot_len <= sizeof(request)) {
        const size_t copied = pbuf_copy_partial(packet, request, packet->tot_len, 0);
        const size_t reply_size =
            wsprry_captive_dns_reply(request, copied, &server->address, reply, sizeof(reply));
        if (reply_size != 0U) {
            struct pbuf* response = pbuf_alloc(PBUF_TRANSPORT, (u16_t)reply_size, PBUF_RAM);
            if (response != NULL) {
                if (pbuf_take(response, reply, reply_size) == ERR_OK)
                    (void)udp_sendto_if(pcb, response, source, source_port,
                                        ip_current_input_netif());
                pbuf_free(response);
            }
        }
    }
    if (packet != NULL)
        pbuf_free(packet);
}

bool wsprry_captive_dns_init(wsprry_captive_dns_t* server, struct netif* interface,
                             const ip_addr_t* address) {
    if (server == NULL || interface == NULL || address == NULL || !IP_IS_V4(address) ||
        server->udp != NULL)
        return false;
    ip_addr_copy(server->address, *address);
    server->interface = interface;
    server->udp = udp_new();
    if (server->udp == NULL)
        return false;
    if (udp_bind(server->udp, address, dns_port) != ERR_OK) {
        udp_remove(server->udp);
        server->udp = NULL;
        return false;
    }
    udp_bind_netif(server->udp, interface);
    udp_recv(server->udp, receive, server);
    return true;
}

void wsprry_captive_dns_deinit(wsprry_captive_dns_t* server) {
    if (server != NULL && server->udp != NULL) {
        udp_remove(server->udp);
        server->udp = NULL;
    }
}

bool wsprry_captive_dns_ready(const wsprry_captive_dns_t* server) {
    return server != NULL && server->udp != NULL;
}
