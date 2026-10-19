#ifdef WSPRRY_PICO_JOURNAL_FAULT_FIXTURE
#include "provisioning/pico/journal_fault_fixture.hpp"
#endif
#include "standalone/pico/adapters.hpp"

#ifdef WSPRRY_PICO_CYW43_TX_GUARD
#include "standalone/pico/cyw43_tx_guard.h"
#endif
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
#include "runtime/activity_trace.hpp"
#include "standalone/pico/flash_layout.hpp"
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
static_assert(PICO_FLASH_SIZE_BYTES == flash_layout::physical_size);
static_assert(MEM_ALIGNMENT >= alignof(std::uint32_t));
PicoNetwork* mdns_owner = nullptr;
FlashResources flash_counters;
std::uint64_t activity_now_ns() {
    return time_us_64() * 1000ULL;
}
struct FlashCall {
    runtime::ActivitySpan<std::uint64_t (*)()> trace;
    std::uint64_t& failures;
    bool ok = false;
    FlashCall(std::uint64_t& attempts, std::uint64_t& failed, std::uint64_t& bytes,
              std::size_t requested, runtime::ActivityKind kind = runtime::ActivityKind::None)
        : trace(runtime::activity_trace(), kind, activity_now_ns,
                kind != runtime::ActivityKind::None),
          failures(failed) {
        ++attempts;
        bytes += requested;
    }
    ~FlashCall() {
        trace.outcome(ok);
        if (!ok)
            ++failures;
    }
    bool finish(bool result) {
        ok = result;
        return result;
    }
};

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
    return "{\"statistics_enabled\":true,\"heap\":" + memory_stats(&lwip_stats.mem) +
           ",\"tcp_pcbs\":" + memory_stats(lwip_stats.memp[MEMP_TCP_PCB]) +
           ",\"tcp_listeners\":" + memory_stats(lwip_stats.memp[MEMP_TCP_PCB_LISTEN]) +
           ",\"udp_pcbs\":" + memory_stats(lwip_stats.memp[MEMP_UDP_PCB]) +
           ",\"timeouts\":" + memory_stats(lwip_stats.memp[MEMP_SYS_TIMEOUT]) +
           ",\"igmp_groups\":" + memory_stats(lwip_stats.memp[MEMP_IGMP_GROUP]) +
           ",\"tcp_segments\":" + memory_stats(lwip_stats.memp[MEMP_TCP_SEG]) +
           ",\"packet_pool\":" + memory_stats(lwip_stats.memp[MEMP_PBUF_POOL]) + "}";
}
} // namespace
FlashResources flash_resources() {
    return flash_counters;
}
bool PicoFlash::read(std::size_t offset, std::span<std::uint8_t> data) {
    const auto storage_size = region_ == Region::Ntp        ? flash_layout::ntp_size
                              : region_ == Region::Progress ? flash_layout::progress_size
                                                            : flash_layout::standalone_size;
    const auto flash_base = region_ == Region::Ntp        ? flash_layout::ntp_base
                            : region_ == Region::Progress ? flash_layout::progress_base
                                                          : flash_layout::standalone_base;
    FlashCall call(flash_counters.read_attempts, flash_counters.read_failures,
                   flash_counters.read_requested_bytes, data.size());
    if (offset > storage_size || data.size() > storage_size - offset)
        return false;
    std::memcpy(data.data(), reinterpret_cast<const void*>(XIP_BASE + flash_base + offset),
                data.size());
    return call.finish(true);
}
bool PicoFlash::erase(std::size_t offset) {
    const auto storage_size = region_ == Region::Ntp        ? flash_layout::ntp_size
                              : region_ == Region::Progress ? flash_layout::progress_size
                                                            : flash_layout::standalone_size;
    const auto flash_base = region_ == Region::Ntp        ? flash_layout::ntp_base
                            : region_ == Region::Progress ? flash_layout::progress_base
                                                          : flash_layout::standalone_base;
    FlashCall call(flash_counters.erase_attempts, flash_counters.erase_failures,
                   flash_counters.erase_requested_bytes, FLASH_SECTOR_SIZE,
                   runtime::ActivityKind::StandaloneErase);
    if (offset % FLASH_SECTOR_SIZE || offset > storage_size - FLASH_SECTOR_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    // Authority excludes Armed/Running and unknown output before entering here.
    auto erase = [](void* argument) {
        flash_range_erase(*static_cast<std::size_t*>(argument), FLASH_SECTOR_SIZE);
    };
    auto physical_offset = flash_base + offset;
    if (flash_safe_execute(erase, &physical_offset, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_erase(flash_base + offset, FLASH_SECTOR_SIZE);
    restore_interrupts(irq);
#endif
    const auto* bytes = reinterpret_cast<const std::uint8_t*>(XIP_BASE + flash_base + offset);
    return call.finish(
        std::all_of(bytes, bytes + FLASH_SECTOR_SIZE, [](auto b) { return b == 255; }));
}
bool PicoFlash::program(std::size_t offset, std::span<const std::uint8_t> page) {
    const auto storage_size = region_ == Region::Ntp        ? flash_layout::ntp_size
                              : region_ == Region::Progress ? flash_layout::progress_size
                                                            : flash_layout::standalone_size;
    const auto flash_base = region_ == Region::Ntp        ? flash_layout::ntp_base
                            : region_ == Region::Progress ? flash_layout::progress_base
                                                          : flash_layout::standalone_base;
    FlashCall call(flash_counters.program_attempts, flash_counters.program_failures,
                   flash_counters.program_requested_bytes, page.size(),
                   runtime::ActivityKind::StandaloneProgram);
    if (offset % FLASH_PAGE_SIZE || page.size() != FLASH_PAGE_SIZE ||
        offset > storage_size - FLASH_PAGE_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    struct Write {
        std::size_t offset;
        const std::uint8_t* data;
    } write{flash_base + offset, page.data()};
    auto program = [](void* argument) {
        const auto& write = *static_cast<Write*>(argument);
        flash_range_program(write.offset, write.data, FLASH_PAGE_SIZE);
    };
    if (flash_safe_execute(program, &write, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_program(flash_base + offset, page.data(), page.size());
    restore_interrupts(irq);
#endif
    return call.finish(true); // Journal independently verifies the complete record.
}
bool PicoProfileMedia::read(std::size_t offset, std::span<std::uint8_t> data) {
    FlashCall call(flash_counters.read_attempts, flash_counters.read_failures,
                   flash_counters.read_requested_bytes, data.size());
    if (offset > provisioning::profile_media_size ||
        data.size() > provisioning::profile_media_size - offset)
        return false;
    std::memcpy(data.data(),
                reinterpret_cast<const void*>(XIP_BASE + flash_layout::profile_base + offset),
                data.size());
    return call.finish(true);
}
bool PicoProfileMedia::erase(std::size_t offset) {
    FlashCall call(flash_counters.erase_attempts, flash_counters.erase_failures,
                   flash_counters.erase_requested_bytes, provisioning::profile_slot_size,
                   runtime::ActivityKind::ProfileErase);
    if (offset % provisioning::profile_slot_size ||
        offset > provisioning::profile_media_size - provisioning::profile_slot_size)
        return false;
    for (std::size_t sector = 0; sector < provisioning::profile_slot_size;
         sector += FLASH_SECTOR_SIZE) {
        const auto physical = flash_layout::profile_base + offset + sector;
#ifdef WSPRRY_PICO_STANDALONE_RF
        auto erase = [](void* argument) {
            flash_range_erase(*static_cast<std::size_t*>(argument), FLASH_SECTOR_SIZE);
        };
        auto address = physical;
        if (flash_safe_execute(erase, &address, 100) != PICO_OK)
            return false;
#else
        const auto irq = save_and_disable_interrupts();
        flash_range_erase(physical, FLASH_SECTOR_SIZE);
        restore_interrupts(irq);
#endif
    }
    const auto* bytes =
        reinterpret_cast<const std::uint8_t*>(XIP_BASE + flash_layout::profile_base + offset);
    return call.finish(std::all_of(bytes, bytes + provisioning::profile_slot_size,
                                   [](auto byte) { return byte == 255; }));
}
bool PicoProfileMedia::program(std::size_t offset, std::span<const std::uint8_t> page) {
    FlashCall call(flash_counters.program_attempts, flash_counters.program_failures,
                   flash_counters.program_requested_bytes, page.size(),
                   runtime::ActivityKind::ProfileProgram);
    if (offset % FLASH_PAGE_SIZE || page.size() != FLASH_PAGE_SIZE ||
        offset > provisioning::profile_media_size - FLASH_PAGE_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    struct Write {
        std::size_t offset;
        const std::uint8_t* data;
    } write{flash_layout::profile_base + offset, page.data()};
    auto program = [](void* argument) {
        const auto& write = *static_cast<Write*>(argument);
        flash_range_program(write.offset, write.data, FLASH_PAGE_SIZE);
    };
    if (flash_safe_execute(program, &write, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_program(flash_layout::profile_base + offset, page.data(), page.size());
    restore_interrupts(irq);
#endif
#ifdef WSPRRY_PICO_JOURNAL_FAULT_FIXTURE
    provisioning::journal_profile_programmed(offset);
#endif
    return call.finish(true);
}
bool PicoAccessMedia::read(std::size_t offset, std::span<std::uint8_t> data) {
    FlashCall call(flash_counters.read_attempts, flash_counters.read_failures,
                   flash_counters.read_requested_bytes, data.size());
    if (offset > provisioning::access_media_size ||
        data.size() > provisioning::access_media_size - offset)
        return false;
    std::memcpy(data.data(),
                reinterpret_cast<const void*>(XIP_BASE + flash_layout::access_base + offset),
                data.size());
    return call.finish(true);
}
bool PicoAccessMedia::erase(std::size_t offset) {
    FlashCall call(flash_counters.erase_attempts, flash_counters.erase_failures,
                   flash_counters.erase_requested_bytes, FLASH_SECTOR_SIZE,
                   runtime::ActivityKind::AccessErase);
    if (offset % provisioning::access_slot_size ||
        offset > provisioning::access_media_size - provisioning::access_slot_size)
        return false;
    const auto physical = flash_layout::access_base + offset;
#ifdef WSPRRY_PICO_STANDALONE_RF
    auto erase = [](void* argument) {
        flash_range_erase(*static_cast<std::size_t*>(argument), FLASH_SECTOR_SIZE);
    };
    auto address = physical;
    if (flash_safe_execute(erase, &address, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_erase(physical, FLASH_SECTOR_SIZE);
    restore_interrupts(irq);
#endif
    const auto* bytes = reinterpret_cast<const std::uint8_t*>(XIP_BASE + physical);
    return call.finish(std::all_of(bytes, bytes + provisioning::access_slot_size,
                                   [](auto byte) { return byte == 255; }));
}
bool PicoAccessMedia::program(std::size_t offset, std::span<const std::uint8_t> page) {
    FlashCall call(flash_counters.program_attempts, flash_counters.program_failures,
                   flash_counters.program_requested_bytes, page.size(),
                   runtime::ActivityKind::AccessProgram);
    if (offset % FLASH_PAGE_SIZE || page.size() != FLASH_PAGE_SIZE ||
        offset > provisioning::access_media_size - FLASH_PAGE_SIZE)
        return false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    struct Write {
        std::size_t offset;
        const std::uint8_t* data;
    } write{flash_layout::access_base + offset, page.data()};
    auto program = [](void* argument) {
        const auto& write = *static_cast<Write*>(argument);
        flash_range_program(write.offset, write.data, FLASH_PAGE_SIZE);
    };
    if (flash_safe_execute(program, &write, 100) != PICO_OK)
        return false;
#else
    const auto irq = save_and_disable_interrupts();
    flash_range_program(flash_layout::access_base + offset, page.data(), page.size());
    restore_interrupts(irq);
#endif
    return call.finish(true);
}
PicoNetwork::PicoNetwork(time::ObservationSink& clock, std::string_view configured_hostname)
    : ntp_(clock),
      peers_{NtpPeer{*this, 0}, NtpPeer{*this, 1}, NtpPeer{*this, 2}, NtpPeer{*this, 3}},
      mdns_(*this, configured_hostname) {}
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
    if (mdns_initialized_)
        return true;
    if (mdns_owner && mdns_owner != this)
        return false;
    if (wsprry_mdns_init(mdns_result) != ERR_OK)
        return false;
    mdns_owner = this;
    mdns_initialized_ = true;
    return true;
}
bool PicoNetwork::add(std::string_view label) {
    const std::string owned(label);
    auto* station = &cyw43_state.netif[CYW43_ITF_STA];
    if (wsprry_mdns_add(station, owned.c_str()) != ERR_OK)
        return false;
    if (consumer_http_ && wsprry_mdns_add_http_service(station, owned.c_str()) != ERR_OK) {
        wsprry_mdns_remove(station, 0);
        return false;
    }
    if (wtp_binding_ != WtpBinding::None &&
        wsprry_mdns_add_wtp_service(station, owned.c_str(), static_cast<u16_t>(wtp_port_),
                                    wtp_binding_ == WtpBinding::Plain ? "plain" : "tls") !=
            ERR_OK) {
        wsprry_mdns_remove(station, 0);
        return false;
    }
    return true;
}
void PicoNetwork::consumer_listener_status(bool ready) {
    if (consumer_http_ == ready)
        return;
    consumer_http_ = ready;
    if (withdrawal_started_us_ || service_withdrawal_started_us_)
        return;
    if (mdns_.withdraw(link_up()))
        service_withdrawal_started_us_ = time_us_64();
    else
        mdns_.disable(false);
}
void PicoNetwork::wtp_listener_status(WtpBinding binding, unsigned port) {
    if (binding == WtpBinding::None || port == 0 || port > 65535) {
        binding = WtpBinding::None;
        port = 0;
    }
    if (binding == wtp_binding_ && port == wtp_port_)
        return;
    wtp_binding_ = binding;
    wtp_port_ = port;
    if (withdrawal_started_us_ || service_withdrawal_started_us_)
        return;
    if (mdns_.withdraw(link_up()))
        service_withdrawal_started_us_ = time_us_64();
    else
        mdns_.disable(false);
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
    if (mdns_owner && interface == &cyw43_state.netif[CYW43_ITF_AP] && slot == 0) {
        mdns_owner->softap_mdns_active_ = result == MDNS_PROBING_SUCCESSFUL;
        mdns_owner->softap_mdns_conflict_ = result == MDNS_PROBING_CONFLICT;
    }
}
bool PicoNetwork::softap_name(bool enabled, std::string_view hostname) {
    auto* interface = &cyw43_state.netif[CYW43_ITF_AP];
    if (!enabled) {
        if (softap_mdns_registered_)
            wsprry_mdns_remove(interface, false);
        softap_mdns_registered_ = softap_mdns_active_ = false;
        softap_mdns_conflict_ = false;
        softap_hostname_.clear();
        return false;
    }
    const auto canonical = network::canonical_local_hostname(hostname);
    if (!canonical || !netif_is_up(interface) || !netif_is_link_up(interface) ||
        ip4_addr_isany_val(*netif_ip4_addr(interface)) || softap_mdns_conflict_)
        return false;
    if (softap_mdns_registered_)
        return softap_mdns_active_ && softap_hostname_ == *canonical;
    if (!initialize())
        return false;
    softap_hostname_ = *canonical;
    const auto label = softap_hostname_.substr(0, softap_hostname_.size() - 6);
    if (wsprry_mdns_add(interface, label.c_str()) != ERR_OK) {
        softap_hostname_.clear();
        return false;
    }
    softap_mdns_registered_ = true;
    softap_mdns_active_ = false;
    return false; // Probing; callback promotes it to usable.
}
bool PicoNetwork::initialize_radio() {
    if (initialized_)
        return !station_mac_.empty();
    watchdog_hw->scratch[1] = 10;
    if (cyw43_arch_init())
        return false;
    initialized_ = true;
    std::array<std::uint8_t, 6> mac{};
    // SDK 2.3.1 does not populate the OTP MAC until the first CYW43
    // ensure-up. Briefly create the station netif solely for that checked read;
    // no SSID/join/DHCP request is supplied, and the interface is disabled
    // again before any access-policy decision or field service starts.
    cyw43_arch_enable_sta_mode();
    const auto mac_result = cyw43_wifi_get_mac(&cyw43_state, CYW43_ITF_STA, mac.data());
    cyw43_arch_disable_sta_mode();
    if (mac_result != 0)
        return false;
    constexpr char digits[] = "0123456789abcdef";
    station_mac_.clear();
    for (auto byte : mac) {
        if (!station_mac_.empty())
            station_mac_ += ':';
        station_mac_ += digits[byte >> 4];
        station_mac_ += digits[byte & 15];
    }
    stable_hostname_ = network::default_hostname(station_mac_);
    if (stable_hostname_.empty())
        station_mac_.clear();
    return !station_mac_.empty();
}
bool PicoNetwork::start(const Config& config) {
    return start_credentials(config.ssid, config.password, config.ntp_ipv4);
}
bool PicoNetwork::start_network_only(std::string_view ssid, std::string_view password,
                                     std::string_view time_server) {
    return start_credentials(ssid, password, time_server);
}
void PicoNetwork::stop_network_only_trial() {
    for (auto& peer : peers_)
        ntp_.cancel(peer.index);
    ntp_.online(false, activity_now_ns());
    for (auto& peer : peers_)
        peer.lookup.link(false);
    mdns_.disable(false);
    service_withdrawal_started_us_.reset();
    if (enabled_)
        cyw43_arch_disable_sta_mode();
    if (pcb_)
        udp_remove(pcb_);
    pcb_ = nullptr;
    auto erase = [](std::string& value) {
        volatile char* bytes = value.empty() ? nullptr : value.data();
        for (std::size_t i = 0; i < value.size(); ++i)
            bytes[i] = 0;
        std::string{}.swap(value);
    };
    erase(ssid_);
    erase(password_);
    enabled_ = false;
    next_connect_us_ = 0;
    reconnect_after_leave_us_.reset();
    withdrawal_started_us_.reset();
    resume_after_withdrawal_ = false;
    pending_enabled_.reset();
}
bool PicoNetwork::start_credentials(std::string_view ssid, std::string_view password,
                                    std::string_view time_server) {
    if (pcb_ || !valid_time_server(time_server) || !initialize_radio())
        return false;
    ntp_.reset_peer();
    for (auto& peer : peers_)
        ntp_.remove(peer.index, activity_now_ns());
    time_server_ = time_server;
    if (!time_server_.empty() && time_server_.back() == '.')
        time_server_.pop_back();
    for (auto& c : time_server_)
        if (c >= 'A' && c <= 'Z')
            c += 'a' - 'A'; // lwIP's .local selection is case-sensitive.
    pool_enabled_ = time_server_ == "pool.ntp.org" || time_server_.ends_with(".pool.ntp.org");
    ntp_link_up_ = false;
    for (auto& peer : peers_) {
        auto pool_name = time_server_;
        if (pool_name.size() > 2 && pool_name[0] >= '0' && pool_name[0] <= '3' &&
            pool_name[1] == '.')
            pool_name.erase(0, 2);
        peer.hostname = pool_enabled_ ? std::to_string(peer.index) + "." + pool_name : time_server_;
        peer.lookup.link(false);
        peer.sent = false;
    }
    server_literal_ = ipaddr_aton(time_server_.c_str(), &peers_[0].address) != 0;
    if (server_literal_)
        (void)ntp_.configure(0, ip4_addr_get_u32(ip_2_ip4(&peers_[0].address)), activity_now_ns());
    watchdog_hw->scratch[1] = 11;
    cyw43_arch_enable_sta_mode();
    enabled_ = true;
    trace_install();
    // USB-powered network control needs continuous receive availability.
    if (!disable_power_save()) {
        trace_mark(4); // Before station disable.
        cyw43_arch_disable_sta_mode();
        trace_mark(5); // After station disable.
        enabled_ = false;
        return false;
    }
    watchdog_hw->scratch[1] = 12;
    ssid_ = ssid;
    password_ = password;
    pcb_ = udp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb_) {
        trace_mark(4); // Before station disable.
        cyw43_arch_disable_sta_mode();
        trace_mark(5); // After station disable.
        enabled_ = false;
        return false;
    }
    udp_recv(pcb_, receive, this);
    return true;
}
void PicoNetwork::resolved(const char* name, const ip_addr_t* address, void* context) {
    auto& peer = *static_cast<NtpPeer*>(context);
    auto& self = peer.owner;
    bool valid = address && IP_IS_V4(address) && !ip_addr_isany(address) &&
                 valid_time_server(ipaddr_ntoa(address)) && name && peer.hostname == name;
    if (valid && self.pool_enabled_)
        for (const auto& other : self.peers_)
            if (other.index != peer.index && other.lookup.ready() &&
                ip_addr_cmp(address, &other.address))
                valid = false; // Never query one endpoint through multiple pool aliases.
    if (!valid)
        ++self.resolution_failures_;
    const auto now = time_us_64();
    const bool retained = now <= UINT64_MAX / 1000 && peer.retained(now * 1000);
    if (peer.lookup.finish(peer.lookup_epoch, valid, now, retained) && valid) {
        if (!ip_addr_cmp(&peer.address, address)) {
            // Keep the previous UTC anchor at its original age while the new
            // endpoint establishes its own history and passes arbitration.
            self.ntp_.remove(peer.index, activity_now_ns());
        }
        peer.address = *address;
        (void)self.ntp_.configure(peer.index, ip4_addr_get_u32(ip_2_ip4(address)),
                                  activity_now_ns());
    }
}
void PicoNetwork::resolve_server(std::uint64_t now) {
    for (auto& peer : peers_) {
        if (peer.index && !pool_enabled_)
            break;
        const bool retained = now <= UINT64_MAX / 1000 && peer.retained(now * 1000);
        const auto epoch = peer.lookup.begin(now, retained);
        if (!epoch)
            continue;
        peer.lookup_epoch = *epoch;
        ip_addr_t address{};
        const auto result = dns_gethostbyname_addrtype(peer.hostname.c_str(), &address, resolved,
                                                       &peer, LWIP_DNS_ADDRTYPE_IPV4);
        if (result != ERR_INPROGRESS)
            resolved(peer.hostname.c_str(), result == ERR_OK ? &address : nullptr, &peer);
    }
}
void PicoNetwork::receive(void* context, udp_pcb*, pbuf* packet, const ip_addr_t* address,
                          u16_t port) {
    auto& self = *static_cast<PicoNetwork*>(context);
    const auto now = activity_now_ns();
    if (packet && address && port == 123) {
        for (auto& peer : self.peers_) {
            if ((peer.index && !self.pool_enabled_) ||
                (!self.server_literal_ && !peer.lookup.ready()) ||
                !ip_addr_cmp(address, &peer.address))
                continue;
            std::array<std::uint8_t, 49> bytes{};
            const auto length = std::min<std::size_t>(bytes.size(), packet->tot_len);
            if (pbuf_copy_partial(packet, bytes.data(), length, 0) == length) {
                const auto process_start = time_us_64();
                const bool admitted = self.ntp_.receive(peer.index, {bytes.data(), length}, now,
                                                        true, packet->tot_len);
                peer.max_process_us = std::max(peer.max_process_us, time_us_64() - process_start);
                if (admitted) {
                    ++self.accepted_;
                    ++peer.accepted;
                    if (self.ntp_.arbiter_accepted())
                        ++self.discipline_accepted_;
                } else {
                    ++self.rejected_;
                    ++peer.rejected;
                }
            }
            break;
        }
    }
    if (packet)
        pbuf_free(packet);
}
bool PicoNetwork::send_ntp(NtpPeer& peer, std::uint64_t now) {
    if (now > UINT64_MAX / 1000)
        return false;
    const auto bytes = ntp_.scheduled_request(peer.index, now * 1000, get_rand_64());
    if (!bytes)
        return false;
    peer.last_sent_us = now;
    peer.sent = true;
    ++queries_;
    ++peer.queries;
    auto* packet = pbuf_alloc(PBUF_TRANSPORT, bytes->size(), PBUF_RAM);
    if (!packet) {
        ntp_.cancel(peer.index);
        return true;
    }
    if (pbuf_take(packet, bytes->data(), bytes->size()) != ERR_OK ||
        udp_sendto(pcb_, packet, &peer.address, 123) != ERR_OK)
        ntp_.cancel(peer.index);
    pbuf_free(packet);
    return true;
}
void PicoNetwork::poll() {
    if (!initialized_)
        return;
    watchdog_hw->scratch[1] = 13;
    cyw43_arch_poll();
    watchdog_hw->scratch[1] = 14;
    if (!pcb_ || (!enabled_ && !withdrawal_started_us_))
        return;
    const auto now = time_us_64();
    const auto link = cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA);
    if (withdrawal_started_us_) {
        // CYW43 send success means a bus transfer, not an over-air completion.
        // Service the driver without mDNS replies/reconnects for one second.
        // This is a bounded transmission opportunity, never a delivery guarantee.
        if (link != CYW43_LINK_UP || now - *withdrawal_started_us_ >= 1'000'000ULL) {
            watchdog_hw->scratch[1] = 15;
            mdns_.disable(false);
            service_withdrawal_started_us_.reset();
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
    const bool up = link == CYW43_LINK_UP;
    if (up != ntp_link_up_) {
        ntp_link_up_ = up;
        ntp_.online(up, now * 1000);
        // A link change establishes new receive/clock cohorts. Restored drift
        // remains only a prior; stale samples cannot vote in source selection.
        ntp_.reset_peer(false);
        for (auto& peer : peers_)
            peer.lookup.link(up);
    }
    auto* station = &cyw43_state.netif[CYW43_ITF_STA];
    // The pinned CYW43 driver makes every newly enabled interface the default,
    // including the consumer setup AP. Keep off-subnet DNS/SNTP traffic on the
    // connected station; AP-local replies still use their matching subnet.
    if (link == CYW43_LINK_UP && netif_is_up(station) && netif_is_link_up(station) &&
        !ip4_addr_isany_val(*netif_ip4_addr(station)))
        netif_set_default(station);
    if (wsprry_mdns_network_changed())
        mdns_.network_changed();
    if (service_withdrawal_started_us_ &&
        (!link_up() || now - *service_withdrawal_started_us_ >= 1'000'000ULL)) {
        mdns_.disable(false);
        service_withdrawal_started_us_.reset();
    }
    mdns_.poll(enabled_ && (listening_ || consumer_http_) && link_up(),
               link_up() ? ip4_addr_get_u32(netif_ip4_addr(station)) : 0, now);
    if (link != CYW43_LINK_UP) {
        for (auto& peer : peers_)
            ntp_.cancel(peer.index);
        // NOIP still has a working Wi-Fi association. DHCP may temporarily
        // clear the address after a NAK; rejoining here disrupts that exchange.
        if (link == CYW43_LINK_NOIP)
            return;
        if (reconnect_after_leave_us_) {
            if (now < *reconnect_after_leave_us_)
                return;
            reconnect_after_leave_us_.reset();
            watchdog_hw->scratch[1] = 15;
            (void)cyw43_arch_wifi_connect_async(ssid_.c_str(), password_.c_str(),
                                                CYW43_AUTH_WPA2_AES_PSK);
            next_connect_us_ = now + 30'000'000ULL;
        } else if (now >= next_connect_us_) {
            watchdog_hw->scratch[1] = 15;
            if (link == CYW43_LINK_DOWN) {
                (void)cyw43_arch_wifi_connect_async(ssid_.c_str(), password_.c_str(),
                                                    CYW43_AUTH_WPA2_AES_PSK);
                next_connect_us_ = now + 30'000'000ULL;
            } else {
                // Failed and stalled joins can remain latched in the CYW43
                // driver's join state.  A fresh join alone may then keep
                // reporting the old failure after the AP returns.  Explicitly
                // disassociate and give its event one second of poll time
                // before starting the next bounded attempt.
                (void)cyw43_wifi_leave(&cyw43_state, CYW43_ITF_STA);
                reconnect_after_leave_us_ = now + 1'000'000ULL;
                next_connect_us_ = now + 31'000'000ULL;
            }
        }
        return;
    }
    reconnect_after_leave_us_.reset();
    if (!server_literal_)
        resolve_server(now);
    for (auto& peer : peers_) {
        if (peer.index && !pool_enabled_)
            break;
        if (server_literal_ || peer.lookup.ready())
            (void)send_ntp(peer, now);
    }
    (void)ntp_.apply(now * 1000);
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
    for (auto& peer : peers_)
        ntp_.cancel(peer.index);
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
        reconnect_after_leave_us_.reset();
        ntp_.online(true, activity_now_ns());
    } else {
        ntp_.online(false, activity_now_ns());
        for (auto& peer : peers_)
            peer.lookup.link(false);
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
std::string PicoNetwork::pool_status(std::uint64_t now) const {
    const auto tracking = ntp_.engine().tracking(now);
    std::string result =
        "{\"schema\":\"microchrony-sources/1\",\"enabled\":" +
        std::string(pool_enabled_ ? "true" : "false") + ",\"selected_slot\":" +
        (tracking.selected < microchrony::source_capacity ? std::to_string(tracking.selected)
                                                          : "null") +
        ",\"combined_sources\":" + std::to_string(tracking.combined_sources) +
        ",\"utc_updates\":" + std::to_string(discipline_accepted_) + ",\"peers\":[";
    for (const auto& peer : peers_) {
        if (peer.index && !pool_enabled_)
            break;
        if (peer.index)
            result += ',';
        const auto state = ntp_.status(peer.index, now);
        result += "{\"slot\":" + std::to_string(peer.index) +
                  ",\"hostname\":" + wtp::json::quote(peer.hostname) + ",\"endpoint\":" +
                  wtp::json::quote(
                      server_literal_ || peer.lookup.ready() ? ipaddr_ntoa(&peer.address) : "") +
                  ",\"queries\":" + std::to_string(peer.queries) +
                  ",\"accepted\":" + std::to_string(peer.accepted) +
                  ",\"rejected\":" + std::to_string(peer.rejected) + ",\"selection_score_milli\":" +
                  std::to_string(std::uint64_t(std::min(1e9, state.selection_score * 1000))) +
                  ",\"reach\":" + std::to_string(state.reach) +
                  ",\"max_process_us\":" + std::to_string(peer.max_process_us) +
                  ",\"poll_seconds\":" + std::to_string(1U << state.poll) +
                  ",\"selected\":" + (state.selected ? "true" : "false") +
                  ",\"combined\":" + (state.combined ? "true" : "false") +
                  ",\"reason\":" + wtp::json::quote(microchrony::name(state.reason)) + "}";
    }
    return result + "]}";
}
std::string PicoNetwork::status() const {
    const auto* softap = &cyw43_state.netif[CYW43_ITF_AP];
    const auto softap_netif =
        std::string("{\"up\":") + (netif_is_up(softap) ? "true" : "false") +
        ",\"link_up\":" + (netif_is_link_up(softap) ? "true" : "false") +
        ",\"ipv4\":" + wtp::json::quote(ip4addr_ntoa(netif_ip4_addr(softap))) + "}";
    const auto& selected = active_peer();
    const auto uncertainty = ntp_.last_uncertainty_ns();
    std::string tx_guard;
#ifdef WSPRRY_PICO_CYW43_TX_GUARD
    std::uint32_t waits, preserved, timeouts;
    wsprry_cyw43_tx_diagnostics(&waits, &preserved, &timeouts);
    tx_guard = ",\"tx_credit\":{\"waits\":" + std::to_string(waits) +
               ",\"preserved\":" + std::to_string(preserved) +
               ",\"timeouts\":" + std::to_string(timeouts) + "}";
#endif
    return "{\"ntp_observations\":" + ntp_.observations_json() +
           ",\"ntp_rate\":" + time::rate_json(ntp_.rate(activity_now_ns())) +
           ",\"ntp_learning\":" + ntp_.learning_json(activity_now_ns()) +
           ",\"ntp_pool\":" + pool_status(activity_now_ns()) +
           ",\"initialized\":" + std::string(initialized_ ? "true" : "false") +
           ",\"enabled\":" + (enabled_ ? "true" : "false") + ",\"link_status\":" +
           std::to_string(initialized_ ? cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA)
                                       : -99) +
           ",\"ipv4\":" + wtp::json::quote(ipv4()) + ",\"softap_netif\":" + softap_netif +
           ",\"requested_enabled\":" +
           (pending_enabled_ ? (*pending_enabled_ ? "true" : "false") : "null") +
           ",\"withdrawal_pending\":" + (withdrawal_started_us_ ? "true" : "false") +
           ",\"resume_after_withdrawal\":" + (resume_after_withdrawal_ ? "true" : "false") +
           ",\"control_configured\":" + (configured_ ? "true" : "false") +
           ",\"control_listening\":" + (listening_ ? "true" : "false") +
           ",\"consumer_web_ready\":" + (consumer_http_ && link_up() ? "true" : "false") +
           ",\"consumer_web_port\":80" +
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
           tx_guard + ",\"ntp_server\":" + wtp::json::quote(time_server_) + ",\"ntp_address\":" +
           wtp::json::quote(
               server_literal_ || selected.lookup.ready() ? ipaddr_ntoa(&selected.address) : "") +
           ",\"ntp_resolution\":" +
           wtp::json::quote(server_literal_             ? "literal"
                            : selected.lookup.pending() ? "resolving"
                            : selected.lookup.ready()   ? "resolved"
                                                        : "unresolved") +
           ",\"ntp_resolution_failures\":" + std::to_string(resolution_failures_) +
           ",\"queries\":" + std::to_string(queries_) +
           ",\"accepted\":" + std::to_string(accepted_) +
           ",\"rejected\":" + std::to_string(rejected_) +
           ",\"last_rtt_ns\":" + std::to_string(ntp_.last_rtt_ns()) +
           ",\"last_sample_uncertainty_ns\":" +
           (uncertainty ? std::to_string(*uncertainty) : "null") + "}";
}
std::string PicoNetwork::ntp_history_page(std::string_view request,
                                          time::NtpDiagnosticBinding binding) const {
    const auto slot = request.size() >= 3 && request[0] == '@' && request[1] >= '0' &&
                              request[1] <= '3' && request[2] == ' '
                          ? unsigned(request[1] - '0')
                          : ntp_.selected_slot();
    const auto& peer = peers_[slot];
    const std::string endpoint =
        server_literal_ || peer.lookup.ready() ? ipaddr_ntoa(&peer.address) : "";
    binding.slot = peer.index;
    binding.endpoint = endpoint;
    return ntp_.history_page(binding, request, activity_now_ns());
}
std::string PicoNetwork::ntp_packet_page(std::string_view cursor,
                                         time::NtpDiagnosticBinding binding) const {
    return ntp_.packet_page(binding, cursor, activity_now_ns());
}
} // namespace wsprrypico::standalone
