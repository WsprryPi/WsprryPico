// Deterministic real lwIP responder/packet tests. No sockets or LAN traffic.
#include "lwip/apps/mdns_domain.h"
#include "lwip/apps/mdns_priv.h"
#include "lwip/igmp.h"
#include "lwip/init.h"
#include "lwip/ip.h"
#include "lwip/mem.h"
#include "lwip/stats.h"
#include "lwip/timeouts.h"
#include "lwip/udp.h"
#include "standalone/pico/mdns_lwip.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static u32_t now_ms;
static unsigned successes, conflicts, packets, answers, zero_ttl;
static unsigned char last_address[4];
static unsigned char dns_packet[1500];
static size_t dns_size;
u32_t sys_now(void) {
    return now_ms;
}
static unsigned read16(const unsigned char* p) {
    return ((unsigned)p[0] << 8) | p[1];
}
static void put16(unsigned char* p, unsigned n) {
    p[0] = n >> 8;
    p[1] = n;
}
static void result(struct netif* interface, u8_t outcome, s8_t slot) {
    (void)interface;
    assert(slot == 0);
    if (outcome == MDNS_PROBING_SUCCESSFUL)
        ++successes;
    else
        ++conflicts;
}
static err_t output(struct netif* interface, struct pbuf* p, const ip4_addr_t* dest) {
    unsigned char bytes[1600];
    unsigned offset, count, i;
    (void)interface;
    (void)dest;
    assert(p->tot_len <= sizeof(bytes));
    pbuf_copy_partial(p, bytes, p->tot_len, 0);
    if (bytes[9] != 17)
        return ERR_OK; // IGMP belongs to the actual stack too.
    offset = (bytes[0] & 15) * 4;
    if (read16(bytes + offset + 2) != 5353)
        return ERR_OK;
    assert(bytes[8] == 255); // RFC multicast IP TTL.
    offset += 8;
    dns_size = p->tot_len - offset;
    memcpy(dns_packet, bytes + offset, dns_size);
    ++packets;
    count = read16(dns_packet + 6);
    if (!count)
        return ERR_OK; // probes are exercised but have no answer section.
    assert((dns_packet[2] & 0x84) == 0x84);
    offset = 12;
    for (i = 0; i < count; ++i) {
        struct mdns_domain domain;
        struct pbuf* dns = pbuf_alloc(PBUF_RAW, dns_size, PBUF_RAM);
        unsigned end, type, length;
        assert(dns);
        pbuf_take(dns, dns_packet, dns_size);
        end = mdns_readname(dns, offset, &domain);
        pbuf_free(dns);
        assert(end != MDNS_READNAME_ERROR && end + 10 <= dns_size);
        type = read16(dns_packet + end);
        length = read16(dns_packet + end + 8);
        assert(end + 10 + length <= dns_size);
        if (type == 1) {
            assert(length == 4);
            assert(read16(dns_packet + end + 2) & 0x8000); // Cache flush.
            memcpy(last_address, dns_packet + end + 10, 4);
            ++answers;
        }
        if (!(dns_packet[end + 4] | dns_packet[end + 5] | dns_packet[end + 6] |
              dns_packet[end + 7]))
            ++zero_ttl;
        offset = end + 10 + length;
    }
    return ERR_OK;
}
static err_t setup(struct netif* interface) {
    interface->name[0] = 't';
    interface->name[1] = 's';
    interface->output = output;
    interface->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_IGMP;
    interface->mtu = 1500;
    return ERR_OK;
}
static void advance(unsigned ms) {
    unsigned until = now_ms + ms;
    while (now_ms < until) {
        now_ms += 10;
        sys_check_timeouts();
    }
}
static void receive(struct netif* interface, const unsigned char* bytes, unsigned size) {
    struct udp_pcb* pcb = get_mdns_pcb();
    struct pbuf* packet = pbuf_alloc(PBUF_RAW, size, PBUF_RAM);
    assert(packet);
    pbuf_take(packet, bytes, size);
    packet->if_idx = netif_get_index(interface);
    ip_data.current_netif = interface;
    ip_data.current_input_netif = interface;
    IP_ADDR4(&ip_data.current_iphdr_src, 192, 0, 2, 200);
    IP_ADDR4(&ip_data.current_iphdr_dest, 224, 0, 0, 251);
    pcb->recv(pcb->recv_arg, pcb, packet, &ip_data.current_iphdr_src, 5353);
    ip_data.current_netif = NULL;
    ip_data.current_input_netif = NULL;
}
static unsigned query(unsigned char* data, int truncated) {
    static const unsigned char name[] = {6, 'p', 'i', 'c', 'o', '-', 'a',
                                         5, 'l', 'o', 'c', 'a', 'l', 0};
    memset(data, 0, 64);
    data[2] = truncated ? 2 : 0;
    data[5] = 1;
    memcpy(data + 12, name, sizeof(name));
    put16(data + 12 + sizeof(name), 1);
    put16(data + 14 + sizeof(name), 1);
    return 16 + sizeof(name);
}
int main(void) {
    struct netif interface;
    ip4_addr_t address, mask, gateway, group1, group2;
    struct udp_pcb* pcbs[MEMP_NUM_UDP_PCB];
    unsigned char data[1500];
    unsigned i, count, before, memory, timeout_count;
    void* allocations[512];
    lwip_init();
    IP4_ADDR(&address, 192, 0, 2, 10);
    IP4_ADDR(&mask, 255, 255, 255, 0);
    IP4_ADDR(&gateway, 192, 0, 2, 1);
    assert(netif_add(&interface, &address, &mask, &gateway, NULL, setup, ip_input));
    netif_set_default(&interface);
    netif_set_up(&interface);
    netif_set_link_up(&interface);
    // PCB exhaustion and bind conflict unwind, then initialization is idempotent.
    for (i = 0; i < MEMP_NUM_UDP_PCB; ++i) {
        pcbs[i] = udp_new();
        assert(pcbs[i]);
    }
    assert(wsprry_mdns_init(result) == ERR_MEM);
    for (i = 0; i < MEMP_NUM_UDP_PCB; ++i)
        udp_remove(pcbs[i]);
    pcbs[0] = udp_new();
    assert(udp_bind(pcbs[0], IP_ANY_TYPE, 5353) == ERR_OK);
    assert(wsprry_mdns_init(result) == ERR_USE);
    udp_remove(pcbs[0]);
    assert(wsprry_mdns_init(result) == ERR_OK);
    assert(wsprry_mdns_init(result) == ERR_OK);
    assert(lwip_stats.memp[MEMP_UDP_PCB]->used == 1);
    // Partial helper/IGMP membership failures must restore heap and netif state.
    count = 0;
    while (count < 512 && (allocations[count] = mem_malloc(64)))
        ++count;
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_MEM);
    while (count)
        mem_free(allocations[--count]);
    memory = lwip_stats.mem.used;
    IP4_ADDR(&group1, 224, 0, 0, 252);
    IP4_ADDR(&group2, 224, 0, 0, 253);
    assert(igmp_joingroup_netif(&interface, &group1) == ERR_OK);
    assert(igmp_joingroup_netif(&interface, &group2) == ERR_OK);
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_MEM);
    assert(!mdns_resp_netif_active(&interface) && lwip_stats.mem.used == memory);
    igmp_leavegroup_netif(&interface, &group1);
    igmp_leavegroup_netif(&interface, &group2);
    // Exclude deliberate startup heap exhaustion from normal responder highwater.
    lwip_stats.mem.max = lwip_stats.mem.used;
    timeout_count = lwip_stats.memp[MEMP_SYS_TIMEOUT]->used;
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
    advance(5000);
    assert(successes == 1 && answers >= 2 && last_address[3] == 10);
    // Truncated questions retain bounded packets; delayed reply/cooldown and TC
    // timers are all canceled on removal before their target helper is freed.
    count = query(data, 1);
    receive(&interface, data, count);
    receive(&interface, data, count);
    receive(&interface, data, count);
    before = packets;
    wsprry_mdns_remove(&interface, 1);
    assert(zero_ttl == 2 && wsprry_mdns_goodbye_attempts() == 1);
    assert(lwip_stats.mem.used == memory);
    assert(lwip_stats.memp[MEMP_SYS_TIMEOUT]->used == timeout_count);
    before = packets;
    advance(31000);
    assert(packets == before);
    // Address replacement quiesces immediately and fresh probing announces new A.
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
    advance(5000);
    IP4_ADDR(&address, 192, 0, 2, 11);
    netif_set_ipaddr(&interface, &address);
    assert(wsprry_mdns_network_changed());
    before = packets;
    advance(2000);
    assert(before == packets);
    wsprry_mdns_remove(&interface, 0);
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
    advance(5000);
    assert(last_address[3] == 11);
    // Established conflicting A response exercises upstream parsing and latches.
    count = query(data, 0);
    data[2] = 0x84;
    data[5] = 0;
    data[7] = 1;
    put16(data + count - 2, 0x8001); // class
    memset(data + count, 0, 10);
    data[count + 3] = 120;
    put16(data + count + 4, 4);
    data[count + 6] = 192;
    data[count + 7] = 0;
    data[count + 8] = 2;
    data[count + 9] = 99;
    receive(&interface, data, count + 10);
    assert(conflicts == 1);
    before = packets;
    advance(2000);
    assert(packets == before);
    wsprry_mdns_remove(&interface, 0);
    // A conflicting response during probing also uses the upstream callback.
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
    advance(300);
    receive(&interface, data, count + 10);
    assert(conflicts == 2);
    before = packets;
    advance(2000);
    assert(packets == before);
    wsprry_mdns_remove(&interface, 0);
    // Invalid names, short records, cyclic compression, huge counts and bounded
    // deterministic malformed bytes traverse the actual upstream responder.
    assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
    advance(5000);
    for (i = 0; i < 12; ++i) {
        memset(data, 0, sizeof(data));
        receive(&interface, data, i);
    }
    memset(data, 0, sizeof(data));
    data[5] = 1;
    data[12] = 0xc0;
    data[13] = 12;
    receive(&interface, data, 18);
    memset(data, 255, sizeof(data));
    receive(&interface, data, 1473);
    assert(wsprry_mdns_rejected_packets());
    for (i = 0; i < 1000; ++i) {
        unsigned j, size = 12 + i % 180;
        memset(data, 0, sizeof(data));
        for (j = 12; j < size; ++j)
            data[j] = (unsigned char)(i * 29 + j * 53);
        data[5] = 1;
        receive(&interface, data, size);
    }
    netif_set_link_down(&interface);
    assert(wsprry_mdns_network_changed());
    wsprry_mdns_remove(&interface, 1);
    assert(wsprry_mdns_goodbye_attempts() == 1);
    netif_set_link_up(&interface);
    for (i = 0; i < 100; ++i) {
        assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
        advance(2000);
        count = query(data, 1);
        receive(&interface, data, count);
        wsprry_mdns_remove(&interface, 0);
        advance(600);
        assert(lwip_stats.mem.used == memory);
        assert(lwip_stats.memp[MEMP_SYS_TIMEOUT]->used == timeout_count);
    }
    // CYW43 disable removes its station netif; re-enable recreates it with a
    // fresh index, while the responder's boot-long PCB/client ID stay reserved.
    for (i = 0; i < 10; ++i) {
        netif_remove(&interface);
        assert(netif_add(&interface, &address, &mask, &gateway, NULL, setup, ip_input));
        netif_set_default(&interface);
        netif_set_up(&interface);
        netif_set_link_up(&interface);
        assert(wsprry_mdns_add(&interface, "pico-a") == ERR_OK);
        advance(2000);
        count = query(data, 1);
        receive(&interface, data, count);
        wsprry_mdns_remove(&interface, 1);
        assert(lwip_stats.mem.used == memory);
        assert(lwip_stats.memp[MEMP_SYS_TIMEOUT]->used == timeout_count);
    }
    printf("actual pinned lwIP mDNS passed: host=%zu packet=%zu, heap peak=%u, timers peak=%u, "
           "UDP=%u\n",
           wsprry_mdns_host_bytes(), wsprry_mdns_packet_bytes(), lwip_stats.mem.max,
           lwip_stats.memp[MEMP_SYS_TIMEOUT]->max, lwip_stats.memp[MEMP_UDP_PCB]->used);
    return 0;
}
