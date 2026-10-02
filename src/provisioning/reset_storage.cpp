#include "provisioning/reset_storage.hpp"

#include "provisioning/consumer_profile.hpp"

#include <algorithm>
#include <array>
namespace wsprrypico::provisioning {
bool ResetStorageTargets::preserve_operational(const ProfileStore& profiles) {
    if (!store_.healthy() && !store_.load(true))
        return false;
    auto config = store_.config();
    if (profiles.source() == ProfileSource::ConsumerProfile) {
        auto consumer = parse_consumer_profile(profiles.data());
        if (!consumer)
            return false;
        if (!config)
            config = standalone::Config{};
        config->callsign = consumer->callsign;
        config->locator = consumer->locator;
        config->power_dbm = consumer->power_dbm;
        scrub(*consumer);
    }
    if (!config)
        return true;
    config->ssid.clear();
    config->password.clear();
    config->ntp_ipv4 = standalone::default_time_server;
    if (!store_.save(*config))
        return false;
    return store_.purge_config_history(flash_);
}
bool ResetStorageTargets::clear_profile(ProfileStore& profiles, ProfileSource target) {
    if (target != ProfileSource::Unprovisioned)
        return false;
    // Resume can re-erase an incomplete journal because durable intent is in
    // the independent access journal and operational preservation precedes this.
    if (!media_.erase(0) || !media_.erase(profile_slot_size))
        return false;
    return profiles.load() && profiles.select(target);
}
bool ResetStorageTargets::erase_operational() {
    for (std::size_t offset = 0; offset < 16 * 1024; offset += 4096)
        if (!flash_.erase(offset))
            return false;
    return store_.load();
}
bool ResetStorageTargets::operational_erased() const {
    std::array<std::uint8_t, 256> bytes{};
    for (std::size_t offset = 0; offset < 16 * 1024; offset += bytes.size()) {
        if (!flash_.read(offset, bytes) ||
            !std::all_of(bytes.begin(), bytes.end(), [](auto b) { return b == 255; }))
            return false;
    }
    return store_.healthy() && !store_.config() && store_.watermark() == 0;
}
} // namespace wsprrypico::provisioning
