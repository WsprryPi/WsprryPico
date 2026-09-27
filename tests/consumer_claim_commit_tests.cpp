#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_claim_commit.hpp"
#include "provisioning/network_profile.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <span>
#include <string>

using namespace wsprrypico;

namespace {
constexpr auto device = "0123456789abcdef0123456789abcdef";
constexpr auto request = "33333333333333333333333333333333";

struct MemoryMedia : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> bytes{};
    unsigned writes = 0, fail_at = 0;
    MemoryMedia() {
        bytes.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        if (at > bytes.size() || out.size() > bytes.size() - at)
            return false;
        std::copy_n(bytes.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        if (at % provisioning::profile_slot_size ||
            at > bytes.size() - provisioning::profile_slot_size)
            return false;
        std::fill_n(bytes.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> page) override {
        if (++writes == fail_at)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[at + i] &= page[i];
        return true;
    }
};

struct Platform : provisioning::ConsumerClaimCommitPlatform {
    bool safe = true, station = true, owner = true, tls = true, generation = true;
    bool expire_during_generation = false, lose_station_during_generation = false;
    bool wrong_generated_hostname = false;
    bool expire_during_write = false;
    unsigned time_reads = 0;
    std::string hostname = "wsprrypico-0a60df.local";
    std::uint64_t ms = 500;
    std::optional<std::uint64_t> utc = 1'800'000'000;
    bool safe_to_commit() override {
        return safe;
    }
    std::uint64_t monotonic_now_ms() override {
        if (expire_during_write && ++time_reads == 3)
            return 90'500;
        return ms;
    }
    bool station_ready(std::string_view ssid) override {
        return station && ssid == "Home Net";
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return utc;
    }
    std::string_view local_hostname() override {
        return hostname;
    }
    bool valid_owner_point(std::string_view value) override {
        return owner && !value.empty();
    }
    bool generate_tls(std::string_view selected_device, std::string_view hostname,
                      std::uint64_t now, provisioning::ConsumerTls& out) override {
        if (!generation || selected_device != device || hostname != "wsprrypico-0a60df.local" ||
            now != 1'800'000'000)
            return false;
        out.hostname = wrong_generated_hostname ? "other.local" : std::string(hostname);
        out.ca_certificate = "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
        out.server_certificate = out.ca_certificate;
        out.ca_private_key = "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
        out.server_private_key = out.ca_private_key;
        out.ca_not_after_utc = 2'000'000'000;
        out.server_not_after_utc = 1'900'000'000;
        if (expire_during_generation)
            ms = 90'500;
        if (lose_station_during_generation)
            station = false;
        return true;
    }
    bool valid_tls(const provisioning::ConsumerTls& value, std::string_view selected_device,
                   std::uint64_t now) override {
        return tls && selected_device == device && now == 1'800'000'000 && !value.hostname.empty();
    }
};

provisioning::ConsumerClaimBinding binding(provisioning::ProfileSource source,
                                           std::uint64_t generation) {
    provisioning::ConsumerClaimBinding value;
    value.device_id = device;
    value.boot_id = "11111111111111111111111111111111";
    value.slot_id = "22222222222222222222222222222222";
    std::array<std::uint8_t, 65> point{};
    point[0] = 4;
    value.owner_public_key = network::bootstrap_b64url(point);
    std::array<std::uint8_t, 32> browser{};
    browser[0] = 1;
    value.browser_public_key = network::bootstrap_b64url(browser);
    value.browser_nonce = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    value.origin = "http://192.168.4.1";
    value.source = source;
    value.generation = generation;
    return value;
}

void grant(provisioning::ConsumerClaimSlot& slot, const provisioning::ConsumerClaimBinding& value,
           std::string_view selected_request = request) {
    assert(slot.start(value, 100, true, false, true));
    assert(slot.grant_open_setup(200, true));
    assert(slot.consume(value, selected_request, 400, true, true));
}

const provisioning::ConsumerClaimValues values{request, "Home Net", "test-password",
                                               "K1ABC", "FN20",     30};
} // namespace

int main() {
    MemoryMedia media;
    provisioning::ProfileStore store(media);
    assert(store.load());
    auto claim = binding(provisioning::ProfileSource::LegacyBootstrap, 0);
    provisioning::ConsumerClaimSlot slot;
    grant(slot, claim);
    Platform platform;

    auto wrong = claim;
    wrong.device_id = "ffffffffffffffffffffffffffffffff";
    assert(provisioning::commit_consumer_claim(store, slot, wrong, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Factory, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.station = false;
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.station = true;
    platform.utc.reset();
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.utc = 1'800'000'000;
    platform.owner = false;
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.owner = true;
    platform.tls = false;
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.tls = true;
    platform.hostname = "WRONG.LOCAL";
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.hostname = "wsprrypico-0a60df.local";
    platform.wrong_generated_hostname = true;
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    platform.wrong_generated_hostname = false;
    platform.ms = 90'500;
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    assert(store.sequence() == 0 && store.data().empty());

    slot.cancel();
    grant(slot, claim);
    platform.ms = 500;
    const auto result = provisioning::commit_consumer_claim(
        store, slot, claim, values, platform, provisioning::RuntimeSource::Unprovisioned, 500);
    assert(result.state == provisioning::ConsumerCommitState::Committed);
    assert(result.generation == 1 && slot.committed());
    assert(store.sequence() == 1 && store.source() == provisioning::ProfileSource::ConsumerProfile);
    const auto parsed = provisioning::parse_consumer_profile(store.data());
    assert(parsed && parsed->device_id == device && parsed->owner_epoch == 0 &&
           parsed->owners.empty() && parsed->ssid == values.ssid &&
           parsed->callsign == values.callsign && parsed->request_sha256 == result.request_sha256);
    provisioning::ProfileStore rebooted(media);
    assert(rebooted.load() && rebooted.data() == store.data());
    assert(provisioning::commit_consumer_claim(store, slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);

    auto update = binding(provisioning::ProfileSource::ConsumerProfile, 1);
    provisioning::ConsumerClaimSlot update_slot;
    constexpr auto update_request = "44444444444444444444444444444444";
    grant(update_slot, update, update_request);
    const auto original_tls = parsed->tls;
    const provisioning::ConsumerClaimValues update_values{
        update_request, "Home Net", "test-password", "K1ABC", "FN20", 30};
    const auto updated =
        provisioning::commit_consumer_claim(store, update_slot, update, update_values, platform,
                                            provisioning::RuntimeSource::ConsumerPreClock, 500);
    assert(updated.state == provisioning::ConsumerCommitState::Committed);
    const auto updated_profile = provisioning::parse_consumer_profile(store.data());
    assert(updated_profile && store.sequence() == 2 && updated_profile->owner_epoch == 0 &&
           updated_profile->owners.empty() && updated_profile->tls == original_tls);

    MemoryMedia network_media;
    provisioning::ProfileStore network_store(network_media);
    assert(network_store.load());
    const auto network_payload =
        provisioning::serialize_network_profile({device, "Home Net", "test-password"});
    assert(network_store.select(provisioning::ProfileSource::NetworkOnly, network_payload));
    auto upgrade = binding(provisioning::ProfileSource::NetworkOnly, 1);
    provisioning::ConsumerClaimSlot upgrade_slot;
    grant(upgrade_slot, upgrade);
    network_media.fail_at = network_media.writes + 1;
    assert(provisioning::commit_consumer_claim(network_store, upgrade_slot, upgrade, values,
                                               platform, provisioning::RuntimeSource::NetworkOnly,
                                               500)
               .state == provisioning::ConsumerCommitState::Reconcile);
    provisioning::ProfileStore after_cut(network_media);
    assert(after_cut.load() && after_cut.source() == provisioning::ProfileSource::NetworkOnly &&
           after_cut.sequence() == 1);

    MemoryMedia reset_media;
    provisioning::ProfileStore reset_store(reset_media);
    assert(reset_store.load());
    assert(reset_store.select(provisioning::ProfileSource::Unprovisioned));
    auto reclaimed = binding(provisioning::ProfileSource::Unprovisioned, 1);
    provisioning::ConsumerClaimSlot reset_slot;
    grant(reset_slot, reclaimed);
    assert(provisioning::commit_consumer_claim(reset_store, reset_slot, reclaimed, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Committed);
    assert(reset_store.sequence() == 2);

    MemoryMedia late_media;
    provisioning::ProfileStore late_store(late_media);
    assert(late_store.load());
    provisioning::ConsumerClaimSlot late_slot;
    grant(late_slot, claim);
    platform.expire_during_generation = true;
    assert(provisioning::commit_consumer_claim(late_store, late_slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    assert(late_store.sequence() == 0);
    platform.expire_during_generation = false;
    platform.ms = 500;
    late_slot.cancel();
    grant(late_slot, claim);
    platform.lose_station_during_generation = true;
    assert(provisioning::commit_consumer_claim(late_store, late_slot, claim, values, platform,
                                               provisioning::RuntimeSource::Unprovisioned, 500)
               .state == provisioning::ConsumerCommitState::Rejected);
    assert(late_store.sequence() == 0);
    MemoryMedia write_late_media;
    provisioning::ProfileStore write_late_store(write_late_media);
    assert(write_late_store.load());
    provisioning::ConsumerClaimSlot write_late_slot;
    grant(write_late_slot, claim);
    Platform write_late_platform;
    write_late_platform.expire_during_write = true;
    const auto write_late = provisioning::commit_consumer_claim(
        write_late_store, write_late_slot, claim, values, write_late_platform,
        provisioning::RuntimeSource::Unprovisioned, 500);
    assert(write_late.state == provisioning::ConsumerCommitState::Reconcile);
    assert(write_late_store.source() == provisioning::ProfileSource::ConsumerProfile &&
           write_late_store.sequence() == 1);
    return 0;
}
