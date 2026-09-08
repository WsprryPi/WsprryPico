#include "standalone/pico/adapters.hpp"

#include "hardware/flash.h"
#include "hardware/structs/watchdog.h"
#include "hardware/sync.h"
#include "lwip/netif.h"
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
PicoNetwork::PicoNetwork(time::UtcDiscipline& clock, std::string_view device_id,
                         std::string_view configured_hostname)
    : sntp_(clock), mdns_(*this, configured_hostname),
      stable_hostname_(network::default_hostname(device_id)) {}
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
void PicoNetwork::mdns_result(struct netif* interface, u8_t result, s8_t slot) {
    if (mdns_owner && interface == &cyw43_state.netif[CYW43_ITF_STA] && slot == 0)
        mdns_owner->mdns_.name_result(result == MDNS_PROBING_SUCCESSFUL);
}
bool PicoNetwork::start(const Config& config) {
    if (initialized_ || !ipaddr_aton(config.ntp_ipv4.c_str(), &server_))
        return false;
    watchdog_hw->scratch[1] = 10;
    if (cyw43_arch_init())
        return false;
    initialized_ = true;
    watchdog_hw->scratch[1] = 11;
    cyw43_arch_enable_sta_mode();
    watchdog_hw->scratch[1] = 12;
    ssid_ = config.ssid;
    password_ = config.password;
    pcb_ = udp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb_) {
        cyw43_arch_disable_sta_mode();
        cyw43_arch_deinit();
        initialized_ = false;
        return false;
    }
    udp_recv(pcb_, receive, this);
    return true;
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
    if (!initialized_ || !pcb_ || !enabled_)
        return;
    watchdog_hw->scratch[1] = 13;
    cyw43_arch_poll();
    watchdog_hw->scratch[1] = 14;
    const auto now = time_us_64();
    const auto link = cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA);
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
bool PicoNetwork::set_enabled(bool enabled) {
    if (!initialized_ || !pcb_)
        return false;
    if (enabled_ == enabled)
        return true;
    sntp_.cancel();
    enabled_ = enabled;
    if (enabled) {
        mdns_.retry();
        cyw43_arch_enable_sta_mode();
        next_connect_us_ = 0;
        poll_schedule_.reset();
    } else {
        // enabled_ was already changed; inspect the actual station before teardown.
        mdns_.disable(cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP);
        cyw43_arch_disable_sta_mode();
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
           ",\"control_configured\":" + (configured_ ? "true" : "false") +
           ",\"control_listening\":" + (listening_ ? "true" : "false") +
           ",\"deployment_identity_matches\":" + (identity_matches_ ? "true" : "false") +
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
           ",\"queries\":" + std::to_string(queries_) +
           ",\"accepted\":" + std::to_string(accepted_) +
           ",\"rejected\":" + std::to_string(rejected_) +
           ",\"last_rtt_ns\":" + std::to_string(sntp_.last_rtt_ns()) +
           ",\"last_sample_uncertainty_ns\":" +
           (uncertainty ? std::to_string(*uncertainty) : "null") + "}";
}
} // namespace wsprrypico::standalone
