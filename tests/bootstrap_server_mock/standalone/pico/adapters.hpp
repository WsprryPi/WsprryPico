#pragma once
#include <string>
#include <string_view>
namespace wsprrypico::standalone {
// Only the radio/association boundary is doubled. Dispatcher, trial gates,
// cryptography and journals are the production implementations.
class PicoNetwork {
  public:
    bool linked = true, start_ok = true;
    unsigned starts = 0, stops = 0;
    std::string ssid = "test-network", password = "test-password";
    std::string address = "192.168.1.53", hostname = "wsprrypico-0a60df.local";
    bool start_network_only(std::string_view s, std::string_view p, std::string_view) {
        ++starts;
        ssid = s;
        password = p;
        return start_ok;
    }
    void stop_network_only_trial() {
        ++stops;
    }
    bool link_up() const {
        return linked;
    }
    std::string ipv4() const {
        return linked ? address : std::string{};
    }
    std::string_view station_ssid() const {
        return ssid;
    }
    std::string_view configured_hostname() const {
        return hostname;
    }
};
} // namespace wsprrypico::standalone
