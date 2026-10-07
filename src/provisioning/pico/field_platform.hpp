#pragma once

#include "hardware/pins.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/pico/captive_dns.h"
#include "provisioning/pico/dhcp_server.h"
#include "provisioning/pico/indicator_output.hpp"

#include <string>

namespace wsprrypico::provisioning {
class PicoRandomSource final : public RandomSource {
  public:
    bool fill(std::span<std::uint8_t> bytes) override;
};

class PicoBondStore final : public BondStore {
  public:
    static std::uint64_t identity(int index);
    bool erase(std::uint64_t peer) override;
    bool erase_all() override;
    bool erase_reset_storage();
};

class PicoSoftAp {
  public:
    bool start(const LocalIdentity& identity, std::string_view password);
    bool start_blank(const LocalIdentity& identity);
    void stop();
    bool ready() const;
    bool running() const {
        return running_;
    }
    bool captive() const {
        return running_ && captive_;
    }

  private:
    bool start_impl(const LocalIdentity& identity, std::string_view password, bool captive);
    wsprry_dhcp_server_t dhcp_{};
    wsprry_captive_dns_t dns_{};
    bool running_ = false;
    bool captive_ = false;
};
} // namespace wsprrypico::provisioning
