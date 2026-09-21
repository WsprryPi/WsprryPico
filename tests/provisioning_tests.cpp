#include "provisioning/manager.hpp"
#include "provisioning/runtime.hpp"
#include "standalone/config.hpp"
#include "standalone/storage.hpp"

#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <iostream>

using namespace wsprrypico;
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                         \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)

namespace {
constexpr auto device = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
constexpr auto other_device = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
constexpr auto session_a = "11111111111111111111111111111111";
constexpr auto session_b = "22222222222222222222222222222222";

std::string request_id(unsigned value) {
    char text[33];
    std::snprintf(text, sizeof(text), "cccccccccccccccccccccccc%08x", value);
    return text;
}
std::span<const std::uint8_t> bytes(std::string_view text) {
    return {reinterpret_cast<const std::uint8_t*>(text.data()), text.size()};
}

struct MemoryMedia : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> data;
    unsigned program_calls = 0;
    unsigned fail_program_call = 0;
    bool fail_erase = false;
    MemoryMedia() {
        data.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> output) override {
        if (offset > data.size() || output.size() > data.size() - offset)
            return false;
        std::copy_n(data.begin() + offset, output.size(), output.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        CHECK(offset % provisioning::profile_slot_size == 0);
        CHECK(offset <= data.size() - provisioning::profile_slot_size);
        if (fail_erase)
            return false;
        std::fill_n(data.begin() + offset, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        CHECK(offset % provisioning::profile_page_size == 0);
        CHECK(page.size() == provisioning::profile_page_size);
        CHECK(offset <= data.size() - page.size());
        ++program_calls;
        if (fail_program_call == program_calls)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i) {
            CHECK((data[offset + i] & page[i]) == page[i]);
            data[offset + i] &= page[i];
        }
        return true;
    }
};

struct StandaloneMedia : standalone::Flash {
    std::array<std::uint8_t, 16384> data;
    StandaloneMedia() {
        data.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> output) override {
        if (offset > data.size() || output.size() > data.size() - offset)
            return false;
        std::copy_n(data.begin() + offset, output.size(), output.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        CHECK(offset % 4096 == 0 && offset <= data.size() - 4096);
        std::fill_n(data.begin() + offset, 4096, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        CHECK(offset % 256 == 0 && page.size() == 256 && offset <= data.size() - 256);
        for (std::size_t i = 0; i < page.size(); ++i) {
            CHECK((data[offset + i] & page[i]) == page[i]);
            data[offset + i] &= page[i];
        }
        return true;
    }
};

struct Validator : provisioning::CredentialValidator {
    unsigned calls = 0;
    bool validate(const provisioning::Profile& profile) override {
        ++calls;
        return profile.server_certificate.find("REJECT") == std::string::npos &&
               profile.hostname == "wsprrypico-010203.local" && profile.port == 18443;
    }
};

provisioning::Profile profile(std::string suffix = "A", std::string id = device) {
    return {std::move(id),
            "test-network-" + suffix,
            "test-password-" + suffix,
            "pool.ntp.org",
            "WsprryPico-010203.LOCAL.",
            18443,
            "-----BEGIN CERTIFICATE-----\nSERVER-" + suffix + "\n-----END CERTIFICATE-----\n",
            "-----BEGIN PRIVATE KEY-----\nKEY-" + suffix + "\n-----END PRIVATE KEY-----\n",
            "-----BEGIN CERTIFICATE-----\nCA-" + suffix + "\n-----END CERTIFICATE-----\n"};
}
provisioning::Authorization authorized() {
    return {true, true, true, "operator"};
}

struct Fixture {
    MemoryMedia media;
    provisioning::ProfileStore store{media};
    Validator validator;
    provisioning::Manager manager{store, validator, device};
    Fixture() {
        CHECK(store.load());
    }
};

void send(provisioning::Manager& manager, std::string_view session, std::string_view payload,
          unsigned& request, std::uint64_t now = 1) {
    const auto split = payload.size() / 2;
    auto first =
        manager.write(request_id(request++), session, 0, bytes(payload).first(split), false, now);
    CHECK(first.ok() && first.accepted_bytes == split);
    auto second = manager.write(request_id(request++), session, split,
                                bytes(payload).subspan(split), true, now + 1);
    CHECK(second.ok() && second.accepted_bytes == payload.size());
    CHECK(manager.status().state == provisioning::State::Ready);
}

void profile_validation() {
    auto original = profile();
    const auto encoded = provisioning::serialize_profile(original);
    const auto decoded = provisioning::parse_profile(encoded);
    original.hostname = "wsprrypico-010203.local";
    CHECK(decoded && *decoded == original);
    auto replace = [&](std::string from, std::string to) {
        auto changed = encoded;
        const auto offset = changed.find(from);
        CHECK(offset != changed.npos);
        changed.replace(offset, from.size(), to);
        CHECK(!provisioning::parse_profile(changed));
    };
    replace("\"version\":1", "\"version\":2");
    replace("test-password-A", "short");
    replace("pool.ntp.org", "127.0.0.1");
    replace("WsprryPico-010203.LOCAL.", "evil.example");
    replace("18443", "0");
    replace("-----END PRIVATE KEY-----", "-----END WRONG KEY-----");
    replace("\"tls\":", "\"extra\":1,\"tls\":");
    CHECK(!provisioning::parse_profile(std::string(provisioning::max_profile_bytes + 1, 'x')));
}

void lifecycle_and_transport() {
    Fixture f;
    unsigned request = 1;
    auto opened = f.manager.open(request_id(request++), session_a, device,
                                 provisioning::Transport::Ble, authorized(), 10);
    CHECK(opened.ok() && opened.generation == 0);
    const auto encoded = provisioning::serialize_profile(profile());
    send(f.manager, session_a, encoded, request, 11);
    const auto applied = f.manager.apply(request_id(request++), session_a, 0, {}, 13);
    CHECK(applied.ok() && applied.generation == 1);
    CHECK(f.manager.status().state == provisioning::State::Complete);
    CHECK(f.manager.status().staged_bytes == 0);
    CHECK(f.store.sequence() == 1);
    auto stored = provisioning::parse_profile(f.store.data());
    CHECK(stored && stored->client_ca.find("CA-A") != std::string::npos);

    auto softap = f.manager.open(request_id(request++), session_b, device,
                                 provisioning::Transport::SoftAp, authorized(), 20);
    CHECK(softap.ok());
    CHECK(f.manager.status().transport == provisioning::Transport::SoftAp);
    CHECK(f.manager.cancel(request_id(request++), session_b, 21).ok());
}

void authentication_identity_and_concurrency() {
    Fixture f;
    unsigned request = 30;
    auto auth = authorized();
    auth.authenticated = false;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble, auth, 1)
              .code == provisioning::Code::AuthenticationRequired);
    auth = authorized();
    auth.confidential = false;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble, auth, 2)
              .code == provisioning::Code::AuthenticationRequired);
    auth = authorized();
    auth.local = false;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble, auth, 3)
              .code == provisioning::Code::AuthenticationRequired);
    auth = authorized();
    auth.principal.clear();
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble, auth, 4)
              .code == provisioning::Code::AuthenticationRequired);
    CHECK(f.manager
              .open(request_id(request++), session_a, other_device, provisioning::Transport::Ble,
                    authorized(), 5)
              .code == provisioning::Code::WrongDevice);
    CHECK(f.manager
              .open(request_id(request++), "bad", device, provisioning::Transport::Ble,
                    authorized(), 6)
              .code == provisioning::Code::InvalidRequest);
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 7)
              .ok());
    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::SoftAp,
                    authorized(), 8)
              .code == provisioning::Code::SessionBusy);
    CHECK(f.manager.cancel(request_id(request++), session_a, 9).ok());
}

void malformed_oversize_and_ordering() {
    Fixture f;
    unsigned request = 50;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    CHECK(f.manager.write(request_id(request++), session_a, 1, bytes("{}"), true, 2).code ==
          provisioning::Code::OutOfOrder);
    CHECK(f.manager.apply(request_id(request++), session_a, 0, {}, 3).code ==
          provisioning::Code::Incomplete);
    CHECK(f.manager.write(request_id(request++), session_a, 0, bytes("{}"), true, 4).ok());
    CHECK(f.manager.apply(request_id(request++), session_a, 0, {}, 5).code ==
          provisioning::Code::Malformed);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 6)
              .ok());
    std::vector<std::uint8_t> large(provisioning::max_profile_bytes + 1, 'x');
    CHECK(f.manager.write(request_id(request++), session_b, 0, large, true, 7).code ==
          provisioning::Code::Oversize);
    CHECK(f.manager.status().state == provisioning::State::Failed);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 8)
              .ok());
    auto rejected = profile("REJECT");
    const auto rejected_payload = provisioning::serialize_profile(rejected);
    CHECK(f.manager.write(request_id(request++), session_a, 0, bytes(rejected_payload), true, 9)
              .ok());
    CHECK(f.manager.apply(request_id(request++), session_a, 0, {}, 10).code ==
          provisioning::Code::CredentialInvalid);
    CHECK(f.store.sequence() == 0 && f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 11)
              .ok());
    const auto wrong_device = provisioning::serialize_profile(profile("A", other_device));
    CHECK(f.manager.write(request_id(request++), session_b, 0, bytes(wrong_device), true, 12).ok());
    CHECK(f.manager.apply(request_id(request++), session_b, 0, {}, 13).code ==
          provisioning::Code::WrongDevice);
    CHECK(f.store.sequence() == 0 && f.manager.status().staged_bytes == 0);
}

void duplicate_replay_and_generation() {
    Fixture f;
    unsigned request = 70;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    const auto payload = provisioning::serialize_profile(profile());
    const auto write_id = request_id(request++);
    auto first = f.manager.write(write_id, session_a, 0, bytes(payload), true, 2);
    auto duplicate = f.manager.write(write_id, session_a, 0, bytes(payload), true, 3);
    CHECK(first.ok() && duplicate.ok() && duplicate.replayed);
    CHECK(f.manager.status().staged_bytes == payload.size());
    CHECK(f.manager.apply(request_id(request++), session_a, 1, {}, 4).code ==
          provisioning::Code::Conflict);
    const auto apply_id = request_id(request++);
    auto applied = f.manager.apply(apply_id, session_a, 0, {}, 5);
    auto replayed = f.manager.apply(apply_id, session_a, 0, {}, 6);
    CHECK(applied.ok() && replayed.ok() && replayed.replayed && f.store.sequence() == 1);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 7)
              .ok());
    const auto reused = request_id(request++);
    CHECK(f.manager.write(reused, session_b, 0, bytes("{"), false, 8).ok());
    CHECK(f.manager.write(reused, session_b, 1, bytes("}"), true, 9).code ==
          provisioning::Code::Replay);
    CHECK(f.manager.status().state == provisioning::State::Failed);
    CHECK(f.manager.status().staged_bytes == 0);
}

void timeout_cancel_and_resource_bounds() {
    Fixture f;
    unsigned request = 100;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1000)
              .ok());
    CHECK(f.manager.write(request_id(request++), session_a, 0, bytes("partial"), false, 1001).ok());
    f.manager.poll(1001 + provisioning::session_timeout_ms);
    CHECK(f.manager.status().state == provisioning::State::Expired);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::SoftAp,
                    authorized(), 40000)
              .ok());
    CHECK(f.manager.write(request_id(request++), session_b, 0, bytes("secret"), false, 40001).ok());
    const auto cancel_id = request_id(request++);
    auto cancelled = f.manager.cancel(cancel_id, session_b, 40002);
    auto duplicate = f.manager.cancel(cancel_id, session_b, 40003);
    CHECK(cancelled.ok() && duplicate.ok() && duplicate.replayed);
    CHECK(f.manager.status().state == provisioning::State::Cancelled);
    CHECK(f.manager.status().staged_bytes == 0);

    for (unsigned i = 0; i < 12; ++i) {
        auto bad = authorized();
        bad.authenticated = false;
        (void)f.manager.open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                             bad, 50000 + i);
    }
    CHECK(f.manager.status().replay_entries == provisioning::replay_capacity);
    f.manager.poll(50011 + provisioning::replay_retention_ms);
    CHECK(f.manager.status().replay_entries == 0);

    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 400000)
              .ok());
    for (unsigned i = 0; i < provisioning::fragment_capacity; ++i) {
        const std::uint8_t value = 'x';
        CHECK(
            f.manager
                .write(request_id(request++), session_a, i, std::span(&value, 1), false, 400001 + i)
                .ok());
    }
    const std::uint8_t excess = 'y';
    CHECK(f.manager
              .write(request_id(request++), session_a, provisioning::fragment_capacity,
                     std::span(&excess, 1), true, 400100)
              .code == provisioning::Code::Oversize);
    CHECK(f.manager.status().staged_bytes == 0);
}

void busy_state_and_rf_ownership() {
    Fixture f;
    unsigned request = 140;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    const auto payload = provisioning::serialize_profile(profile());
    CHECK(f.manager.write(request_id(request++), session_a, 0, bytes(payload), true, 2).ok());
    const std::array<provisioning::Activity, 6> blocked{{
        {.owned = true},
        {.output_known = false},
        {.output_active = true},
        {.armed = true},
        {.running = true},
        {.failed = true},
    }};
    for (const auto& activity : blocked) {
        CHECK(f.manager.apply(request_id(request++), session_a, 0, activity, 3).code ==
              provisioning::Code::Busy);
        CHECK(f.store.sequence() == 0 && f.manager.status().state == provisioning::State::Ready);
    }
    CHECK(f.manager.apply(request_id(request++), session_a, 0, {}, 4).ok());
}

void replacement_and_transaction_recovery() {
    MemoryMedia media;
    provisioning::ProfileStore store(media);
    CHECK(store.load());
    const auto first = provisioning::serialize_profile(profile("A"));
    const auto second = provisioning::serialize_profile(profile("B"));
    CHECK(store.replace(first));
    CHECK(store.sequence() == 1 && store.data() == first);
    const auto calls_before = media.program_calls;
    const auto payload_pages =
        (second.size() + provisioning::profile_page_size - 1) / provisioning::profile_page_size;
    media.fail_program_call = calls_before + payload_pages + 2;
    CHECK(!store.replace(second));
    provisioning::ProfileStore recovered(media);
    CHECK(recovered.load());
    CHECK(recovered.sequence() == 1 && recovered.data() == first);

    media.fail_program_call = 0;
    CHECK(recovered.replace(second));
    CHECK(recovered.sequence() == 2 && recovered.data() == second);
    CHECK(recovered.replace(second));
    CHECK(recovered.sequence() == 2 && recovered.data() == second);
    const auto active_payload =
        recovered.active_slot() * provisioning::profile_slot_size + provisioning::profile_page_size;
    media.data[active_payload] ^= 1;
    provisioning::ProfileStore corrupt_newest(media);
    CHECK(!corrupt_newest.load());

    MemoryMedia partial_media;
    provisioning::ProfileStore partial(partial_media);
    CHECK(partial.load() && partial.replace(first));
    const auto old_calls = partial_media.program_calls;
    partial_media.fail_program_call = old_calls + payload_pages + 2;
    CHECK(!partial.replace(second));
    const auto pending_slot = provisioning::profile_slot_size;
    partial_media
        .data[pending_slot + provisioning::profile_slot_size - provisioning::profile_page_size] = 0;
    provisioning::ProfileStore ambiguous_commit(partial_media);
    CHECK(!ambiguous_commit.load());

    MemoryMedia partial_header_media;
    provisioning::ProfileStore partial_header(partial_header_media);
    CHECK(partial_header.load() && partial_header.replace(first));
    partial_header_media.data[provisioning::profile_slot_size] = 0;
    provisioning::ProfileStore recovered_header(partial_header_media);
    CHECK(recovered_header.load());
    CHECK(recovered_header.sequence() == 1 && recovered_header.data() == first);

    MemoryMedia partial_erase_media;
    provisioning::ProfileStore partial_erase(partial_erase_media);
    CHECK(partial_erase.load() && partial_erase.replace(first));
    CHECK(partial_erase.replace(second));
    CHECK(partial_erase.active_slot() == 1);
    std::fill_n(partial_erase_media.data.begin(), 4096, 255);
    provisioning::ProfileStore recovered_erase(partial_erase_media);
    CHECK(recovered_erase.load());
    CHECK(recovered_erase.sequence() == 2 && recovered_erase.data() == second);

    const auto active_second_sector = provisioning::profile_slot_size + 4096;
    std::fill_n(partial_erase_media.data.begin() + active_second_sector, 4096, 255);
    provisioning::ProfileStore erased_active_commit(partial_erase_media);
    CHECK(!erased_active_commit.load());
}

void replacement_policy_and_existing_state_preservation() {
    StandaloneMedia station_media;
    standalone::Store station_store(station_media);
    CHECK(station_store.load());
    const auto config = standalone::parse_config(
        R"({"version":1,"enabled":true,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"old-network","password":"old-password","ntp_ipv4":"pool.ntp.org"},"schedules":[{"period_s":120,"phase_s":0}]})");
    CHECK(config && station_store.save(*config) &&
          station_store.reserve(1'900'000'000'000'000'000ULL));
    const auto before = station_media.data;

    Fixture f;
    unsigned request = 180;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    auto first = provisioning::serialize_profile(profile("A"));
    CHECK(f.manager.write(request_id(request++), session_a, 0, bytes(first), true, 2).ok());
    CHECK(f.manager.apply(request_id(request++), session_a, 0, {}, 3).ok());
    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 4)
              .ok());
    auto second = provisioning::serialize_profile(profile("B"));
    CHECK(f.manager.write(request_id(request++), session_b, 0, bytes(second), true, 5).ok());
    CHECK(f.manager.apply(request_id(request++), session_b, 1, {}, 6).ok());
    CHECK(f.store.sequence() == 2);
    CHECK(f.store.data().find("CA-B") != std::string::npos);
    CHECK(f.store.data().find("CA-A") == std::string::npos);

    CHECK(station_media.data == before);
    standalone::Store reloaded(station_media);
    CHECK(reloaded.load());
    CHECK(reloaded.config() && *reloaded.config() == *config);
    CHECK(reloaded.watermark() == 1'900'000'000'000'000'000ULL);
}

void runtime_selection_and_overlay() {
    const auto base = standalone::parse_config(
        R"({"version":1,"enabled":true,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"old-network","password":"old-password","ntp_ipv4":"pool.ntp.org"},"schedules":[{"period_s":120,"phase_s":0}]})");
    CHECK(base);

    MemoryMedia empty_media;
    provisioning::ProfileStore empty_store(empty_media);
    CHECK(empty_store.load());
    provisioning::RuntimeProfile factory;
    CHECK(factory.load(empty_store, device));
    CHECK(factory.source() == provisioning::RuntimeSource::Factory);
    CHECK(factory.fault() == provisioning::RuntimeFault::None);
    CHECK(factory.generation() == 0 && !factory.profile());
    const auto factory_config = factory.overlay(*base);
    CHECK(factory_config && *factory_config == *base);

    MemoryMedia provisioned_media;
    provisioning::ProfileStore provisioned_store(provisioned_media);
    CHECK(provisioned_store.load());
    CHECK(provisioned_store.replace(provisioning::serialize_profile(profile("runtime"))));
    provisioning::RuntimeProfile provisioned;
    CHECK(provisioned.load(provisioned_store, device));
    CHECK(provisioned.source() == provisioning::RuntimeSource::Provisioned);
    CHECK(provisioned.generation() == 1 && provisioned.profile());
    const auto selected = provisioned.overlay(*base);
    CHECK(selected);
    CHECK(selected->ssid == "test-network-runtime");
    CHECK(selected->password == "test-password-runtime");
    CHECK(selected->ntp_ipv4 == "pool.ntp.org");
    CHECK(selected->enabled == base->enabled && selected->expires_utc_s == base->expires_utc_s);
    CHECK(selected->callsign == base->callsign && selected->locator == base->locator);
    CHECK(selected->power_dbm == base->power_dbm && selected->schedules == base->schedules);
    const auto material = provisioning::credentials(*provisioned.profile());
    CHECK(material.device_id == device && material.hostname == "wsprrypico-010203.local");
    CHECK(material.port == 18443 && material.server_private_key.find("KEY-runtime") != material.server_private_key.npos);

    provisioning::RuntimeProfile wrong_device;
    CHECK(!wrong_device.load(provisioned_store, other_device));
    CHECK(wrong_device.source() == provisioning::RuntimeSource::Fault);
    CHECK(wrong_device.fault() == provisioning::RuntimeFault::WrongDevice);
    CHECK(!wrong_device.overlay(*base));

    MemoryMedia malformed_media;
    provisioning::ProfileStore malformed_store(malformed_media);
    CHECK(malformed_store.load() && malformed_store.replace("{}"));
    provisioning::RuntimeProfile malformed;
    CHECK(!malformed.load(malformed_store, device));
    CHECK(malformed.source() == provisioning::RuntimeSource::Fault);
    CHECK(malformed.fault() == provisioning::RuntimeFault::Malformed);
    CHECK(!malformed.overlay(*base));
}
} // namespace

int main() {
    profile_validation();
    lifecycle_and_transport();
    authentication_identity_and_concurrency();
    malformed_oversize_and_ordering();
    duplicate_replay_and_generation();
    timeout_cancel_and_resource_bounds();
    busy_state_and_rf_ownership();
    replacement_and_transaction_recovery();
    replacement_policy_and_existing_state_preservation();
    runtime_selection_and_overlay();
    std::cout << "provisioning tests passed\n";
}
