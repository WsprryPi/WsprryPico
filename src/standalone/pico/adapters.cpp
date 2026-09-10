#include "standalone/pico/adapters.hpp"

#include "hardware/flash.h"
#include "hardware/structs/watchdog.h"
#include "hardware/sync.h"
#include "lwip/dns.h"
#include "lwip/netif.h"
#include "lwip/stats.h"
#include "network/identity.hpp"
#include "pico/cyw43_arch.h"
#include "pico/rand.h"
#include "pico/time.h"
#include "standalone/pico/mdns_lwip.h"
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "pico/flash.h"
#endif
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace wsprrypico::standalone {
namespace {
constexpr std::size_t storage_size = 16 * 1024;
// RP2350-E10 boot workaround occupies the final physical flash page. Keep
// its entire erase sector outside both journals.
constexpr std::size_t flash_base = PICO_FLASH_SIZE_BYTES - 4096 - storage_size;
static_assert(PICO_FLASH_SIZE_BYTES == 4 * 1024 * 1024);
static_assert(MEM_ALIGNMENT >= alignof(std::uint32_t));
PicoNetwork* mdns_owner = nullptr;
std::string memory_stats(const stats_mem* value) {
    if (!value)
        return "null";
    return "{\"used\":" + std::to_string(value->used) +
           ",\"capacity\":" + std::to_string(value->avail) +
           ",\"peak\":" + std::to_string(value->max) + ",\"errors\":" + std::to_string(value->err) +
           "}";
}
std::string packet_stats(const stats_proto& value) {
    return "{\"received\":" + std::to_string(value.recv) +
           ",\"sent\":" + std::to_string(value.xmit) +
           ",\"dropped\":" + std::to_string(value.drop) + "}";
}
std::string network_memory() {
    return "{\"heap\":" + memory_stats(&lwip_stats.mem) +
           ",\"tcp_pcbs\":" + memory_stats(lwip_stats.memp[MEMP_TCP_PCB]) +
           ",\"tcp_segments\":" + memory_stats(lwip_stats.memp[MEMP_TCP_SEG]) +
           ",\"packet_pool\":" + memory_stats(lwip_stats.memp[MEMP_PBUF_POOL]) + "}";
}
} // namespace
bool PicoFlash::read(std::size_t offset, std::span<std::uint8_t> data) {
    if (offset > storage_size || data.size() > storage_size - offset)
        return false;
    std::memcpy(data.data(), reinterpret_cast<const void*>(XIP_BASE + flash_base + offset),
                data.size());
    return true;
}
bool PicoFlash::erase(std::size_t offset) {
    if (offset % FLASH_SECTOR_SIZE || offset > storage_size - FLASH_SECTOR_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    // Authority excludes Armed/Running and unknown output before entering here.
    auto erase = [](void* argument) {
        flash_range_erase(flash_base + *static_cast<std::size_t*>(argument), FLASH_SECTOR_SIZE);
    };
    if (flash_safe_execute(erase, &offset, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_erase(flash_base + offset, FLASH_SECTOR_SIZE);
    restore_interrupts(irq);
#endif
    const auto* bytes = reinterpret_cast<const std::uint8_t*>(XIP_BASE + flash_base + offset);
    return std::all_of(bytes, bytes + FLASH_SECTOR_SIZE, [](auto b) { return b == 255; });
}
bool PicoFlash::program(std::size_t offset, std::span<const std::uint8_t> page) {
    if (offset % FLASH_PAGE_SIZE || page.size() != FLASH_PAGE_SIZE ||
        offset > storage_size - FLASH_PAGE_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    struct Write {
        std::size_t offset;
        const std::uint8_t* data;
    } write{offset, page.data()};
    auto program = [](void* argument) {
        const auto& write = *static_cast<Write*>(argument);
        flash_range_program(flash_base + write.offset, write.data, FLASH_PAGE_SIZE);
    };
    if (flash_safe_execute(program, &write, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_program(flash_base + offset, page.data(), page.size());
    restore_interrupts(irq);
#endif
    return true; // Journal independently verifies the complete record.
}
PicoNetwork::PicoNetwork(time::UtcDiscipline& clock, std::string_view configured_hostname)
    : sntp_(clock), mdns_(*this, configured_hostname) {}
#ifndef WSPRRY_PICO_STANDALONE_RF
void PicoNetwork::trace_install() {
    (void)trace_.install(&cyw43_state.netif[CYW43_ITF_STA]);
}
std::string PicoNetwork::association() {
    if (!initialized_ || !link_up())
        return "{\"valid\":false,\"error\":\"not_connected\"}";
    std::array<std::uint8_t, 6> bssid{};
    const auto enclosing = watchdog_hw->scratch[1];
    watchdog_hw->scratch[1] = 26;
    const auto bssid_result = cyw43_wifi_get_bssid(&cyw43_state, bssid.data());
    watchdog_hw->scratch[1] = enclosing;
    if (bssid_result)
        return "{\"valid\":false,\"error\":\"bssid_query\",\"code\":" +
               std::to_string(bssid_result) + "}";
    if (!link_up())
        return "{\"valid\":false,\"error\":\"link_changed\"}";
    std::string address;
    constexpr char digits[] = "0123456789abcdef";
    for (auto byte : bssid) {
        if (!address.empty())
            address += ':';
        address += digits[byte >> 4];
        address += digits[byte & 15];
    }
    if (network::default_hostname(address).empty())
        return "{\"valid\":false,\"error\":\"invalid_bssid\"}";
    return "{\"valid\":true,\"bssid\":" + wtp::json::quote(address) + "}";
}
#endif
bool PicoNetwork::initialize() {
    if (mdns_owner && mdns_owner != this)
        return false;
    if (wsprry_mdns_init(mdns_result) != ERR_OK)
        return false;
    mdns_owner = this;
    return true;
}
bool PicoNetwork::add(std::string_view label) {
    const std::string owned(label);
    return wsprry_mdns_add(&cyw43_state.netif[CYW43_ITF_STA], owned.c_str()) == ERR_OK;
}
void PicoNetwork::remove(bool goodbye) {
    wsprry_mdns_remove(&cyw43_state.netif[CYW43_ITF_STA], goodbye);
}
void PicoNetwork::withdraw() {
    trace_mark(2); // Before goodbye submission.
    (void)wsprry_mdns_withdraw(&cyw43_state.netif[CYW43_ITF_STA]);
    trace_mark(3); // After goodbye submission.
}
void PicoNetwork::mdns_result(struct netif* interface, u8_t result, s8_t slot) {
    if (mdns_owner && interface == &cyw43_state.netif[CYW43_ITF_STA] && slot == 0)
        mdns_owner->mdns_.name_result(result == MDNS_PROBING_SUCCESSFUL);
}
bool PicoNetwork::start(const Config& config) {
    if (initialized_ || !valid_time_server(config.ntp_ipv4))
        return false;
    time_server_ = config.ntp_ipv4;
    if (!time_server_.empty() && time_server_.back() == '.')
        time_server_.pop_back();
    for (auto& c : time_server_)
        if (c >= 'A' && c <= 'Z')
            c += 'a' - 'A'; // lwIP's .local selection is case-sensitive.
    server_literal_ = ipaddr_aton(time_server_.c_str(), &server_) != 0;
    watchdog_hw->scratch[1] = 10;
    if (cyw43_arch_init())
        return false;
    initialized_ = true;
    watchdog_hw->scratch[1] = 11;
    cyw43_arch_enable_sta_mode();
    std::array<std::uint8_t, 6> mac{};
    station_mac_.clear();
    stable_hostname_.clear();
    if (cyw43_wifi_get_mac(&cyw43_state, CYW43_ITF_STA, mac.data()) == 0) {
        constexpr char digits[] = "0123456789abcdef";
        for (auto byte : mac) {
            if (!station_mac_.empty())
                station_mac_ += ':';
            station_mac_ += digits[byte >> 4];
            station_mac_ += digits[byte & 15];
        }
        stable_hostname_ = network::default_hostname(station_mac_);
        if (stable_hostname_.empty())
            station_mac_.clear();
    }
    trace_install();
    // USB-powered network control needs continuous receive availability.
    if (!disable_power_save()) {
        trace_mark(4); // Before station disable.
        cyw43_arch_disable_sta_mode();
        trace_mark(5); // After station disable.
        cyw43_arch_deinit();
        initialized_ = false;
        return false;
    }
    watchdog_hw->scratch[1] = 12;
    ssid_ = config.ssid;
    password_ = config.password;
    pcb_ = udp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb_) {
        trace_mark(4); // Before station disable.
        cyw43_arch_disable_sta_mode();
        trace_mark(5); // After station disable.
        cyw43_arch_deinit();
        initialized_ = false;
        return false;
    }
    udp_recv(pcb_, receive, this);
    return true;
}
void PicoNetwork::resolved(const char* name, const ip_addr_t* address, void* context) {
    auto& self = *static_cast<PicoNetwork*>(context);
    const bool valid = address && IP_IS_V4(address) && !ip_addr_isany(address) &&
                       valid_time_server(ipaddr_ntoa(address)) && name && self.time_server_ == name;
    if (!valid)
        ++self.resolution_failures_;
    if (self.lookup_.finish(self.lookup_epoch_, valid, time_us_64()) && valid) {
        if (!ip_addr_cmp(&self.server_, address)) {
            self.sntp_.cancel(); // Never accept an old peer's outstanding reply.
            self.poll_schedule_.reset();
        }
        self.server_ = *address;
    }
}
void PicoNetwork::resolve_server(std::uint64_t now) {
    const auto epoch = lookup_.begin(now);
    if (!epoch)
        return;
    lookup_epoch_ = *epoch;
    ip_addr_t address{};
    const auto result = dns_gethostbyname_addrtype(time_server_.c_str(), &address, resolved, this,
                                                   LWIP_DNS_ADDRTYPE_IPV4);
    if (result != ERR_INPROGRESS)
        resolved(time_server_.c_str(), result == ERR_OK ? &address : nullptr, this);
}
void PicoNetwork::receive(void* context, udp_pcb*, pbuf* packet, const ip_addr_t* address,
                          u16_t port) {
    auto& self = *static_cast<PicoNetwork*>(context);
    const auto now = time_us_64() * 1000ULL;
    if (packet && port == 123 && ip_addr_cmp(address, &self.server_) && packet->tot_len == 48) {
        std::array<std::uint8_t, 48> bytes{};
        if (pbuf_copy_partial(packet, bytes.data(), bytes.size(), 0) == bytes.size()) {
            if (self.sntp_.receive(bytes, now)) {
                ++self.accepted_;
                self.poll_schedule_.accepted(now / 1000);
            } else
                ++self.rejected_;
        }
    }
    if (packet)
        pbuf_free(packet);
}
void PicoNetwork::poll() {
    if (!initialized_ || !pcb_ || (!enabled_ && !withdrawal_started_us_))
        return;
    watchdog_hw->scratch[1] = 13;
    cyw43_arch_poll();
    watchdog_hw->scratch[1] = 14;
    const auto now = time_us_64();
    const auto link = cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA);
    if (withdrawal_started_us_) {
        // CYW43 send success means a bus transfer, not an over-air completion.
        // Service the driver without mDNS replies/reconnects for one second.
        // This is a bounded transmission opportunity, never a delivery guarantee.
        if (link != CYW43_LINK_UP || now - *withdrawal_started_us_ >= 1'000'000ULL) {
            watchdog_hw->scratch[1] = 15;
            mdns_.disable(false);
            watchdog_hw->scratch[1] = 16;
            trace_mark(4); // Before station disable.
            cyw43_arch_disable_sta_mode();
            trace_mark(5); // After station disable.
            watchdog_hw->scratch[1] = 17;
            withdrawal_started_us_.reset();
            const bool resume = resume_after_withdrawal_;
            resume_after_withdrawal_ = false;
            if (resume)
                (void)set_enabled(true);
        }
        return;
    }
    lookup_.link(link == CYW43_LINK_UP);
    const auto* station = &cyw43_state.netif[CYW43_ITF_STA];
    if (wsprry_mdns_network_changed())
        mdns_.network_changed();
    mdns_.poll(enabled_ && listening_ && link_up(),
               link_up() ? ip4_addr_get_u32(netif_ip4_addr(station)) : 0, now);
    if (link != CYW43_LINK_UP) {
        sntp_.cancel();
        poll_schedule_.reset();
        if (now >= next_connect_us_) {
            watchdog_hw->scratch[1] = 15;
            (void)cyw43_arch_wifi_connect_async(ssid_.c_str(), password_.c_str(),
                                                CYW43_AUTH_WPA2_AES_PSK);
            next_connect_us_ = now + 30'000'000ULL;
        }
        return;
    }
    if (!server_literal_) {
        resolve_server(now);
        if (!lookup_.ready())
            return;
    }
    if (!poll_schedule_.due(now) || sntp_.denied())
        return;
    poll_schedule_.sent(now);
    ++queries_;
    const auto bytes = sntp_.request(now * 1000ULL, get_rand_64());
    auto* packet = pbuf_alloc(PBUF_TRANSPORT, bytes.size(), PBUF_RAM);
    if (!packet) {
        sntp_.cancel();
        return;
    }
    if (pbuf_take(packet, bytes.data(), bytes.size()) != ERR_OK ||
        udp_sendto(pcb_, packet, &server_, 123) != ERR_OK)
        sntp_.cancel();
    pbuf_free(packet);
}
bool PicoNetwork::request_enabled(bool enabled) {
    if (!initialized_ || !pcb_)
        return false;
    pending_enabled_ = enabled;
    return true;
}
void PicoNetwork::finish_request(bool idle) {
    if (pending_enabled_ && idle)
        (void)set_enabled(*pending_enabled_);
    pending_enabled_.reset();
}
bool PicoNetwork::disable_power_save() {
    if (!initialized_ || !enabled_)
        return false;
    std::uint32_t observed = 0;
    power_save_.reset();
    if (cyw43_wifi_pm(&cyw43_state, CYW43_NONE_PM) || cyw43_wifi_get_pm(&cyw43_state, &observed))
        return false;
    power_save_ = (observed & 0xf) != CYW43_NO_POWERSAVE_MODE;
    return !*power_save_;
}
bool PicoNetwork::set_enabled(bool enabled) {
    if (!initialized_ || !pcb_)
        return false;
    if (withdrawal_started_us_) {
        // Repeated OFF never extends the deadline. Rapid ON waits for teardown
        // before recreating the netif; it cannot resurrect the old registration.
        resume_after_withdrawal_ = enabled;
        return true;
    }
    if (enabled_ == enabled)
        return true;
    sntp_.cancel();
    enabled_ = enabled;
    if (enabled) {
        mdns_.retry();
        cyw43_arch_enable_sta_mode();
        trace_install();
        if (!disable_power_save()) {
            trace_mark(4); // Before station disable.
            cyw43_arch_disable_sta_mode();
            trace_mark(5); // After station disable.
            enabled_ = false;
            return false;
        }
        next_connect_us_ = 0;
        poll_schedule_.reset();
    } else {
        lookup_.link(false);
        // enabled_ was already changed; inspect the actual station before teardown.
        if (mdns_.withdraw(cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP))
            withdrawal_started_us_ = time_us_64();
        else {
            mdns_.disable(false);
            trace_mark(4); // Before station disable.
            cyw43_arch_disable_sta_mode();
            trace_mark(5); // After station disable.
        }
    }
    return true;
}
bool PicoNetwork::link_up() const {
    return initialized_ && enabled_ &&
           cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP;
}
std::string PicoNetwork::ipv4() const {
    return link_up() ? ip4addr_ntoa(netif_ip4_addr(&cyw43_state.netif[CYW43_ITF_STA])) : "";
}
std::string PicoNetwork::status() const {
    const auto uncertainty = sntp_.last_uncertainty_ns();
    return "{\"initialized\":" + std::string(initialized_ ? "true" : "false") +
           ",\"enabled\":" + (enabled_ ? "true" : "false") + ",\"link_status\":" +
           std::to_string(initialized_ ? cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA)
                                       : -99) +
           ",\"ipv4\":" + wtp::json::quote(ipv4()) + ",\"requested_enabled\":" +
           (pending_enabled_ ? (*pending_enabled_ ? "true" : "false") : "null") +
           ",\"withdrawal_pending\":" + (withdrawal_started_us_ ? "true" : "false") +
           ",\"resume_after_withdrawal\":" + (resume_after_withdrawal_ ? "true" : "false") +
           ",\"control_configured\":" + (configured_ ? "true" : "false") +
           ",\"control_listening\":" + (listening_ ? "true" : "false") +
           ",\"deployment_identity_matches\":" + (identity_matches_ ? "true" : "false") +
           ",\"station_mac\":" + wtp::json::quote(station_mac_) +
           ",\"stable_hostname\":" + wtp::json::quote(stable_hostname_) +
           ",\"configured_hostname\":" + wtp::json::quote(mdns_.hostname()) +
           ",\"advertised_hostname\":" + wtp::json::quote(mdns_.advertised()) +
           ",\"mdns_state\":" + wtp::json::quote(mdns_.state()) +
           ",\"mdns_reason\":" + wtp::json::quote(mdns_.reason()) +
           ",\"mdns_registrations\":" + std::to_string(mdns_.registrations()) +
           ",\"mdns_conflicts\":" + std::to_string(mdns_.conflicts()) +
           ",\"mdns_failures\":" + std::to_string(mdns_.failures()) +
           ",\"mdns_address_changes\":" + std::to_string(mdns_.address_changes()) +
           ",\"mdns_goodbye_attempts\":" + std::to_string(wsprry_mdns_goodbye_attempts()) +
           ",\"mdns_goodbye_failures\":" + std::to_string(wsprry_mdns_goodbye_failures()) +
           ",\"mdns_rejected_packets\":" + std::to_string(wsprry_mdns_rejected_packets()) +
           ",\"power_save\":" + (power_save_ ? (*power_save_ ? "true" : "false") : "null") +
           ",\"packets\":{\"arp\":" + packet_stats(lwip_stats.etharp) +
           ",\"ipv4\":" + packet_stats(lwip_stats.ip) + ",\"tcp\":" + packet_stats(lwip_stats.tcp) +
           ",\"udp\":" + packet_stats(lwip_stats.udp) + "}" + ",\"memory\":" + network_memory() +
           ",\"ntp_server\":" + wtp::json::quote(time_server_) + ",\"ntp_address\":" +
           wtp::json::quote(server_literal_ || lookup_.ready() ? ipaddr_ntoa(&server_) : "") +
           ",\"ntp_resolution\":" +
           wtp::json::quote(server_literal_     ? "literal"
                            : lookup_.pending() ? "resolving"
                            : lookup_.ready()   ? "resolved"
                                                : "unresolved") +
           ",\"ntp_resolution_failures\":" + std::to_string(resolution_failures_) +
           ",\"queries\":" + std::to_string(queries_) +
           ",\"accepted\":" + std::to_string(accepted_) +
           ",\"rejected\":" + std::to_string(rejected_) +
           ",\"last_rtt_ns\":" + std::to_string(sntp_.last_rtt_ns()) +
           ",\"last_sample_uncertainty_ns\":" +
           (uncertainty ? std::to_string(*uncertainty) : "null") + "}";
}
} // namespace wsprrypico::standalone
