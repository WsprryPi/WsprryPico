#include "lwip/def.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/udp.h"
#include "provisioning/pico/dhcp_server.h"

#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum {
    message_type_option = 53,
    requested_ip_option = 50,
    option_end = 255,
    discover = 1,
    offer = 2,
    request = 3,
    acknowledge = 5,
};

u32_t sys_now(void) {
    return 0;
}

static size_t make_request(uint8_t* packet, size_t capacity, uint8_t type, const uint8_t mac[6],
                           uint8_t requested_host) {
    assert(capacity >= WSPRRY_DHCPS_PACKET_CAPACITY);
    memset(packet, 0, capacity);
    packet[0] = 1;
    packet[1] = 1;
    packet[2] = 6;
    packet[4] = 0x12;
    packet[5] = 0x34;
    packet[6] = 0x56;
    packet[7] = 0x78;
    memcpy(packet + 28, mac, 6);
    uint8_t* option = packet + 236;
    const uint8_t cookie[4] = {99, 130, 83, 99};
    memcpy(option, cookie, sizeof(cookie));
    option += sizeof(cookie);
    *option++ = message_type_option;
    *option++ = 1;
    *option++ = type;
    if (requested_host != 0U) {
        *option++ = requested_ip_option;
        *option++ = 4;
        *option++ = 192;
        *option++ = 168;
        *option++ = 4;
        *option++ = requested_host;
    }
    *option++ = option_end;
    return (size_t)(option - packet);
}

static uint8_t reply_type(const uint8_t* packet, size_t size) {
    for (size_t offset = 240; offset + 2 < size && packet[offset] != option_end;) {
        if (packet[offset] == 0) {
            ++offset;
            continue;
        }
        const size_t length = packet[offset + 1];
        assert(offset + 2 + length <= size);
        if (packet[offset] == message_type_option) {
            assert(length == 1);
            return packet[offset + 2];
        }
        offset += 2 + length;
    }
    return 0;
}

static wsprry_dhcp_server_t server(void) {
    wsprry_dhcp_server_t result = {0};
    IP4_ADDR(ip_2_ip4(&result.ip), 192, 168, 4, 1);
    IP4_ADDR(ip_2_ip4(&result.netmask), 255, 255, 255, 0);
    return result;
}

int main(void) {
    _Static_assert(MEMP_NUM_UDP_PCB == 5, "firmware must reserve station and AP DHCP PCBs");
    const uint8_t first_mac[6] = {0x02, 0, 0, 0, 0, 1};
    uint8_t input[WSPRRY_DHCPS_PACKET_CAPACITY];
    uint8_t output[WSPRRY_DHCPS_PACKET_CAPACITY];
    wsprry_dhcp_server_t state = server();

    size_t input_size = make_request(input, sizeof(input), discover, first_mac, 0);
    size_t output_size =
        wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 1000);
    assert(output_size > 240);
    assert(output[0] == 2);
    assert(memcmp(output + 4, input + 4, 4) == 0);
    assert(memcmp(output + 16, "\xc0\xa8\x04\x10", 4) == 0);
    assert(reply_type(output, output_size) == offer);

    const uint8_t concurrent_mac[6] = {0x02, 0, 0, 0, 0, 2};
    input_size = make_request(input, sizeof(input), discover, concurrent_mac, 0);
    output_size = wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 1000);
    assert(output_size > 240);
    assert(output[19] == 17);

    input_size = make_request(input, sizeof(input), request, first_mac, 16);
    output_size = wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 1001);
    assert(output_size > 240);
    assert(reply_type(output, output_size) == acknowledge);
    assert(memcmp(state.lease[0].mac, first_mac, sizeof(first_mac)) == 0);

    input_size = make_request(input, sizeof(input), request, first_mac, 0);
    memcpy(input + 12, "\xc0\xa8\x04\x10", 4);
    output_size = wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 1002);
    assert(output_size > 240);
    assert(reply_type(output, output_size) == acknowledge);

    input_size = make_request(input, sizeof(input), request, concurrent_mac, 17);
    assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 1002) > 240);

    for (unsigned index = 2; index < WSPRRY_DHCPS_MAX_IP; ++index) {
        uint8_t mac[6] = {0x02, 0, 0, 0, 0, (uint8_t)(index + 1)};
        input_size = make_request(input, sizeof(input), discover, mac, 0);
        output_size = wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output),
                                               1002 + index);
        assert(output_size > 240);
        assert(output[19] == WSPRRY_DHCPS_BASE_IP + index);
        input_size = make_request(input, sizeof(input), request, mac,
                                  (uint8_t)(WSPRRY_DHCPS_BASE_IP + index));
        assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output),
                                        2000 + index) > 240);
    }

    const uint8_t ninth_mac[6] = {0x02, 0, 0, 0, 0, 9};
    input_size = make_request(input, sizeof(input), discover, ninth_mac, 0);
    assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 3000) == 0);
    assert(wsprry_dhcp_server_reply(&state, input, 242, output, sizeof(output), 3000) == 0);

    state = server();
    input_size = make_request(input, sizeof(input), discover, first_mac, 0);
    input[240] = message_type_option;
    input[241] = 250;
    assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 0) == 0);
    input_size = make_request(input, sizeof(input), request, first_mac, 99);
    assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 0) == 0);
    input_size = make_request(input, sizeof(input), discover, first_mac, 0);
    input[236] = 0;
    assert(wsprry_dhcp_server_reply(&state, input, input_size, output, sizeof(output), 0) == 0);

    lwip_init();
    struct udp_pcb* occupied[MEMP_NUM_UDP_PCB - 1];
    for (size_t index = 0; index < MEMP_NUM_UDP_PCB - 1; ++index) {
        occupied[index] = udp_new();
        assert(occupied[index] != NULL);
    }
    struct netif interface = {0};
    interface.num = 0;
    state = server();
    assert(wsprry_dhcp_server_init(&state, &interface, &state.ip, &state.netmask));
    assert(wsprry_dhcp_server_ready(&state));
    assert(udp_new() == NULL);
    wsprry_dhcp_server_deinit(&state);
    assert(!wsprry_dhcp_server_ready(&state));
    for (size_t index = 0; index < MEMP_NUM_UDP_PCB - 1; ++index)
        udp_remove(occupied[index]);

    puts("dhcp server tests passed");
    return 0;
}
