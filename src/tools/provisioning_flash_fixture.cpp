// Offline fixture construction through production journals. Never accesses a device.
#include "provisioning/access.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/reset.hpp"
#include "provisioning/storage.hpp"
#include "standalone/storage.hpp"

#include <algorithm>
#include <cerrno>
#include <charconv>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <source_location>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
using namespace wsprrypico;
namespace {
constexpr std::size_t flash_size = 4194304, begin = 0x3f7000, end = 0x3ff000;
constexpr auto default_device = "29f20b7342051ef947aa56cb9d4fab42";
void check(bool ok, std::source_location location = std::source_location::current()) {
    if (!ok)
        throw std::runtime_error("fixture check " + std::to_string(location.line()));
}
std::vector<std::uint8_t> read(const std::string& path, std::size_t maximum) {
    int fd = open(path.c_str(), O_RDONLY | O_NOFOLLOW);
    check(fd >= 0);
    struct stat st{};
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || (st.st_mode & 0077) || st.st_size < 0 ||
        static_cast<std::uint64_t>(st.st_size) > maximum) {
        close(fd);
        check(false);
    }
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(st.st_size));
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        auto n = ::read(fd, bytes.data() + offset, bytes.size() - offset);
        if (n <= 0) {
            close(fd);
            check(false);
        }
        offset += static_cast<std::size_t>(n);
    }
    std::uint8_t extra{};
    const bool exact = ::read(fd, &extra, 1) == 0;
    close(fd);
    check(exact);
    return bytes;
}
struct Bounded {
    std::vector<std::uint8_t>& bytes;
    std::size_t base, size, sector;
    bool read(std::size_t offset, std::span<std::uint8_t> output) {
        if (offset > size || output.size() > size - offset)
            return false;
        std::copy_n(bytes.begin() + base + offset, output.size(), output.begin());
        return true;
    }
    bool erase(std::size_t offset) {
        if (offset % sector || offset > size || sector > size - offset)
            return false;
        std::fill_n(bytes.begin() + base + offset, sector, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) {
        if (offset % 256 || page.size() != 256 || offset > size || page.size() > size - offset)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            if ((bytes[base + offset + i] & page[i]) != page[i])
                return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[base + offset + i] &= page[i];
        return true;
    }
};
struct Profile : provisioning::Media {
    Bounded m;
    explicit Profile(std::vector<std::uint8_t>& b) : m{b, begin, 16384, 8192} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return m.read(o, b);
    }
    bool erase(std::size_t o) override {
        return m.erase(o);
    }
    bool program(std::size_t o, std::span<const std::uint8_t> b) override {
        return m.program(o, b);
    }
};
struct Access : provisioning::AccessMedia {
    Bounded m;
    explicit Access(std::vector<std::uint8_t>& b) : m{b, 0x3f3000, 8192, 4096} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return m.read(o, b);
    }
    bool erase(std::size_t o) override {
        return m.erase(o);
    }
    bool program(std::size_t o, std::span<const std::uint8_t> b) override {
        return m.program(o, b);
    }
};
struct Operational : standalone::Flash {
    Bounded m;
    unsigned erases = 0, programs = 0;
    explicit Operational(std::vector<std::uint8_t>& b) : m{b, 0x3fb000, 16384, 4096} {}
    bool read(std::size_t o, std::span<std::uint8_t> b) override {
        return m.read(o, b);
    }
    bool erase(std::size_t o) override {
        ++erases;
        return m.erase(o);
    }
    bool program(std::size_t o, std::span<const std::uint8_t> b) override {
        ++programs;
        return m.program(o, b);
    }
};
// begin() only writes the durable intent. No reset effects are permitted here;
// the separately deployed target consumes the intent before starting its stack.
struct IntentTargets final : provisioning::ResetTargets {
    provisioning::Activity activity() const override {
        return {};
    }
    bool erase_operational() override {
        return false;
    }
    bool operational_erased() const override {
        return false;
    }
    bool erase_bonds() override {
        return false;
    }
    bool bonds_erased() const override {
        return false;
    }
};
std::string text(const std::vector<std::uint8_t>& value) {
    return {value.begin(), value.end()};
}
void publish(const std::string& path, const std::vector<std::uint8_t>& bytes) {
    const auto temporary = path + ".temporary-" + std::to_string(getpid());
    int fd = open(temporary.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    check(fd >= 0);
    bool closed = false, published = false;
    struct stat identity{};
    try {
        check(fchmod(fd, 0600) == 0 && fstat(fd, &identity) == 0);
        std::size_t offset = 0;
        while (offset < bytes.size()) {
            auto n = write(fd, bytes.data() + offset, bytes.size() - offset);
            check(n > 0);
            offset += static_cast<std::size_t>(n);
        }
        check(fsync(fd) == 0);
        check(close(fd) == 0);
        closed = true;
        // link is atomic and refuses an existing file or symlink; rename is not.
        check(link(temporary.c_str(), path.c_str()) == 0);
        published = true;
        check(unlink(temporary.c_str()) == 0);
        const auto slash = path.find_last_of('/');
        const auto parent = slash == std::string::npos ? "." : path.substr(0, slash);
        int dir = open(parent.empty() ? "/" : parent.c_str(), O_RDONLY);
        check(dir >= 0);
        bool synced = fsync(dir) == 0;
        close(dir);
        check(synced);
    } catch (...) {
        if (!closed)
            close(fd);
        unlink(temporary.c_str());
        if (published) {
            struct stat current{};
            if (lstat(path.c_str(), &current) == 0 && current.st_dev == identity.st_dev &&
                current.st_ino == identity.st_ino)
                unlink(path.c_str());
        }
        throw;
    }
}
} // namespace
int main(int argc, char** argv) {
    try {
        std::map<std::string, std::string> args;
        check(argc >= 3 && argc % 2 == 1);
        for (int i = 1; i < argc; i += 2)
            check(args.emplace(argv[i], argv[i + 1]).second);
        // Consumer fixtures and reset intents must be bound to their intended
        // physical identity. Existing B callers retain their default; a second
        // board requires an explicit canonical identity matching its profile.
        std::string device = default_device;
        if (args.contains("--device-id")) {
            device = args.at("--device-id");
            check(device.size() == 32 && std::all_of(device.begin(), device.end(), [](char c) {
                      return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                  }));
            check(args.contains("--consumer-profile") || args.contains("--prepare-reset-intent"));
            args.erase("--device-id");
        }
        if (args.contains("--prepare-reset-intent")) {
            check(args.size() == 4 && args.at("--prepare-reset-intent") == "yes" &&
                  args.contains("--backup") && args.contains("--output") &&
                  args.contains("--request-sha256"));
            const auto& hex = args.at("--request-sha256");
            check(hex.size() == 64 && std::all_of(hex.begin(), hex.end(), [](char c) {
                      return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
                  }));
            wtp::PayloadDigest digest{};
            for (std::size_t i = 0; i < digest.size(); ++i) {
                unsigned byte = 0;
                const auto parsed =
                    std::from_chars(hex.data() + 2 * i, hex.data() + 2 * i + 2, byte, 16);
                check(parsed.ec == std::errc{} && parsed.ptr == hex.data() + 2 * i + 2);
                digest[i] = static_cast<std::uint8_t>(byte);
            }
            auto bytes = read(args.at("--backup"), flash_size);
            check(bytes.size() == flash_size);
            const auto original = bytes;
            Access access_media(bytes);
            Profile profile_media(bytes);
            Operational operational_media(bytes);
            provisioning::AccessStore access(access_media);
            provisioning::ProfileStore profiles(profile_media);
            standalone::Store operational(operational_media);
            check(access.load() && access.record() && !access.record()->reset.pending() &&
                  !access.record()->ble_disabled && access.record()->bond_count >= 1 &&
                  access.record()->bond_count <= provisioning::authorized_bond_capacity &&
                  profiles.load() &&
                  profiles.source() == provisioning::ProfileSource::RuntimeProfile &&
                  operational.load() && (!operational.config() || !operational.config()->enabled));
            auto profile = provisioning::parse_profile(profiles.data());
            check(profile && profile->device_id == device);
            provisioning::scrub(*profile);
            auto old = *access.record();
            const auto sequence = access.sequence();
            IntentTargets targets;
            // The identity is unused by begin(); the target derives its own
            // physical identity when it performs the later reset recovery.
            provisioning::ResetCoordinator reset(access, profiles, targets, {});
            check(reset.begin(provisioning::ResetLevel::Provisioning,
                              provisioning::ProfileSource::Unprovisioned,
                              digest) == provisioning::ResetResult::Pending);
            provisioning::AccessStore verified(access_media);
            check(verified.load() && verified.record() && verified.sequence() == sequence + 1);
            auto actual = *verified.record();
            check(actual.reset.level == provisioning::ResetLevel::Provisioning &&
                  actual.reset.phase == provisioning::ResetPhase::Intent &&
                  actual.reset.target_source == provisioning::ProfileSource::Unprovisioned &&
                  actual.reset.request_digest == digest);
            actual.reset = old.reset;
            check(actual == old &&
                  std::equal(bytes.begin(), bytes.begin() + 0x3f3000, original.begin()) &&
                  std::equal(bytes.begin() + 0x3f5000, bytes.end(), original.begin() + 0x3f5000));
            provisioning::scrub(actual);
            provisioning::scrub(old);
            publish(args.at("--output"), bytes);
            std::cout << "{\"status\":\"OFFLINE_PROVISIONING_RESET_INTENT_READY\","
                         "\"reset_level\":2,\"reset_phase\":1,\"target_source\":2,\"rf_jobs\":0}\n";
            return 0;
        }
        if (args.contains("--enable-field-mode")) {
            check(args.size() == 3 && args.at("--enable-field-mode") == "yes" &&
                  args.contains("--backup") && args.contains("--output"));
            auto bytes = read(args.at("--backup"), flash_size);
            check(bytes.size() == flash_size);
            const auto original = bytes;
            Access media(bytes);
            provisioning::AccessStore store(media);
            check(store.load() && store.healthy() && store.record() &&
                  !store.record()->reset.pending());
            const auto old = *store.record();
            auto selected = old;
            selected.field_mode = true;
            check(store.replace(selected));
            provisioning::AccessStore verified(media);
            check(verified.load() && verified.record() && *verified.record() == selected);
            auto restored = *verified.record();
            restored.field_mode = old.field_mode;
            check(restored == old);
            check(std::equal(bytes.begin(), bytes.begin() + 0x3f3000, original.begin()) &&
                  std::equal(bytes.begin() + 0x3f5000, bytes.end(), original.begin() + 0x3f5000));
            publish(args.at("--output"), bytes);
            std::cout << "{\"status\":\"OFFLINE_FIELD_MODE_READY\",\"rf_jobs\":0}\n";
            return 0;
        }
        if (args.contains("--prepare-config-rollover")) {
            check(args.size() == 3 && args.at("--prepare-config-rollover") == "yes" &&
                  args.contains("--backup") && args.contains("--output"));
            auto bytes = read(args.at("--backup"), flash_size);
            check(bytes.size() == flash_size);
            const auto original = bytes;
            Operational media(bytes);
            standalone::Store store(media);
            check(store.load() && store.config() && !store.config()->enabled);
            const auto config = *store.config();
            const auto old_sequence = store.config_sequence();
            const auto old_cursor = store.cursor_sequence(), old_watermark = store.watermark();
            auto bank_full = [&]() {
                for (std::size_t offset = 0; offset < 8192; offset += 2048) {
                    std::uint64_t sequence = 0;
                    for (unsigned i = 0; i < 8; ++i)
                        sequence |= std::uint64_t{bytes[0x3fb000 + offset + 8 + i]} << (8 * i);
                    if (sequence == store.config_sequence())
                        return offset % 4096 == 2048;
                }
                check(false);
                return false;
            };
            unsigned appends = 0;
            if (!bank_full()) {
                check(store.save(config));
                ++appends;
            }
            check(bank_full() && media.erases == 0 &&
                  store.config_sequence() == old_sequence + appends &&
                  store.cursor_sequence() == old_cursor && store.watermark() == old_watermark);
            standalone::Store verified(media);
            check(verified.load() && verified.config() && *verified.config() == config &&
                  verified.watermark() == old_watermark &&
                  verified.cursor_sequence() == old_cursor);
            check(std::equal(bytes.begin(), bytes.begin() + 0x3fb000, original.begin()) &&
                  std::equal(bytes.begin() + 0x3fd000, bytes.end(), original.begin() + 0x3fd000));
            // Independently exercise the next production append on a disposable
            // copy. Only the prepared image is published, never this dry run.
            auto probe_bytes = bytes;
            Operational probe_media(probe_bytes);
            standalone::Store probe(probe_media);
            check(probe.load() && probe.save(config) && probe_media.erases == 1 &&
                  probe_media.programs == 8 && probe.watermark() == old_watermark);
            publish(args.at("--output"), bytes);
            std::cout << "{\"status\":\"OFFLINE_ROLLOVER_READY\",\"appends\":" << appends
                      << ",\"next_append_erase_verified_offline\":true,\"rf_jobs\":0}\n";
            return 0;
        }
        const bool pending_fixture = args.contains("--allow-tls-pending");
        check(args.size() == (pending_fixture ? 6 : 5));
        if (pending_fixture)
            check(args.at("--allow-tls-pending") == "yes");
        for (auto name : {"--backup", "--consumer-profile", "--config", "--watermark", "--output"})
            check(args.contains(name));
        auto bytes = read(args.at("--backup"), flash_size);
        check(bytes.size() == flash_size);
        const auto original = bytes;
        const auto profile_text =
            text(read(args.at("--consumer-profile"), provisioning::max_profile_bytes));
        auto profile = provisioning::parse_consumer_profile(profile_text);
        check(profile && profile->device_id == device && profile->tls_pending == pending_fixture);
        const auto config_text = text(read(args.at("--config"), standalone::max_config_bytes));
        const auto config = standalone::parse_config(config_text);
        check(config && !config->enabled && !config->schedules.empty() &&
              standalone::serialize_config(*config) == config_text);
        const auto& watermark_text = args.at("--watermark");
        std::uint64_t watermark = 0;
        const auto result = std::from_chars(
            watermark_text.data(), watermark_text.data() + watermark_text.size(), watermark);
        check(result.ec == std::errc{} &&
              result.ptr == watermark_text.data() + watermark_text.size() && watermark > 0 &&
              std::to_string(watermark) == watermark_text);
        Profile pm(bytes);
        Operational om(bytes);
        provisioning::ProfileStore ps(pm);
        standalone::Store store(om);
        check(ps.load() && store.load());
        check(ps.select(provisioning::ProfileSource::ConsumerProfile, profile_text));
        if (pending_fixture) {
            // Explicit offline pending-TLS preparation changes only the profile.
            // The production parser already requires no TLS material or clients.
            check(store.config() && standalone::serialize_config(*store.config()) == config_text &&
                  store.watermark() == watermark);
        } else
            check(store.save(*config) && store.reserve(watermark));
        provisioning::ProfileStore verified_profile(pm);
        standalone::Store verified_store(om);
        check(verified_profile.load() && verified_store.load() &&
              verified_profile.source() == provisioning::ProfileSource::ConsumerProfile &&
              verified_profile.data() == profile_text &&
              provisioning::parse_consumer_profile(verified_profile.data()).has_value() &&
              verified_store.config() &&
              standalone::serialize_config(*verified_store.config()) == config_text &&
              verified_store.watermark() == watermark);
        check(std::equal(bytes.begin(), bytes.begin() + begin, original.begin()) &&
              std::equal(bytes.begin() + end, bytes.end(), original.begin() + end));
        if (pending_fixture)
            check(std::equal(bytes.begin() + 0x3fb000, bytes.end(), original.begin() + 0x3fb000));
        publish(args.at("--output"), bytes);
        provisioning::scrub(*profile);
        std::cout << "{\"status\":\"OFFLINE_FIXTURE_READY\",\"bytes\":4194304,\"rf_jobs\":0}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 2;
    }
}
