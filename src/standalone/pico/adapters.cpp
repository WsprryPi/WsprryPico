#include "standalone/pico/adapters.hpp"

#include "hardware/flash.h"
#include "hardware/structs/watchdog.h"
#include "hardware/sync.h"
#include "pico/cyw43_arch.h"
#include "pico/rand.h"
#include "pico/time.h"

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
    // Single-core polling architecture; no second core or background CYW43 IRQ
    // accesses XIP. Callers must exclude armed/running jobs before flash writes.
    const auto irq = save_and_disable_interrupts();
    flash_range_erase(flash_base + offset, FLASH_SECTOR_SIZE);
    restore_interrupts(irq);
    const auto* bytes = reinterpret_cast<const std::uint8_t*>(XIP_BASE + flash_base + offset);
    return std::all_of(bytes, bytes + FLASH_SECTOR_SIZE, [](auto b) { return b == 255; });
}
bool PicoFlash::program(std::size_t offset, std::span<const std::uint8_t> page) {
    if (offset % FLASH_PAGE_SIZE || page.size() != FLASH_PAGE_SIZE ||
        offset > storage_size - FLASH_PAGE_SIZE)
        return false;
    const auto irq = save_and_disable_interrupts();
    flash_range_program(flash_base + offset, page.data(), page.size());
    restore_interrupts(irq);
    return true; // Journal independently verifies the complete record.
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
    if (!pcb_)
        return false;
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
bool PicoNetwork::set_enabled(bool enabled) {
    if (!initialized_ || !pcb_)
        return false;
    if (enabled_ == enabled)
        return true;
    sntp_.cancel();
    enabled_ = enabled;
    if (enabled) {
        cyw43_arch_enable_sta_mode();
        next_connect_us_ = 0;
        poll_schedule_.reset();
    } else
        cyw43_arch_disable_sta_mode();
    return true;
}
std::string PicoNetwork::status() const {
    const auto uncertainty = sntp_.last_uncertainty_ns();
    return "{\"initialized\":" + std::string(initialized_ ? "true" : "false") +
           ",\"enabled\":" + (enabled_ ? "true" : "false") + ",\"link_status\":" +
           std::to_string(initialized_ ? cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA)
                                       : -99) +
           ",\"queries\":" + std::to_string(queries_) +
           ",\"accepted\":" + std::to_string(accepted_) +
           ",\"rejected\":" + std::to_string(rejected_) +
           ",\"last_rtt_ns\":" + std::to_string(sntp_.last_rtt_ns()) +
           ",\"last_sample_uncertainty_ns\":" +
           (uncertainty ? std::to_string(*uncertainty) : "null") + "}";
}
} // namespace wsprrypico::standalone
