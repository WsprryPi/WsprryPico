#pragma once
#include "lwip/udp.h"
#ifndef WSPRRY_PICO_STANDALONE_RF
#include "standalone/pico/net_trace.hpp"
#endif
#include "network/api.hpp"
#include "network/mdns.hpp"
#include "provisioning/access.hpp"
#include "provisioning/storage.hpp"
#include "standalone/storage.hpp"
#include "time/server_lookup.hpp"
#include "time/sntp.hpp"

namespace wsprrypico::standalone {
class PicoFlash final : public Flash {
  public:
    bool read(std::size_t offset, std::span<std::uint8_t> data) override;
    bool erase(std::size_t sector_offset) override;
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override;
};
class PicoProfileMedia final : public provisioning::Media {
  public:
    bool read(std::size_t offset, std::span<std::uint8_t> data) override;
    bool erase(std::size_t slot_offset) override;
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override;
};
class PicoAccessMedia final : public provisioning::AccessMedia {
  public:
    bool read(std::size_t offset, std::span<std::uint8_t> data) override;
    bool erase(std::size_t slot_offset) override;
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override;
};
class PicoNetwork : public network::NetworkControl, private network::MdnsAdapter {
  public:
    PicoNetwork(time::ObservationSink& clock, std::string_view configured_hostname);
    bool start(const Config& config);
    bool initialize_radio();
#ifndef WSPRRY_PICO_STANDALONE_RF
    std::string trace_page(std::uint64_t after) const { return trace_.page(after); }
    std::string association();
#endif
    void poll();
    bool set_enabled(bool enabled) override;
    bool request_enabled(bool enabled) override;
    void finish_request(bool idle) override;
    std::string status() const override;
    bool link_up() const;
    std::string ipv4() const;
    bool initialized() const {
        return initialized_;
    }
    const std::string& station_mac() const { return station_mac_; }
    const std::string& stable_hostname() const { return stable_hostname_; }
    // Register the same certified local hostname on the AP netif. The AP has
    // an independent responder record but shares the one bounded lwIP mDNS PCB.
    bool softap_name(bool enabled, std::string_view hostname);
    void listener_status(bool configured, bool listening, bool identity_matches = true) {
        configured_ = configured;
        listening_ = listening;
        identity_matches_ = identity_matches;
        if (!identity_matches)
            mdns_.identity_failure();
    }

  private:
#ifndef WSPRRY_PICO_STANDALONE_RF
    NetTrace trace_;
    void trace_mark(unsigned code) { trace_.mark(code); }
    void trace_install();
#else
    void trace_mark(unsigned) {}
    void trace_install() {}
#endif
    bool disable_power_save();
    bool initialize() override;
    bool add(std::string_view label) override;
    void withdraw() override;
    void remove(bool goodbye) override;
    static void mdns_result(struct netif*, u8_t result, s8_t slot);
    static void receive(void* context, udp_pcb*, pbuf* packet, const ip_addr_t* address,
                        u16_t port);
    static void resolved(const char* name, const ip_addr_t* address, void* context);
    void resolve_server(std::uint64_t now);
    time::Sntp sntp_;
    network::Mdns mdns_;
    std::string station_mac_, stable_hostname_;
    time::SntpPollSchedule poll_schedule_;
    udp_pcb* pcb_ = nullptr;
    ip_addr_t server_{};
    std::string time_server_;
    time::ServerLookup lookup_;
    std::uint64_t lookup_epoch_ = 0;
    bool server_literal_ = false;
    std::uint32_t resolution_failures_ = 0;
    std::string ssid_, password_;
    std::uint64_t next_connect_us_ = 0;
    std::optional<std::uint64_t> reconnect_after_leave_us_;
    bool initialized_ = false, enabled_ = false;
    std::optional<bool> power_save_;
    std::optional<bool> pending_enabled_;
    std::optional<std::uint64_t> withdrawal_started_us_;
    bool resume_after_withdrawal_ = false;
    bool configured_ = false, listening_ = false;
    bool identity_matches_ = true;
    std::string softap_hostname_;
    bool mdns_initialized_ = false;
    bool softap_mdns_registered_ = false;
    bool softap_mdns_active_ = false;
    bool softap_mdns_conflict_ = false;
    std::uint32_t queries_ = 0, accepted_ = 0, rejected_ = 0;
};
} // namespace wsprrypico::standalone
