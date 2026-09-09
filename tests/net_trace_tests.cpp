#include "lwip/init.h"
#include "standalone/pico/net_trace.hpp"
#include "wtp/json.hpp"

#include <cassert>
#include <iostream>
#include <vector>
using wsprrypico::standalone::NetTrace;
static std::uint64_t tick = 100;
std::uint64_t time_us_64() {
    return tick++;
}
extern "C" u32_t sys_now() {
    return tick / 1000;
}
static unsigned calls;
static err_t tx(netif*, pbuf*) {
    ++calls;
    return ERR_IF;
}
static err_t rx(pbuf* p, netif*) {
    ++calls;
    pbuf_free(p);
    return ERR_OK;
}
static pbuf* packet(const std::vector<std::uint8_t>& b, bool chain = false) {
    auto* p = pbuf_alloc(PBUF_RAW, chain ? 9 : b.size(), PBUF_RAM);
    if (chain) {
        auto* tail = pbuf_alloc(PBUF_RAW, b.size() - 9, PBUF_RAM);
        pbuf_cat(p, tail);
    }
    assert(pbuf_take(p, b.data(), b.size()) == ERR_OK);
    return p;
}
int main() {
    lwip_init();
    NetTrace trace;
    netif n{};
    assert(!trace.install(&n));
    n.input = rx;
    n.linkoutput = tx;
    assert(trace.install(&n));
    assert(trace.install(&n)); // Idempotent; must not recurse.
    std::vector<std::uint8_t> arp(42);
    arp[12] = 8;
    arp[13] = 6;
    arp[21] = 1;
    auto* p = packet(arp, true);
    assert(n.linkoutput(&n, p) == ERR_IF && calls == 1);
    assert(p->tot_len == arp.size()); // TX ownership unchanged.
    pbuf_free(p);
    assert(n.input(packet(arp, true), &n) == ERR_OK && calls == 2); // Callback consumes RX.
    auto page = trace.page(0);
    assert(page.find("\"result\":-12") != std::string::npos);
    assert(page.find("\"kind\":1") != std::string::npos);
    assert(page.find("\"latest\":3") != std::string::npos);
    assert(trace.page(0) == page); // Reads cannot lose data on USB retransmission.
    std::vector<std::uint8_t> dns(54);
    dns[12] = 8;
    dns[14] = 0x45;
    dns[17] = 40;
    dns[23] = 17;
    dns[36] = 0x14;
    dns[37] = 0xe9;
    dns[39] = 20;
    p = packet(dns, true);
    n.linkoutput(&n, p);
    pbuf_free(p);
    assert(trace.page(3).find("\"hash\":0,") == std::string::npos);
    dns.resize(43); // Claimed UDP payload extends beyond received bytes.
    p = packet(dns);
    n.linkoutput(&n, p);
    pbuf_free(p);
    assert(trace.page(3).find("\"latest\":4") != std::string::npos);
    p = packet(std::vector<std::uint8_t>(5));
    n.linkoutput(&n, p);
    pbuf_free(p);
    assert(trace.page(3).find("\"latest\":4") != std::string::npos);
    n.input = rx;
    n.linkoutput = tx; // Station netif recreated in same storage.
    assert(!trace.intact());
    assert(trace.install(&n));
    p = packet(arp);
    n.linkoutput(&n, p);
    pbuf_free(p);
    assert(trace.page(4).find("\"generation\":2") != std::string::npos);
    for (unsigned i = 0; i < 300; ++i)
        trace.mark(4);
    page = trace.page(0);
    assert(page.find("\"oldest\":51") != std::string::npos);
    assert(page.find("\"overwritten\":50") != std::string::npos);
    assert(page.size() < 8192);
    assert(trace.page(UINT64_MAX).find("\"events\":[]") != std::string::npos);
    // Exercise malformed lengths/options/fragments across chained pbuf boundaries.
    std::uint32_t random = 1;
    for (unsigned size = 1; size <= 1518; ++size) {
        std::vector<std::uint8_t> bytes(size);
        for (auto& b : bytes) {
            random = random * 1664525U + 1013904223U;
            b = random >> 24;
        }
        if (size >= 14) {
            bytes[12] = 8;
            bytes[13] = size % 2 ? 0 : 6;
        }
        auto* malformed = packet(bytes, size > 9);
        const auto count = calls;
        assert(n.linkoutput(&n, malformed) == ERR_IF && calls == count + 1);
        pbuf_free(malformed);
    }
    std::cout << "NET_TRACE_PASS\n";
}
