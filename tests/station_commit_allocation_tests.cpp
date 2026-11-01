// Deny all C++ allocation after the durable commit. Publication and verification
// must still finish, including first-use Config creation and long credentials.
#include "network_support.hpp"
#include "provisioning/local_settings.hpp"

#include <cstdlib>
#include <new>

using namespace wsprrypico;
namespace {
bool deny_allocations = false;
struct Media : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> bytes;
    bool deny_after_commit = false;
    Media() {
        bytes.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        std::copy_n(bytes.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        std::fill_n(bytes.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        std::copy(in.begin(), in.end(), bytes.begin() + at);
        if (deny_after_commit &&
            at % provisioning::profile_slot_size ==
                provisioning::profile_slot_size - provisioning::profile_page_size)
            deny_allocations = true;
        return true;
    }
};
struct Flash : network_test::Flash {
    bool deny_after_commit = false;
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        const auto result = network_test::Flash::program(at, in);
        if (result && deny_after_commit && at % 2048 == 1792)
            deny_allocations = true;
        return result;
    }
};
} // namespace
void* operator new(std::size_t size) {
    if (deny_allocations)
        throw std::bad_alloc();
    if (auto* p = std::malloc(size ? size : 1))
        return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) {
    return ::operator new(size);
}
void operator delete(void* p) noexcept {
    std::free(p);
}
void operator delete[](void* p) noexcept {
    std::free(p);
}
void operator delete(void* p, std::size_t) noexcept {
    std::free(p);
}
void operator delete[](void* p, std::size_t) noexcept {
    std::free(p);
}
int main() {
    Media media;
    provisioning::ProfileStore profiles(media);
    provisioning::RuntimeProfile runtime;
    Flash flash, draft_flash;
    standalone::Store store(flash);
    standalone::Progress progress(draft_flash);
    const std::string device(32, 'a');
    provisioning::ConsumerProfile profile;
    profile.device_id = device;
    profile.ssid = "retained-network-with-long-name";
    profile.password = "retained-passphrase-with-long-value";
    profile.time_server = "192.0.2.1";
    profile.callsign = "AA0NT";
    profile.locator = "EM18";
    profile.power_dbm = 37;
    profile.tls_pending = true;
    profile.tls.hostname = "wsprrypico-test.local";
    profile.request_sha256 = std::string(64, 'a');
    REQUIRE(profiles.load() && store.load() && progress.load());
    REQUIRE(profiles.select(provisioning::ProfileSource::ConsumerProfile,
                            provisioning::serialize_consumer_profile(profile)));
    REQUIRE(runtime.load(profiles, device, provisioning::BuildBundleState::Absent));
    provisioning::LocalSettings settings(profiles, runtime, store, progress, device,
                                         "wsprrypico-test.local");
    auto candidate = *runtime.overlay(standalone::factory_config());
    media.deny_after_commit = true;
    const auto error = settings.station_save(candidate);
    deny_allocations = false;
    REQUIRE(error.empty() && runtime.control_healthy(profiles));
    REQUIRE(runtime.session_generation_current(1, profiles));
    REQUIRE(runtime.consumer_profile()->password == profile.password);
    REQUIRE(runtime.consumer_profile()->request_sha256 == profile.request_sha256);
    candidate.power_dbm = 0;
    flash.deny_after_commit = true;
    REQUIRE(store.save(candidate));
    deny_allocations = false;
    REQUIRE(store.config() == candidate);
    Flash first_flash;
    standalone::Store first(first_flash);
    REQUIRE(first.load() && !first.config());
    first_flash.deny_after_commit = true;
    REQUIRE(first.save(candidate));
    deny_allocations = false;
    REQUIRE(first.config() == candidate);
    standalone::Store cold(flash);
    REQUIRE(cold.load() && cold.config() == candidate);
}
