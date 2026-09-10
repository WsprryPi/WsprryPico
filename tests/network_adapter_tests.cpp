// Actual PicoNetwork + pinned lwIP, with a delayed radio boundary. No hardware.
#include "hardware/structs/watchdog.h"
#include "lwip/apps/mdns_domain.h"
#include "lwip/igmp.h"
#include "lwip/init.h"
#include "lwip/ip.h"
#include "lwip/stats.h"
#include "lwip/timeouts.h"
#include "pico/cyw43_arch.h"
#include "standalone/pico/adapters.hpp"
#include "standalone/pico/mdns_lwip.h"

#include <array>
#include <cassert>
#include <iostream>
#include <optional>
#include <vector>

using wsprrypico::standalone::PicoNetwork;
cyw43_t cyw43_state{};
static watchdog_hw_t watchdog{};
watchdog_hw_t* watchdog_hw = &watchdog;
static std::uint64_t now_us;
static unsigned enables, disables, driver_polls, delivered_goodbyes, lost_goodbyes;
static bool power_failure;
static std::vector<std::array<unsigned char, 4>> positive_addresses;
static int mac_result;
static bool invalid_mac;
static int bssid_result;
static bool association_link_loss, invalid_bssid;
static unsigned bssid_queries;
static std::optional<std::uint64_t> queued_goodbye;
std::uint64_t time_us_64() {
    return now_us;
}
extern "C" u32_t sys_now() {
    return now_us / 1000;
}
static unsigned read16(const unsigned char* p) {
    return (p[0] << 8) | p[1];
}
static err_t output(netif*, pbuf* packet, const ip4_addr_t*) {
    std::vector<unsigned char> bytes(packet->tot_len);
    pbuf_copy_partial(packet, bytes.data(), bytes.size(), 0);
    assert(bytes.size() >= 20 && (bytes[0] >> 4) == 4);
    if (bytes[9] != 17)
        return ERR_OK;
    const unsigned udp = (bytes[0] & 15) * 4;
    assert(udp >= 20 && udp + 8 <= bytes.size());
    if (read16(bytes.data() + udp + 2) != 5353)
        return ERR_OK;
    const auto* dns = bytes.data() + udp + 8;
    const auto dns_size = bytes.size() - udp - 8;
    assert(dns_size >= 12);
    if (!(dns[2] & 0x80))
        return ERR_OK; // Queries/probes do not advertise an address.
    assert(read16(dns + 4) == 0);
    const auto records = read16(dns + 6) + read16(dns + 8) + read16(dns + 10);
    auto* message = pbuf_alloc(PBUF_RAW, dns_size, PBUF_RAM);
    assert(message && pbuf_take(message, dns, dns_size) == ERR_OK);
    unsigned offset = 12;
    bool goodbye = false;
    for (unsigned i = 0; i < records; ++i) {
        mdns_domain name{};
        const auto end = mdns_readname(message, offset, &name);
        assert(end != MDNS_READNAME_ERROR && end + 10 <= dns_size);
        const auto length = read16(dns + end + 8);
        assert(end + 10 + length <= dns_size);
        const bool positive = dns[end + 4] | dns[end + 5] | dns[end + 6] | dns[end + 7];
        if (read16(dns + end) == 1 && positive) {
            assert(length == 4 && read16(dns + end + 2) == 0x8001);
            positive_addresses.push_back(
                {dns[end + 10], dns[end + 11], dns[end + 12], dns[end + 13]});
        }
        goodbye |= !positive;
        offset = end + 10 + length;
    }
    assert(offset == dns_size);
    pbuf_free(message);
    if (goodbye) {
        assert(!queued_goodbye);
        queued_goodbye = now_us;
    }
    return ERR_OK; // Submitted to simulated radio, not delivered yet.
}
static err_t ethernet_output_stub(netif*, pbuf*) {
    return ERR_OK;
}
static err_t setup(netif* n) {
    n->linkoutput = ethernet_output_stub;
    n->name[0] = 'w';
    n->name[1] = '0';
    n->output = output;
    n->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_IGMP;
    n->mtu = 1500;
    return ERR_OK;
}
int cyw43_arch_init() {
    lwip_init();
    return 0;
}
void cyw43_arch_deinit() {}
void cyw43_arch_enable_sta_mode() {
    ++enables;
    ip4_addr_t address{}, mask{}, gateway{};
    IP4_ADDR(&mask, 255, 255, 255, 0);
    IP4_ADDR(&gateway, 192, 0, 2, 1);
    assert(netif_add(&cyw43_state.netif[0], &address, &mask, &gateway, nullptr, setup, ip_input));
    netif_set_default(&cyw43_state.netif[0]);
    netif_set_up(&cyw43_state.netif[0]);
}
void cyw43_arch_disable_sta_mode() {
    ++disables;
    if (queued_goodbye) {
        ++lost_goodbyes;
        queued_goodbye.reset();
    }
    netif_remove(&cyw43_state.netif[0]);
    cyw43_state.netif[0].flags = 0;
    ip4_addr_set_zero(ip_2_ip4(&cyw43_state.netif[0].ip_addr));
}
int cyw43_arch_wifi_connect_async(const char*, const char*, int) {
    ip4_addr_t address{};
    IP4_ADDR(&address, 192, 0, 2, 10);
    netif_set_ipaddr(&cyw43_state.netif[0], &address);
    netif_set_link_up(&cyw43_state.netif[0]);
    return 0;
}
int cyw43_tcpip_link_status(cyw43_t*, int) {
    return netif_is_up(&cyw43_state.netif[0]) && netif_is_link_up(&cyw43_state.netif[0]) ? 3 : 0;
}
int cyw43_wifi_pm(cyw43_t*, std::uint32_t) {
    return power_failure ? -1 : 0;
}
int cyw43_wifi_get_pm(cyw43_t*, std::uint32_t* pm) {
    *pm = 0;
    return 0;
}
int cyw43_wifi_get_mac(cyw43_t*, int interface, std::uint8_t* mac) {
    assert(interface == CYW43_ITF_STA);
    const std::uint8_t station[] = {0x88, 0xa2, 0x9e, 0x0a, 0x60, 0xdf};
    for (unsigned i = 0; i < 6; ++i)
        mac[i] = invalid_mac ? 0 : station[i];
    return mac_result;
}
int cyw43_wifi_get_bssid(cyw43_t* state, std::uint8_t* bssid) {
    assert(state == &cyw43_state && watchdog_hw->scratch[1] == 26);
    ++bssid_queries;
    const std::uint8_t ap[] = {0x42, 0x98, 0xb5, 0xfe, 0x36, 0xa1};
    for (unsigned i = 0; i < 6; ++i)
        bssid[i] = invalid_bssid ? 0 : ap[i];
    if (association_link_loss)
        netif_set_link_down(&cyw43_state.netif[0]);
    return bssid_result;
}
void cyw43_arch_poll() {
    ++driver_polls;
    sys_check_timeouts();
    if (queued_goodbye && now_us - *queued_goodbye >= 100'000) {
        // Delivery requires both station and multicast membership to remain alive.
        ip4_addr_t group;
        IP4_ADDR(&group, 224, 0, 0, 251);
        if (cyw43_tcpip_link_status(nullptr, 0) == 3 &&
            igmp_lookfor_group(&cyw43_state.netif[0], &group))
            ++delivered_goodbyes;
        else
            ++lost_goodbyes;
        queued_goodbye.reset();
    }
}
static void advance(PicoNetwork& network, unsigned us) {
    const auto end = now_us + us;
    while (now_us < end) {
        now_us += std::min<std::uint64_t>(1000, end - now_us);
        network.poll();
    }
}
static void active(PicoNetwork& network) {
    advance(network, 3'000'000);
    assert(network.status().find("\"mdns_state\":\"active\"") != std::string::npos);
}
int main(int argc, char** argv) {
    if (argc == 2) {
        const std::string mode(argv[1]);
        assert(mode == "mac-error" || mode == "mac-invalid");
        mac_result = mode == "mac-error" ? -1 : 0;
        invalid_mac = mode == "mac-invalid";
    }
    wsprrypico::time::UtcDiscipline clock([](void*) { return now_us * 1000; }, nullptr);
    PicoNetwork network(clock, "pico-a.local");
    wsprrypico::standalone::Config config;
    config.ntp_ipv4 = "192.0.2.1";
    assert(!network.set_enabled(false));
    assert(network.association().find("not_connected") != std::string::npos);
    assert(bssid_queries == 0);
    assert(network.status().find("\"stable_hostname\":\"\"") != std::string::npos);
    assert(network.start(config));
    if (argc == 2) {
        assert(network.status().find("\"station_mac\":\"\"") != std::string::npos);
        assert(network.status().find("\"stable_hostname\":\"\"") != std::string::npos);
        return 0;
    }
    assert(network.status().find("\"station_mac\":\"88:a2:9e:0a:60:df\"") != std::string::npos);
    assert(network.status().find("\"stable_hostname\":\"wsprrypico-0a60df.local\"") !=
           std::string::npos);
    assert(network.status().find("\"configured_hostname\":\"pico-a.local\"") != std::string::npos);
    network.listener_status(true, true);
    // OFF before association/probing needs no drain.
    assert(network.set_enabled(false) && disables == 1);
    assert(network.set_enabled(true));
    active(network);
    watchdog_hw->scratch[1] = 5;
    assert(network.association() == "{\"valid\":true,\"bssid\":\"42:98:b5:fe:36:a1\"}");
    assert(watchdog_hw->scratch[1] == 5);
    bssid_result = -7;
    assert(network.association().find("\"code\":-7") != std::string::npos);
    assert(watchdog_hw->scratch[1] == 5);
    bssid_result = 0;
    invalid_bssid = true;
    assert(network.association().find("invalid_bssid") != std::string::npos);
    invalid_bssid = false;
    association_link_loss = true;
    assert(network.association().find("link_changed") != std::string::npos);
    association_link_loss = false;
    assert(network.association().find("not_connected") != std::string::npos);
    netif_set_link_up(&cyw43_state.netif[0]);
    const auto queries_before_status = bssid_queries;
    (void)network.status();
    assert((bssid_queries == queries_before_status));
    assert(network.trace_page(0).find("\"install_errors\":0") != std::string::npos);
    assert(network.trace_page(0).find("\"intact\":true") != std::string::npos);
    // D1 composition: an address event must reach the actual adapter state
    // machine and reprobe automatically, without manually rebuilding mDNS.
    active(network);
    const auto radio_disables = disables;
    const auto expect_address = [&](unsigned char last) {
        const std::array<unsigned char, 4> expected{192, 0, 2, last};
        assert(!positive_addresses.empty());
        for (const auto& address : positive_addresses)
            assert(address == expected);
        assert(network.status().find("\"advertised_hostname\":\"pico-a.local\"") !=
               std::string::npos);
        assert(network.status().find("\"configured_hostname\":\"pico-a.local\"") !=
               std::string::npos);
        assert(disables == radio_disables);
    };
    positive_addresses.clear();
    ip4_addr_t changed_address{};
    IP4_ADDR(&changed_address, 192, 0, 2, 11);
    netif_set_ipaddr(&cyw43_state.netif[0], &changed_address);
    network.poll();
    assert(network.status().find("\"mdns_state\":\"probing\"") != std::string::npos);
    assert(network.status().find("\"advertised_hostname\":\"\"") != std::string::npos);
    assert(network.status().find("\"mdns_address_changes\":1,") != std::string::npos);
    active(network);
    expect_address(11);
    positive_addresses.clear();
    ip4_addr_set_zero(&changed_address);
    netif_set_ipaddr(&cyw43_state.netif[0], &changed_address);
    network.poll();
    assert(network.status().find("\"mdns_state\":\"waiting_address\"") != std::string::npos);
    advance(network, 3'000'000);
    assert(positive_addresses.empty());
    IP4_ADDR(&changed_address, 192, 0, 2, 12);
    netif_set_ipaddr(&cyw43_state.netif[0], &changed_address);
    active(network);
    expect_address(12);
    const auto before = now_us;
    const auto down = disables;
    const auto polls = driver_polls;
    assert(network.set_enabled(false));
    assert(now_us == before && disables == down && queued_goodbye && !network.link_up());
    assert(network.status().find("\"withdrawal_pending\":true") != std::string::npos);
    assert(network.status().find("\"mdns_state\":\"withdrawing\"") != std::string::npos);
    advance(network, 100'000);
    assert(delivered_goodbyes == 1 && !lost_goodbyes && driver_polls > polls);
    // Duplicate OFF neither resends nor extends the deadline.
    assert(network.set_enabled(false));
    advance(network, 899'999);
    assert(disables == down);
    advance(network, 1);
    assert(disables == down + 1);
    const auto clean_heap = lwip_stats.mem.used;
    const auto clean_timers = lwip_stats.memp[MEMP_SYS_TIMEOUT]->used;
    assert(network.set_enabled(true));
    active(network);
    // ON during withdrawal waits for the original deadline, then recreates/probes.
    const auto up = enables;
    assert(network.set_enabled(false));
    advance(network, 100'000);
    assert(network.set_enabled(true) && enables == up);
    advance(network, 899'999);
    assert(enables == up);
    advance(network, 1);
    assert(enables == up + 1);
    active(network);
    assert(network.set_enabled(false));
    assert(network.set_enabled(true));
    assert(network.set_enabled(false));
    advance(network, 1'000'000);
    assert(!network.link_up() && enables == up + 1);
    // Cancelled HTTP changes never start withdrawal; accepted changes use the same path.
    assert(network.set_enabled(true));
    active(network);
    assert(network.request_enabled(false));
    network.finish_request(false);
    assert(network.link_up());
    assert(network.request_enabled(false));
    network.finish_request(true);
    assert(!network.link_up());
    advance(network, 1'000'000);
    // Unexpected link loss ends drain without pretending delivery.
    assert(network.set_enabled(true));
    active(network);
    assert(network.set_enabled(false));
    const auto lost_down = disables;
    netif_set_link_down(&cyw43_state.netif[0]);
    network.poll();
    assert(disables == lost_down + 1 && !network.link_up());
    const auto expected_lost = lost_goodbyes;
    for (unsigned i = 0; i < 50; ++i) {
        assert(network.set_enabled(true));
        active(network);
        assert(network.set_enabled(false));
        advance(network, 1'000'000);
        assert(lwip_stats.mem.used == clean_heap);
        assert(lwip_stats.memp[MEMP_SYS_TIMEOUT]->used == clean_timers);
    }
    assert(lost_goodbyes == expected_lost);
    assert((bssid_queries == queries_before_status));
    power_failure = true;
    assert(!network.set_enabled(true) && !network.link_up());
    assert(network.status().find("\"withdrawal_pending\":false") != std::string::npos);
    std::cout << "actual network lifecycle: nonblocking drain, rapid toggles, idle cancellation, "
                 "link loss, 50 resource-stable cycles and enable failure passed\n";
}
