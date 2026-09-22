#include "provisioning/activation.hpp"
#include "provisioning/ble_session.hpp"
#include "provisioning/command.hpp"
#include "provisioning/pico/field_platform.hpp"
#include "provisioning/pico/gatt_transport.hpp"
#include "provisioning/softap_http.hpp"
#include "provisioning/storage.hpp"
#include "standalone/pico/flash_layout.hpp"
#include "time/controller_time.hpp"

#include <span>

namespace {
using namespace wsprrypico::provisioning;
class ProfileMedia final : public Media {
  public:
    bool read(std::size_t, std::span<std::uint8_t>) override { return false; }
    bool erase(std::size_t) override { return false; }
    bool program(std::size_t, std::span<const std::uint8_t>) override { return false; }
};
class AccessBytes final : public AccessMedia {
  public:
    bool read(std::size_t, std::span<std::uint8_t>) override { return false; }
    bool erase(std::size_t) override { return false; }
    bool program(std::size_t, std::span<const std::uint8_t>) override { return false; }
};
class Validator final : public CredentialValidator {
  public:
    bool validate(const Profile&) override { return false; }
};
class Platform final : public ActivationPlatform {
  public:
    bool prepare(const Profile&, std::uint64_t) override { return false; }
    Activity activity() const override { return {}; }
    bool quiesce() override { return false; }
    bool install(const Profile&, std::uint64_t) override { return false; }
    bool restart() override { return false; }
    bool fail_closed(std::uint64_t) override { return true; }
};
Activity activity(void*) { return {}; }
std::uint64_t now(void*) { return 0; }
using GattStart = bool (PicoGattTransport::*)();
using GattPoll = void (PicoGattTransport::*)();
using SoftApStart = bool (PicoSoftAp::*)(const LocalIdentity&, std::string_view);
using LedWrite = bool (PicoIndicatorOutput::*)(bool);
using HttpLogin = SoftApHttpResponse (SoftApHttpAdmission::*)(
    const wsprrypico::network::HttpRequest&, SoftApSurface, std::string_view, std::uint64_t);
using TimeSubmit = wsprrypico::time::ControllerTimeCode
    (wsprrypico::time::ControllerTimeArbiter::*)(std::string_view, std::string_view,
                                                std::string_view, std::string_view,
                                                std::uint64_t);
GattStart volatile retained_gatt_start = &PicoGattTransport::start;
GattPoll volatile retained_gatt_poll = &PicoGattTransport::poll;
SoftApStart volatile retained_softap_start = &PicoSoftAp::start;
LedWrite volatile retained_led_write = &PicoIndicatorOutput::write;
PicoIndicatorOutput retained_led_instance;
IndicatorOutput* volatile retained_led_interface = &retained_led_instance;
HttpLogin volatile retained_http_login = &SoftApHttpAdmission::login;
TimeSubmit volatile retained_time_submit = &wsprrypico::time::ControllerTimeArbiter::submit;
} // namespace

int main() {
    using namespace wsprrypico;
    using namespace provisioning;
    static_assert(standalone::flash_layout::access_base == 0x3f3000);
    static_assert(standalone::flash_layout::access_size == 0x2000);
    static_assert(standalone::flash_layout::btstack_base == 0x3f5000);
    static_assert(standalone::flash_layout::btstack_size == 0x2000);
    const std::string device = "00112233445566778899aabbccddeeff";
    const auto identity = derive_local_identity(device, "02:11:22:0a:60:df");
    if (!identity) return 1;
    ProfileMedia profile_media;
    ProfileStore profile_store(profile_media);
    AccessBytes access_bytes;
    AccessStore access_store(access_bytes);
    PicoBondStore bonds;
    PicoRandomSource random;
    LocalAccessController access(access_store, bonds, random, device, "link-boot", *identity);
    Validator validator;
    Platform platform;
    ActivationCoordinator activation(platform);
    Manager manager(profile_store, validator, device, &activation);
    CommandAdapter command(manager, device, Transport::Ble);
    BleCommandSession session(access, command, manager, device, activity, nullptr);
    PicoGattTransport gatt(session, command.identity(), identity->advertising_name, now, nullptr);
    PicoIndicatorOutput led;
    PicoSoftAp softap;
    std::size_t retained = gatt.running() || softap.running() || session.authorized();
    retained += sizeof(led);
    return retained == static_cast<std::size_t>(-1) || retained_gatt_start == nullptr ||
           retained_gatt_poll == nullptr || retained_softap_start == nullptr ||
           retained_led_write == nullptr ||
           retained_led_interface == nullptr ||
           retained_http_login == nullptr || retained_time_submit == nullptr;
}
