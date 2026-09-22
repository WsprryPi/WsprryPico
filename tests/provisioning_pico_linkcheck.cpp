#include "network/pico/psa_lifetime.hpp"
#include "provisioning/activation.hpp"
#include "provisioning/command.hpp"
#include "provisioning/pico/credential_validator.hpp"
#include "standalone/pico/flash_layout.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>

namespace {
using namespace wsprrypico::provisioning;

class LinkMedia final : public Media {
  public:
    bool read(std::size_t, std::span<std::uint8_t>) override {
        return false;
    }
    bool erase(std::size_t) override {
        return false;
    }
    bool program(std::size_t, std::span<const std::uint8_t>) override {
        return false;
    }
};

class LinkActivationPlatform final : public ActivationPlatform {
  public:
    bool prepare(const Profile&, std::uint64_t) override {
        return true;
    }
    Activity activity() const override {
        return {};
    }
    bool quiesce() override {
        return true;
    }
    bool install(const Profile&, std::uint64_t) override {
        return true;
    }
    bool restart() override {
        return true;
    }
    bool fail_closed(std::uint64_t) override {
        return true;
    }
};
} // namespace

int main() {
    using namespace wsprrypico;
    using namespace provisioning;

    static_assert(standalone::flash_layout::access_base == 0x3f3000);
    static_assert(standalone::flash_layout::access_size == 0x2000);
    static_assert(standalone::flash_layout::btstack_base == 0x3f5000);
    static_assert(standalone::flash_layout::btstack_size == 0x2000);

    LinkMedia media;
    ProfileStore store(media);
    MbedTlsCredentialValidator validator("linkcheck-device");
    LinkActivationPlatform platform;
    ActivationCoordinator activation(platform);
    Manager manager(store, validator, "linkcheck-device", &activation);
    CommandAdapter command(manager, "linkcheck-device", Transport::Ble);

    Profile profile;
    profile.device_id = "linkcheck-device";
    profile.hostname = "linkcheck-device.local";
    profile.port = 443;

    std::size_t retained = command.identity().size();
    const Authorization authorization{};
    const Activity activity{};
    retained += command.handle("{}", authorization, activity, 0).notification.size();
    retained += validator.validate(profile) ? 1u : 0u;
    retained += activation.stage("linkcheck-request", profile, 1, 0) ? 1u : 0u;
    retained += static_cast<std::size_t>(
        manager.release_activation("stale-request", 0, 0));
    manager.poll(activation_delivery_timeout_ms);
    retained += static_cast<std::size_t>(manager.status().activation.state);
    network::PsaCryptoOwner psa;
    retained += psa.acquire() == PSA_SUCCESS ? 1u : 0u;
    psa.release();
    retained += network::PsaCryptoOwner::owners();
    retained += network::PsaCryptoOwner::peak_owners();

    return retained == static_cast<std::size_t>(-1);
}
