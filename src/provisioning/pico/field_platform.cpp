#include "provisioning/pico/field_platform.hpp"

#include "btstack.h"
#include "hardware/flash.h"
#include "hardware/gpio.h"
#include "hardware/regs/addressmap.h"
#include "lwip/netif.h"
#include "pico/cyw43_arch.h"
#include "pico/flash.h"
#include "pico/rand.h"
#include "standalone/pico/flash_layout.hpp"

#include <algorithm>
#include <array>

namespace wsprrypico::provisioning {
static_assert(CYW43_DEFAULT_IP_AP_ADDRESS == LWIP_MAKEU32(192, 168, 4, 1));

bool PicoRandomSource::fill(std::span<std::uint8_t> bytes) {
    for (std::size_t offset = 0; offset < bytes.size();) {
        const auto random = get_rand_64();
        const auto count = std::min<std::size_t>(sizeof(random), bytes.size() - offset);
        for (std::size_t i = 0; i < count; ++i)
            bytes[offset + i] = static_cast<std::uint8_t>(random >> (i * 8));
        offset += count;
    }
    return true;
}

std::uint64_t PicoBondStore::identity(int index) {
    if (index < 0 || index >= le_device_db_max_count())
        return 0;
    int address_type = BD_ADDR_TYPE_UNKNOWN;
    bd_addr_t address{};
    le_device_db_info(index, &address_type, address, nullptr);
    if (address_type == BD_ADDR_TYPE_UNKNOWN)
        return 0;
    std::uint64_t peer = static_cast<std::uint64_t>(static_cast<unsigned>(address_type) + 1U) << 48;
    for (std::size_t i = 0; i < sizeof(address); ++i)
        peer |= static_cast<std::uint64_t>(address[i]) << (i * 8);
    return peer;
}

bool PicoBondStore::erase(std::uint64_t peer) {
    if (!peer)
        return false;
    const auto before = le_device_db_count();
    for (int index = 0; index < le_device_db_max_count(); ++index) {
        if (identity(index) != peer)
            continue;
        le_device_db_remove(index);
        return le_device_db_count() == before - 1;
    }
    return false;
}

bool PicoBondStore::erase_all() {
    const auto maximum = le_device_db_max_count();
    for (int index = 0; index < maximum; ++index)
        le_device_db_remove(index);
    return le_device_db_count() == 0;
}

bool PicoBondStore::erase_reset_storage() {
    // Called before stack initialization on recovery boot. Never erase a live
    // database: in-memory peers could otherwise repopulate deleted flash.
    using namespace standalone::flash_layout;
    for (std::size_t offset = btstack_base; offset < btstack_base + btstack_size;
         offset += erase_sector_size) {
        auto address = offset;
        auto erase = [](void* p) {
            flash_range_erase(*static_cast<std::size_t*>(p), FLASH_SECTOR_SIZE);
        };
        if (flash_safe_execute(erase, &address, 100) != PICO_OK)
            return false;
    }
    const auto* bytes = reinterpret_cast<const volatile std::uint8_t*>(XIP_BASE + btstack_base);
    for (std::size_t i = 0; i < btstack_size; ++i)
        if (bytes[i] != 255)
            return false;
    return true;
}

bool PicoIndicatorOutput::write(bool on) {
    if (pins_.indicator == hardware::PinPlan::Indicator::Disabled)
        return true;
    if (pins_.indicator == hardware::PinPlan::Indicator::External) {
        if (!hardware::operational(pins_) || !pins_.indicator_gp)
            return false;
        const auto gp = *pins_.indicator_gp;
        if (!initialized_) {
            gpio_init(gp);
            gpio_put(gp, !pins_.indicator_active_high);
            gpio_set_dir(gp, GPIO_OUT);
            initialized_ = true;
        }
        gpio_put(gp, on == pins_.indicator_active_high);
        return true;
    }
    return cyw43_gpio_set(&cyw43_state, CYW43_WL_GPIO_LED_PIN, on) == 0;
}

namespace {
void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
} // namespace

bool PicoSoftAp::start(const LocalIdentity& identity, std::string_view password) {
    return start_impl(identity, password, false);
}

bool PicoSoftAp::start_blank(const LocalIdentity& identity) {
    return start_impl(identity, {}, true);
}

bool PicoSoftAp::start_impl(const LocalIdentity& identity, std::string_view password,
                            bool captive) {
    if (running_ || identity.softap_ssid.empty() || (!captive && !valid_local_password(password)))
        return false;
    if (captive)
        cyw43_arch_enable_ap_mode(identity.softap_ssid.c_str(), nullptr, CYW43_AUTH_OPEN);
    else {
        std::string owned(password);
        cyw43_arch_enable_ap_mode(identity.softap_ssid.c_str(), owned.c_str(),
                                  CYW43_AUTH_WPA2_AES_PSK);
        clear(owned);
    }
    ip_addr_t gateway = IPADDR4_INIT(PP_HTONL(CYW43_DEFAULT_IP_AP_ADDRESS));
    ip_addr_t netmask = IPADDR4_INIT(PP_HTONL(CYW43_DEFAULT_IP_MASK));
    if (captive && !wsprry_captive_dns_init(&dns_, &cyw43_state.netif[CYW43_ITF_AP], &gateway)) {
        cyw43_arch_disable_ap_mode();
        return false;
    }
    if (!wsprry_dhcp_server_init(&dhcp_, &cyw43_state.netif[CYW43_ITF_AP], &gateway, &netmask,
                                 captive)) {
        wsprry_captive_dns_deinit(&dns_);
        cyw43_arch_disable_ap_mode();
        return false;
    }
    running_ = true;
    captive_ = captive;
    return true;
}

void PicoSoftAp::stop() {
    if (running_) {
        wsprry_dhcp_server_deinit(&dhcp_);
        wsprry_captive_dns_deinit(&dns_);
        cyw43_arch_disable_ap_mode();
    }
    running_ = false;
    captive_ = false;
}

bool PicoSoftAp::ready() const {
    return running_ && wsprry_dhcp_server_ready(&dhcp_) &&
           (!captive_ || wsprry_captive_dns_ready(&dns_)) &&
           netif_is_up(&cyw43_state.netif[CYW43_ITF_AP]);
}
} // namespace wsprrypico::provisioning
