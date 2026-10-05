#include "provisioning/access.hpp"
#include "provisioning/reset_storage.hpp"

#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>
using namespace wsprrypico::provisioning;
template <class Interface> struct TestRegion final : Interface {
    std::vector<std::uint8_t>& bytes;
    std::size_t base, size, sector;
    TestRegion(std::vector<std::uint8_t>& value, std::size_t offset, std::size_t length,
               std::size_t erase_size)
        : bytes(value), base(offset), size(length), sector(erase_size) {}
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset > size || out.size() > size - offset)
            return false;
        std::copy_n(bytes.begin() + base + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (offset % sector || offset > size - sector)
            return false;
        std::fill_n(bytes.begin() + base + offset, sector, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (offset % 256 || page.size() != 256 || offset > size - 256)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[base + offset + i] &= page[i];
        return true;
    }
};
struct TestBonds final : BondStore {
    std::vector<std::uint8_t>& bytes;
    explicit TestBonds(std::vector<std::uint8_t>& value) : bytes(value) {}
    bool erase(std::uint64_t) override {
        return false;
    }
    bool erase_all() override {
        std::fill(bytes.begin() + 0x3f5000, bytes.begin() + 0x3f7000, 255);
        return true;
    }
};
struct TestAccessMedia final : AccessMedia {
    std::vector<std::uint8_t>& bytes;
    explicit TestAccessMedia(std::vector<std::uint8_t>& value) : bytes(value) {}
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset > access_media_size || out.size() > access_media_size - offset)
            return false;
        std::copy_n(bytes.begin() + 0x3f3000 + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (offset % access_slot_size || offset > access_media_size - access_slot_size)
            return false;
        std::fill_n(bytes.begin() + 0x3f3000 + offset, access_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (offset % 256 || page.size() != 256 || offset > access_media_size - 256)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[0x3f3000 + offset + i] &= page[i];
        return true;
    }
};
int main(int argc, char** argv) {
    assert(argc == 2);
    const auto root =
        std::filesystem::temp_directory_path() / ("p12-field-mode-" + std::to_string(getpid()));
    assert(std::filesystem::create_directory(root));
    std::vector<std::uint8_t> bytes(4194304, 0x51);
    std::fill(bytes.begin() + 0x3f3000, bytes.begin() + 0x3f5000, 255);
    TestAccessMedia media(bytes);
    AccessStore store(media);
    assert(store.load());
    AccessRecord record;
    record.password = "wspr-test";
    record.default_password = true;
    record.epoch = 1;
    assert(store.initialize(record));
    record.epoch = 2;
    record.bond_count = 2;
    record.bonds[0] = 17;
    record.bonds[1] = 29;
    assert(store.replace(record));
    const auto original = bytes;
    const auto input = root / "baseline.bin", output = root / "field.bin";
    {
        std::ofstream file(input, std::ios::binary);
        file.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    }
    std::filesystem::permissions(input, std::filesystem::perms::owner_read |
                                            std::filesystem::perms::owner_write);
    auto invoke = [&] {
        const auto pid = fork();
        assert(pid >= 0);
        if (!pid) {
            execl(argv[1], argv[1], "--backup", input.c_str(), "--enable-field-mode", "yes",
                  "--output", output.c_str(), nullptr);
            _exit(127);
        }
        int status = 0;
        assert(waitpid(pid, &status, 0) == pid);
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
    };
    assert(invoke() == 0);
    {
        std::ifstream file(output, std::ios::binary);
        file.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
        assert(file.gcount() == static_cast<std::streamsize>(bytes.size()));
    }
    TestAccessMedia final_media(bytes);
    AccessStore final_store(final_media);
    assert(final_store.load() && final_store.record());
    auto actual = *final_store.record();
    assert(actual.field_mode);
    actual.field_mode = false;
    assert(actual == record);
    assert(std::equal(bytes.begin(), bytes.begin() + 0x3f3000, original.begin()));
    assert(std::equal(bytes.begin() + 0x3f5000, bytes.end(), original.begin() + 0x3f5000));
    assert(invoke() != 0); // Existing output must never be overwritten.

    // One native intent fixture, then cold production recovery on its actual
    // output. This is storage behavior, not a mocked reset state machine.
    std::fill(bytes.begin(), bytes.end(), 0x51);
    std::fill(bytes.begin() + 0x3f3000, bytes.begin() + 0x3f5000, 255);
    std::fill(bytes.begin() + 0x3f7000, bytes.begin() + 0x3ff000, 255);
    TestAccessMedia seed_access_media(bytes);
    AccessStore seed_access(seed_access_media);
    assert(seed_access.load());
    record = {};
    record.password = "private-reset-test-password";
    record.epoch = 1;
    assert(seed_access.initialize(record));
    record.epoch = 7;
    record.bond_count = 1;
    record.bonds[0] = 17;
    record.field_mode = true;
    assert(seed_access.replace(record));
    const auto access_sequence = seed_access.sequence();
    TestRegion<Media> seed_profile_media(bytes, 0x3f7000, 16384, 8192);
    ProfileStore seed_profile(seed_profile_media);
    assert(seed_profile.load());
    Profile profile{"29f20b7342051ef947aa56cb9d4fab42",
                    "Host fixture",
                    "test-wifi-password",
                    "time.example.org",
                    "wsprrypico-000001.local",
                    443,
                    "-----BEGIN CERTIFICATE-----\nSERVER\n-----END CERTIFICATE-----\n",
                    "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n",
                    "-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----\n"};
    assert(seed_profile.replace(serialize_profile(profile)));
    TestRegion<wsprrypico::standalone::Flash> seed_flash(bytes, 0x3fb000, 16384, 4096);
    wsprrypico::standalone::Store seed_store(seed_flash);
    assert(seed_store.load());
    wsprrypico::standalone::Config config;
    config.callsign = "K1ABC";
    config.locator = "FN20";
    config.power_dbm = 30;
    config.ssid = profile.ssid;
    config.password = profile.password;
    config.ntp_ipv4 = profile.time_server;
    config.expires_utc_s = 2'000'000'000;
    config.schedules = {{240, 0}, {240, 120}};
    assert(seed_store.save(config) && seed_store.reserve(123456789));
    const auto seeded = bytes;
    {
        std::ofstream file(input, std::ios::binary);
        file.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    }
    const auto intent_output = root / "reset-intent.bin";
    const std::string request(64, 'a');
    auto intent = [&](const std::filesystem::path& backup, const char* digest,
                      const std::filesystem::path& destination) {
        const auto pid = fork();
        assert(pid >= 0);
        if (!pid) {
            execl(argv[1], argv[1], "--backup", backup.c_str(), "--prepare-reset-intent", "yes",
                  "--request-sha256", digest, "--output", destination.c_str(), nullptr);
            _exit(127);
        }
        int status = 0;
        assert(waitpid(pid, &status, 0) == pid);
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128;
    };
    assert(intent(input, request.c_str(), intent_output) == 0);
    {
        std::ifstream file(intent_output, std::ios::binary);
        file.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
        assert(file.gcount() == static_cast<std::streamsize>(bytes.size()));
    }
    assert(std::equal(bytes.begin(), bytes.begin() + 0x3f3000, seeded.begin()));
    assert(std::equal(bytes.begin() + 0x3f5000, bytes.end(), seeded.begin() + 0x3f5000));
    TestAccessMedia pending_media(bytes);
    AccessStore pending(pending_media);
    assert(pending.load() && pending.sequence() == access_sequence + 1 && pending.record());
    auto pending_record = *pending.record();
    assert(pending_record.reset.level == ResetLevel::Provisioning &&
           pending_record.reset.phase == ResetPhase::Intent &&
           pending_record.reset.target_source == ProfileSource::Unprovisioned);
    assert(std::all_of(pending_record.reset.request_digest.begin(),
                       pending_record.reset.request_digest.end(),
                       [](auto b) { return b == 0xaa; }));
    pending_record.reset = {};
    assert(pending_record == record);
    const auto refused = root / "refused.bin";
    assert(intent(intent_output, request.c_str(), refused) != 0 &&
           !std::filesystem::exists(refused));
    const std::string zero(64, '0');
    assert(intent(input, zero.c_str(), refused) != 0 && !std::filesystem::exists(refused));

    // Fresh loaders and real ResetStorageTargets match the pre-stack boot path.
    TestRegion<Media> resumed_profile_media(bytes, 0x3f7000, 16384, 8192);
    ProfileStore resumed_profile(resumed_profile_media);
    TestRegion<wsprrypico::standalone::Flash> resumed_flash(bytes, 0x3fb000, 16384, 4096);
    wsprrypico::standalone::Store resumed_store(resumed_flash);
    assert(resumed_profile.load() && resumed_store.load(true));
    const auto identity = derive_local_identity(profile.device_id, "02:00:00:00:00:01");
    assert(identity);
    TestBonds bonds(bytes);
    ResetStorageTargets targets(
        resumed_store, resumed_flash, resumed_profile_media, bonds,
        +[](void*) { return Activity{}; }, nullptr);
    ResetCoordinator resumed(pending, resumed_profile, targets, *identity);
    assert(resumed.pending() && resumed.resume() == ResetResult::Complete && !resumed.pending());
    assert(pending.record()->epoch == record.epoch + 1 && pending.record()->bond_count == 0 &&
           pending.record()->password == identity->default_password &&
           !pending.record()->field_mode && !pending.record()->ble_disabled);
    assert(resumed_profile.source() == ProfileSource::Unprovisioned &&
           resumed_profile.data().empty());
    config.ssid.clear();
    config.password.clear();
    config.ntp_ipv4 = wsprrypico::standalone::default_time_server;
    assert(resumed_store.config() && *resumed_store.config() == config &&
           resumed_store.watermark() == 123456789);
    assert(std::all_of(bytes.begin() + 0x3f5000, bytes.begin() + 0x3f7000,
                       [](auto b) { return b == 255; }));
    assert(std::equal(bytes.begin(), bytes.begin() + 0x3f3000, seeded.begin()) &&
           std::equal(bytes.begin() + 0x3ff000, bytes.end(), seeded.begin() + 0x3ff000));
    const auto completed = bytes;
    assert(resumed.resume() == ResetResult::Complete && bytes == completed);
    std::filesystem::remove_all(root);
}
