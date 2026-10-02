#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/reset_storage.hpp"

#include <algorithm>
#include <array>
#include <cassert>
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
struct Flash : standalone::Flash {
    std::array<std::uint8_t, 16384> data{};
    int erases_until_fail = -1;
    int program_budget = -1;
    Flash() {
        data.fill(255);
    }
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        std::copy_n(data.begin() + o, b.size(), b.begin());
        return true;
    }
    bool erase(std::size_t o) override {
        if (erases_until_fail == 0) {
            std::fill_n(data.begin() + o, 2048, 255);
            return false;
        }
        if (erases_until_fail > 0)
            --erases_until_fail;
        std::fill_n(data.begin() + o, 4096, 255);
        return true;
    }
    bool program(std::size_t o, std::span<const std::uint8_t> b) override {
        if (program_budget == 0) {
            for (std::size_t i = 0; i < b.size() / 2; ++i)
                data[o + i] &= b[i];
            return false;
        }
        if (program_budget > 0)
            --program_budget;
        for (std::size_t i = 0; i < b.size(); ++i)
            data[o + i] &= b[i];
        return true;
    }
};
struct Bonds : provisioning::BondStore {
    bool erase(std::uint64_t) override {
        return true;
    }
    bool erase_all() override {
        return true;
    }
};
struct AccessMemory : provisioning::AccessMedia {
    std::array<std::uint8_t, provisioning::access_media_size> data{};
    AccessMemory() {
        data.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        std::copy_n(data.begin() + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        std::fill_n(data.begin() + offset, provisioning::access_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        for (std::size_t i = 0; i < page.size(); ++i)
            data[offset + i] &= page[i];
        return true;
    }
};
struct Reboot {};
provisioning::ResetCheckpoint cut_stage;
void cut(provisioning::ResetCheckpoint stage) {
    if (stage == cut_stage)
        throw Reboot{};
}
provisioning::Activity idle(void*) {
    return {};
}
} // namespace
int main() {
    // Each named target checkpoint must have durable authority that survives
    // destruction/reconstruction of all stores. Cut both destructive levels.
    for (auto level : {provisioning::ResetLevel::Provisioning, provisioning::ResetLevel::Full}) {
        for (unsigned stage = 1; stage <= 7; ++stage) {
            Flash target_flash;
            MemoryMedia target_media;
            AccessMemory access_media;
            Bonds target_bonds;
            const auto identity = *provisioning::derive_local_identity(device, "02:00:00:00:00:01");
            {
                standalone::Store target_store(target_flash);
                assert(target_store.load());
                auto config = standalone::Config{};
                config.callsign = "W1OLD";
                config.locator = "FN31";
                config.enabled = true;
                config.schedules = {{120, 0}};
                assert(target_store.save(config));
                assert(target_store.reserve(1800000000000000000ULL));
                provisioning::ProfileStore target_profiles(target_media);
                assert(target_profiles.load());
                assert(
                    target_profiles.select(provisioning::ProfileSource::ConsumerProfile,
                                           provisioning::serialize_consumer_profile(consumer())));
                provisioning::AccessStore access(access_media);
                assert(access.load());
                provisioning::AccessRecord record;
                record.epoch = 1;
                record.password = identity.default_password;
                assert(access.initialize(record));
                record.bonds[0] = 42;
                record.bond_count = 1;
                assert(access.replace(record));
                provisioning::ResetStorageTargets target(target_store, target_flash, target_media,
                                                         target_bonds, idle, nullptr);
                provisioning::ResetCoordinator reset(access, target_profiles, target, identity);
                reset.checkpoint_observer(cut);
                cut_stage = static_cast<provisioning::ResetCheckpoint>(stage);
                wtp::PayloadDigest digest{};
                digest[0] = 1;
                bool fired = false;
                try {
                    assert(reset.begin(level, provisioning::ProfileSource::Unprovisioned, digest) ==
                           provisioning::ResetResult::Pending);
                    (void)reset.resume();
                } catch (const Reboot&) {
                    fired = true;
                }
                assert(fired);
            }
            standalone::Store recovered(target_flash);
            assert(recovered.load());
            provisioning::ProfileStore recovered_profiles(target_media);
            assert(recovered_profiles.load());
            provisioning::AccessStore recovered_access(access_media);
            assert(recovered_access.load());
            provisioning::ResetStorageTargets targets(recovered, target_flash, target_media,
                                                      target_bonds, idle, nullptr);
            provisioning::ResetCoordinator resumed(recovered_access, recovered_profiles, targets,
                                                   identity);
            assert(resumed.resume() == provisioning::ResetResult::Complete);
            assert(!resumed.pending());
            assert(recovered_access.record()->epoch == 2);
            assert(recovered_access.record()->bond_count == 0);
            assert(recovered_profiles.source() == provisioning::ProfileSource::Unprovisioned);
            if (level == provisioning::ResetLevel::Full) {
                assert(!recovered.config() && recovered.watermark() == 0);
            } else {
                assert(recovered.config()->callsign == consumer().callsign);
                assert(recovered.config()->locator == consumer().locator);
                assert(recovered.config()->schedules.size() == 1);
                assert(recovered.config()->enabled);
                assert(recovered.watermark() == 1800000000000000000ULL);
            }
        }
    }

    Flash flash;
    standalone::Store store(flash);
    assert(store.load());
    MemoryMedia media;
    provisioning::ProfileStore profiles(media);
    assert(profiles.load());
    auto c = consumer();
    assert(profiles.select(provisioning::ProfileSource::ConsumerProfile,
                           provisioning::serialize_consumer_profile(c)));
    Bonds bonds;
    provisioning::ResetStorageTargets targets(store, flash, media, bonds, idle, nullptr);
    assert(targets.preserve_operational(profiles));
    assert(store.config());
    assert(!store.config()->enabled && store.config()->schedules.empty());
    assert(store.config()->callsign == c.callsign && store.config()->locator == c.locator &&
           store.config()->power_dbm == c.power_dbm);
    assert(store.config()->ssid.empty() && store.config()->password.empty());
    standalone::Store reboot(flash);
    assert(reboot.load());
    assert(reboot.config() == store.config());
    auto scheduled = *store.config();
    scheduled.enabled = true;
    scheduled.schedules = {{120, 0}};
    scheduled.ssid = "secretSSID";
    scheduled.password = "secretPW";
    assert(store.save(scheduled));
    assert(store.reserve(1800000000000000000ULL));
    assert(targets.preserve_operational(profiles));
    assert(store.config()->schedules == scheduled.schedules);
    assert(store.config()->enabled);
    assert(store.watermark() == 1800000000000000000ULL);
    auto text = std::string(reinterpret_cast<char*>(flash.data.data()), flash.data.size());
    assert(text.find("secretSSID") == text.npos && text.find("secretPW") == text.npos);
    // Cut every page boundary of the save/migration, reconstruct Store as a
    // reboot would, then resume under the same durable reset authority.
    const auto preserved_flash = flash;
    for (int cut = 0; cut < 20; ++cut) {
        auto interrupted = preserved_flash;
        standalone::Store before(interrupted);
        assert(before.load());
        interrupted.program_budget = cut;
        provisioning::ResetStorageTargets first(before, interrupted, media, bonds, idle, nullptr);
        (void)first.preserve_operational(profiles);
        interrupted.program_budget = -1;
        standalone::Store recovered(interrupted);
        provisioning::ResetStorageTargets retry(recovered, interrupted, media, bonds, idle,
                                                nullptr);
        assert(retry.preserve_operational(profiles));
        assert(recovered.config()->callsign == c.callsign);
        assert(recovered.config()->schedules == scheduled.schedules);
        assert(recovered.watermark() == 1800000000000000000ULL);
        standalone::Store normal_boot(interrupted);
        assert(normal_boot.load());
    }
    for (int cut : {0, 1}) {
        auto interrupted = preserved_flash;
        standalone::Store before(interrupted);
        assert(before.load());
        interrupted.erases_until_fail = cut;
        provisioning::ResetStorageTargets first(before, interrupted, media, bonds, idle, nullptr);
        assert(!first.preserve_operational(profiles));
        interrupted.erases_until_fail = -1;
        standalone::Store recovered(interrupted);
        provisioning::ResetStorageTargets retry(recovered, interrupted, media, bonds, idle,
                                                nullptr);
        assert(retry.preserve_operational(profiles));
        assert(recovered.config()->schedules == scheduled.schedules);
        assert(recovered.watermark() == 1800000000000000000ULL);
    }
    auto irrecoverable = preserved_flash;
    std::fill_n(irrecoverable.data.begin(), 8192, 0x55);
    standalone::Store lost(irrecoverable);
    provisioning::ResetStorageTargets refuse(lost, irrecoverable, media, bonds, idle, nullptr);
    assert(!refuse.preserve_operational(profiles));
    assert(profiles.source() == provisioning::ProfileSource::ConsumerProfile);
    assert(targets.clear_profile(profiles, provisioning::ProfileSource::Unprovisioned));
    assert(profiles.source() == provisioning::ProfileSource::Unprovisioned);
    text = std::string(reinterpret_cast<char*>(media.data.data()), media.data.size());
    assert(text.find("BEGIN PRIVATE KEY") == text.npos && text.find("test-password") == text.npos);
    flash.erases_until_fail = 1;
    assert(!targets.erase_operational());
    flash.erases_until_fail = -1;
    assert(targets.erase_operational());
    assert(targets.operational_erased());
    assert(targets.erase_bonds() && targets.bonds_erased());
    auto empty = scheduled;
    empty.schedules.clear();
    assert(!standalone::parse_config(standalone::serialize_config(empty)));
    empty.enabled = false;
    assert(standalone::parse_config(standalone::serialize_config(empty)) == empty);
}
