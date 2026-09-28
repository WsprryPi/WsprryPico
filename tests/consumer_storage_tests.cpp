#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/network_profile.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <string>

using namespace wsprrypico;

namespace {
constexpr auto device = "fd6127d11d6aca42a9905fa3fb1bf1d5";

struct MemoryMedia : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> data{};
    unsigned program_calls = 0;
    unsigned fail_program_call = 0;
    MemoryMedia() {
        data.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset > data.size() || out.size() > data.size() - offset)
            return false;
        std::copy_n(data.begin() + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        assert(offset % provisioning::profile_slot_size == 0);
        assert(offset <= data.size() - provisioning::profile_slot_size);
        std::fill_n(data.begin() + offset, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        assert(offset % provisioning::profile_page_size == 0);
        assert(page.size() == provisioning::profile_page_size);
        assert(offset <= data.size() - page.size());
        if (++program_calls == fail_program_call)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i) {
            assert((data[offset + i] & page[i]) == page[i]);
            data[offset + i] &= page[i];
        }
        return true;
    }
};

provisioning::ConsumerProfile consumer(std::string_view device_id = device) {
    provisioning::ConsumerProfile value;
    value.device_id = device_id;
    value.owner_epoch = 1;
    std::array<std::uint8_t, 65> point{};
    point[0] = 4;
    point[64] = 1;
    value.owners = {network::bootstrap_b64url(point)};
    value.ssid = "Home Net";
    value.password = "test-password";
    value.time_server = "time.example.org";
    value.callsign = "K1ABC";
    value.locator = "FN20";
    value.power_dbm = 30;
    value.tls.hostname = "wsprrypico-0a60df.local";
    value.tls.ca_certificate = "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
    value.tls.server_certificate = value.tls.ca_certificate;
    value.tls.ca_private_key = "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
    value.tls.server_private_key = value.tls.ca_private_key;
    value.tls.ca_not_after_utc = 2'000'000'000;
    value.tls.server_not_after_utc = 1'800'000'000;
    value.request_sha256 = std::string(64, 'a');
    return value;
}
} // namespace

int main() {
    const auto network_payload =
        provisioning::serialize_network_profile({device, "Home Net", "test-password"});
    auto profile = consumer();
    const auto payload = provisioning::serialize_consumer_profile(profile);
    assert(!payload.empty());

    MemoryMedia blank;
    provisioning::ProfileStore direct(blank);
    assert(direct.load());
    assert(direct.select(provisioning::ProfileSource::ConsumerProfile, payload));
    assert(direct.sequence() == 1);
    provisioning::ProfileStore direct_readback(blank);
    assert(direct_readback.load() && direct_readback.data() == payload);
    provisioning::RuntimeProfile preclock;
    assert(preclock.load(direct_readback, device, provisioning::BuildBundleState::Absent));
    assert(preclock.source() == provisioning::RuntimeSource::ConsumerPreClock);
    assert(preclock.consumer_profile() && preclock.consumer_profile()->device_id == device);
    assert(!preclock.profile() && !preclock.network_profile());
    const standalone::Config empty_config{};
    const auto selected = preclock.overlay(empty_config);
    assert(selected && selected->ssid == "Home Net" && selected->password == "test-password");
    assert(selected->callsign == "K1ABC" && selected->locator == "FN20");
    assert(selected->schedules == empty_config.schedules && !selected->enabled);
    auto retained = empty_config;
    retained.enabled = true;
    retained.expires_utc_s = 1'900'000'000;
    retained.schedules = {{120, 0}};
    const auto retained_overlay = preclock.overlay(retained);
    assert(retained_overlay && retained_overlay->enabled == retained.enabled);
    assert(retained_overlay->expires_utc_s == retained.expires_utc_s);
    assert(retained_overlay->schedules == retained.schedules);
    provisioning::RuntimeProfile wrong_device;
    assert(!wrong_device.load(direct_readback, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                              provisioning::BuildBundleState::Absent));
    assert(wrong_device.source() == provisioning::RuntimeSource::Fault);
    assert(wrong_device.fault() == provisioning::RuntimeFault::WrongDevice);
    assert(!wrong_device.consumer_profile());

    MemoryMedia after_reset;
    provisioning::ProfileStore tombstone(after_reset);
    assert(tombstone.load());
    assert(tombstone.select(provisioning::ProfileSource::Unprovisioned));
    assert(tombstone.sequence() == 1);
    assert(preclock.load(tombstone, device, provisioning::BuildBundleState::Absent));
    assert(preclock.source() == provisioning::RuntimeSource::Unprovisioned);
    assert(!preclock.consumer_profile() && !preclock.overlay(empty_config));
    assert(tombstone.select(provisioning::ProfileSource::ConsumerProfile, payload));
    assert(tombstone.sequence() == 2);
    assert(preclock.load(tombstone, device, provisioning::BuildBundleState::Absent));
    assert(preclock.source() == provisioning::RuntimeSource::ConsumerPreClock);
    assert(preclock.generation() == 2);

    MemoryMedia media;
    provisioning::ProfileStore initial(media);
    assert(initial.load());
    assert(initial.select(provisioning::ProfileSource::NetworkOnly, network_payload));
    assert(initial.sequence() == 1);
    // Re-entering the same Wi-Fi settings is still a distinct browser save.
    MemoryMedia repeat_media;
    provisioning::ProfileStore repeat(repeat_media);
    assert(repeat.load());
    assert(repeat.select(provisioning::ProfileSource::NetworkOnly, network_payload));
    assert(repeat.select(provisioning::ProfileSource::NetworkOnly, network_payload));
    assert(repeat.sequence() == 2);
    provisioning::ProfileStore repeat_readback(repeat_media);
    assert(repeat_readback.load() && repeat_readback.sequence() == 2 &&
           repeat_readback.data() == network_payload);
    const auto base = media;
    const auto pages = (payload.size() + 16 + provisioning::profile_page_size - 1) /
                       provisioning::profile_page_size;
    for (unsigned cut = 1; cut <= pages + 2; ++cut) {
        auto trial = base;
        provisioning::ProfileStore transaction(trial);
        assert(transaction.load());
        trial.fail_program_call = trial.program_calls + cut;
        assert(!transaction.select(provisioning::ProfileSource::ConsumerProfile, payload));
        provisioning::ProfileStore recovered(trial);
        assert(recovered.load());
        assert(recovered.source() == provisioning::ProfileSource::NetworkOnly);
        assert(recovered.sequence() == 1 && recovered.data() == network_payload);
    }

    provisioning::ProfileStore upgraded(media);
    assert(upgraded.load());
    assert(upgraded.select(provisioning::ProfileSource::ConsumerProfile, payload));
    assert(upgraded.sequence() == 2);
    provisioning::ProfileStore recovered(media);
    assert(recovered.load());
    assert(recovered.source() == provisioning::ProfileSource::ConsumerProfile);
    assert(recovered.sequence() == 2 && recovered.data() == payload);
    assert(!recovered.select(provisioning::ProfileSource::RuntimeProfile, payload));
    assert(!recovered.select(provisioning::ProfileSource::BuildBundle));
    assert(!recovered.select(static_cast<provisioning::ProfileSource>(6)));
    assert(!recovered.select(provisioning::ProfileSource::ConsumerProfile, "{}"));
    auto other = consumer("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    assert(!recovered.select(provisioning::ProfileSource::ConsumerProfile,
                             provisioning::serialize_consumer_profile(other)));
    profile.owner_epoch = 2;
    profile.request_sha256 = std::string(64, 'b');
    const auto replacement = provisioning::serialize_consumer_profile(profile);
    assert(recovered.select(provisioning::ProfileSource::ConsumerProfile, replacement));
    assert(recovered.sequence() == 3);
    profile.owner_epoch = 1;
    profile.request_sha256 = std::string(64, 'c');
    assert(!recovered.select(provisioning::ProfileSource::ConsumerProfile,
                             provisioning::serialize_consumer_profile(profile)));
    profile.owner_epoch = 3;
    profile.request_sha256 = std::string(64, 'b');
    assert(!recovered.select(provisioning::ProfileSource::ConsumerProfile,
                             provisioning::serialize_consumer_profile(profile)));
    assert(recovered.select(provisioning::ProfileSource::ConsumerProfile, replacement));
    assert(recovered.sequence() == 3);

    auto corrupt = media;
    const auto newest_payload =
        recovered.active_slot() * provisioning::profile_slot_size + provisioning::profile_page_size;
    corrupt.data[newest_payload + 20] ^= 1;
    provisioning::ProfileStore invalid_newest(corrupt);
    assert(!invalid_newest.load());

    MemoryMedia bundle_media;
    provisioning::ProfileStore bundle(bundle_media);
    assert(bundle.load() && bundle.select(provisioning::ProfileSource::BuildBundle));
    assert(!bundle.select(provisioning::ProfileSource::ConsumerProfile, payload));
    provisioning::scrub(profile);
    provisioning::scrub(other);
}
