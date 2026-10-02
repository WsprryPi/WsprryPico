#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_claim_commit.hpp"
#include "provisioning/network_profile.hpp"
#include "wtp/sha256.hpp"

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
    bool fail_erase = false, write_then_fail = false;
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
        if (fail_erase)
            return false;
        if (at % provisioning::profile_slot_size ||
            at > bytes.size() - provisioning::profile_slot_size)
            return false;
        std::fill_n(bytes.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> page) override {
        const bool failed = ++writes == fail_at;
        if (failed && !write_then_fail)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[at + i] &= page[i];
        return !failed;
    }
};

struct Platform : provisioning::ConsumerClaimCommitPlatform {
    bool safe = true, station = true, owner = true, tls = true, generation = true;
    bool expire_during_generation = false, lose_station_during_generation = false;
    bool wrong_generated_hostname = false, lose_time_during_generation = false;
    bool expire_during_write = false;
    unsigned time_reads = 0, tls_generations = 0;
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
        ++tls_generations;
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
        if (lose_time_during_generation)
            utc.reset();
        if (expire_during_generation)
            ms = 90'500;
        if (lose_station_during_generation)
            station = false;
        return true;
    }
    bool valid_tls(const provisioning::ConsumerTls& value, std::string_view selected_device,
                   std::uint64_t now) override {
        return tls && selected_device == device && now == 1'800'000'000 &&
               !value.hostname.empty() && value.ca_not_after_utc > now &&
               value.server_not_after_utc > now;
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
        update_request, "Home Net", "test-password", "PJ4/K1ABC", "FN20XX", 30};
    const auto updated =
        provisioning::commit_consumer_claim(store, update_slot, update, update_values, platform,
                                            provisioning::RuntimeSource::ConsumerPreClock, 500);
    assert(updated.state == provisioning::ConsumerCommitState::Committed);
    const auto updated_profile = provisioning::parse_consumer_profile(store.data());
    assert(updated_profile && store.sequence() == 2 && updated_profile->owner_epoch == 0 &&
           updated_profile->owners.empty() && updated_profile->tls == original_tls);
    assert(updated_profile->locator == "FN20XX");
    assert(updated_profile->callsign == "PJ4/K1ABC");

    // Populated engineering clients survive station edits even without UTC or
    // with expired/invalid trust. Activation independently rejects invalid trust.
    for (unsigned invalid_case = 0; invalid_case < 4; ++invalid_case) {
        MemoryMedia populated_media;
        provisioning::ProfileStore populated_store(populated_media);
        assert(populated_store.load());
        auto populated = *updated_profile;
        populated.request_sha256 = std::string(64, 'd');
        std::array<std::uint8_t, 3> csr{0x30, 0x01, 0x00};
        populated.clients = {{"wspr5", network::bootstrap_b64url(csr),
                              network::bootstrap_hex(wtp::sha256(csr)), std::string(64, 'b'), 1,
                              1'850'000'000}};
        if (invalid_case == 1)
            populated.tls.server_not_after_utc = 1'800'000'000;
        assert(populated_store.select(provisioning::ProfileSource::ConsumerProfile,
                                      provisioning::serialize_consumer_profile(populated)));
        const auto original = populated_store.data();
        auto populated_binding = binding(provisioning::ProfileSource::ConsumerProfile, 1);
        provisioning::ConsumerClaimSlot populated_slot;
        grant(populated_slot, populated_binding, update_request);
        Platform populated_platform;
        if (invalid_case == 2)
            populated_platform.tls = false;
        if (invalid_case == 3)
            populated_platform.utc.reset();
        const auto edited = provisioning::commit_consumer_claim(
            populated_store, populated_slot, populated_binding, update_values, populated_platform,
            provisioning::RuntimeSource::ConsumerPreClock, 500);
        assert(populated_platform.tls_generations == 0);
        assert(edited.state == provisioning::ConsumerCommitState::Committed);
        auto after = provisioning::parse_consumer_profile(populated_store.data());
        assert(after && after->clients == populated.clients && after->tls == populated.tls);
        assert(provisioning::setup_request_digest(populated_store, device) ==
               edited.request_sha256);
    }

    // First offline save is durable and structurally loadable, but has no TLS authority.
    MemoryMedia offline_media;
    provisioning::ProfileStore offline_store(offline_media);
    assert(offline_store.load());
    provisioning::ConsumerClaimSlot offline_slot;
    grant(offline_slot, claim);
    Platform offline_platform;
    offline_platform.utc.reset();
    const auto offline = provisioning::commit_consumer_claim(
        offline_store, offline_slot, claim, values, offline_platform,
        provisioning::RuntimeSource::Unprovisioned, 500);
    assert(offline.state == provisioning::ConsumerCommitState::Committed);
    auto offline_profile = provisioning::parse_consumer_profile(offline_store.data());
    assert(offline_profile && offline_profile->tls_pending && offline_profile->clients.empty());
    assert(offline_profile->tls.ca_certificate.empty() && offline_platform.tls_generations == 0);
    provisioning::ProfileStore offline_reboot(offline_media);
    assert(offline_reboot.load() && offline_reboot.data() == offline_store.data());
    provisioning::RuntimeProfile offline_runtime;
    assert(offline_runtime.load(offline_reboot, device, provisioning::BuildBundleState::Absent));
    assert(offline_runtime.source() == provisioning::RuntimeSource::ConsumerPreClock);
    standalone::Config base;
    const auto effective = offline_runtime.overlay(base);
    assert(effective && effective->callsign == values.callsign &&
           effective->locator == values.locator);
    assert(offline_runtime.consumer_profile()->tls_pending);

    assert(provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Rejected);
    assert(offline_platform.tls_generations == 0);
    offline_platform.utc = 1'800'000'000;
    offline_platform.generation = false;
    assert(provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Rejected);
    assert(offline_reboot.sequence() == 1);
    offline_platform.safe = false;
    assert(provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Rejected);
    offline_platform.safe = true;
    offline_platform.generation = true;
    offline_platform.lose_time_during_generation = true;
    assert(provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Rejected);
    assert(offline_reboot.sequence() == 1);
    offline_platform.lose_time_during_generation = false;
    offline_platform.utc = 1'800'000'000;
    offline_platform.generation = true;
    const auto ready =
        provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform);
    assert(ready.state == provisioning::ConsumerCommitState::Committed && ready.generation == 2 &&
           ready.request_sha256 == offline.request_sha256);
    auto ready_profile = provisioning::parse_consumer_profile(offline_reboot.data());
    assert(ready_profile && !ready_profile->tls_pending &&
           ready_profile->callsign == values.callsign);
    assert(provisioning::materialize_consumer_tls(offline_reboot, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Rejected);
    // A pending record cannot smuggle existing trust or engineering clients.
    auto malformed_pending = *offline_profile;
    malformed_pending.tls.ca_certificate = parsed->tls.ca_certificate;
    assert(provisioning::serialize_consumer_profile(malformed_pending).empty());

    // Interrupted TLS completion retains the old pending authority after reboot.
    MemoryMedia completion_cut_media;
    provisioning::ProfileStore completion_cut(completion_cut_media);
    assert(completion_cut.load());
    assert(completion_cut.select(provisioning::ProfileSource::ConsumerProfile,
                                 provisioning::serialize_consumer_profile(*offline_profile)));
    completion_cut_media.fail_at = completion_cut_media.writes + 1;
    assert(provisioning::materialize_consumer_tls(completion_cut, device, offline_platform).state ==
           provisioning::ConsumerCommitState::Reconcile);
    provisioning::ProfileStore completion_reboot(completion_cut_media);
    assert(completion_reboot.load() && completion_reboot.sequence() == 1);
    assert(provisioning::parse_consumer_profile(completion_reboot.data())->tls_pending);
    // Exhaust every program boundary for TLS completion, both before and after
    // the media applies the page. Reboot must select exact old/new authority.
    for (bool after_write : {false, true}) {
        bool reached_success = false;
        for (unsigned cut = 0; cut < 40 && !reached_success; ++cut) {
            MemoryMedia cut_media;
            provisioning::ProfileStore cut_store(cut_media);
            assert(cut_store.load());
            assert(cut_store.select(provisioning::ProfileSource::ConsumerProfile,
                                    provisioning::serialize_consumer_profile(*offline_profile)));
            cut_media.fail_erase = cut == 0;
            cut_media.fail_at = cut ? cut_media.writes + cut : 0;
            cut_media.write_then_fail = after_write;
            const auto result =
                provisioning::materialize_consumer_tls(cut_store, device, offline_platform);
            reached_success = result.state == provisioning::ConsumerCommitState::Committed;
            cut_media.fail_erase = false;
            provisioning::ProfileStore boot(cut_media);
            assert(boot.load());
            auto chosen = provisioning::parse_consumer_profile(boot.data());
            assert(chosen && chosen->request_sha256 == offline.request_sha256 &&
                   chosen->callsign == offline_profile->callsign);
            assert((boot.sequence() == 1 && chosen->tls_pending) ||
                   (boot.sequence() == 2 && !chosen->tls_pending));
        }
        assert(reached_success);
    }
    auto pending_text = provisioning::serialize_consumer_profile(*offline_profile);
    const auto pending_flag = pending_text.find("\"tls_pending\":true");
    assert(pending_flag != std::string::npos);
    pending_text.replace(pending_flag, 18, "\"tls_pending\":false");
    assert(!provisioning::parse_consumer_profile(pending_text));

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
