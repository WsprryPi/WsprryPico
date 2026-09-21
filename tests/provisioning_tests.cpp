#include "provisioning/command.hpp"
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

std::string base64(std::span<const std::uint8_t> input) {
    constexpr char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string output;
    output.reserve((input.size() + 2) / 3 * 4);
    for (std::size_t offset = 0; offset < input.size(); offset += 3) {
        const unsigned a = input[offset];
        const unsigned b = offset + 1 < input.size() ? input[offset + 1] : 0;
        const unsigned c = offset + 2 < input.size() ? input[offset + 2] : 0;
        output += alphabet[a >> 2];
        output += alphabet[((a & 3) << 4) | (b >> 4)];
        output += offset + 1 < input.size() ? alphabet[((b & 15) << 2) | (c >> 6)] : '=';
        output += offset + 2 < input.size() ? alphabet[c & 63] : '=';
    }
    return output;
}

std::string command(std::string_view operation, std::string_view request,
                    std::string_view session = session_a, std::string_view requested = device,
                    std::string_view extra = {}) {
    return "{\"version\":1,\"operation\":\"" + std::string(operation) + "\",\"request_id\":\"" +
           std::string(request) + "\",\"session_id\":\"" + std::string(session) +
           "\",\"device_id\":\"" + std::string(requested) + "\"" + std::string(extra) + "}";
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

struct Activator : provisioning::ProfileActivator {
    bool succeed = true;
    unsigned calls = 0;
    unsigned fail_closed_calls = 0;
    std::uint64_t generation = 0;
    std::string observed_ssid;
    bool activate(const provisioning::Profile& candidate, std::uint64_t next) override {
        ++calls;
        generation = next;
        observed_ssid = candidate.ssid;
        return succeed;
    }
    void fail_closed(std::uint64_t failed) override {
        ++fail_closed_calls;
        generation = failed;
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

provisioning::Result
session_write(provisioning::Manager& manager, std::string_view request, std::string_view session,
              std::size_t offset, std::span<const std::uint8_t> input, bool final,
              std::uint64_t now, provisioning::Transport transport = provisioning::Transport::Ble,
              const provisioning::Authorization& authorization = authorized()) {
    return manager.write(request, session, offset, input, final, transport, authorization, now);
}
provisioning::Result
session_apply(provisioning::Manager& manager, std::string_view request, std::string_view session,
              std::uint64_t expected_generation, const provisioning::Activity& activity,
              std::uint64_t now, provisioning::Transport transport = provisioning::Transport::Ble,
              const provisioning::Authorization& authorization = authorized()) {
    return manager.apply(request, session, expected_generation, activity, transport, authorization,
                         now);
}
provisioning::Result
session_cancel(provisioning::Manager& manager, std::string_view request, std::string_view session,
               std::uint64_t now, provisioning::Transport transport = provisioning::Transport::Ble,
               const provisioning::Authorization& authorization = authorized()) {
    return manager.cancel(request, session, transport, authorization, now);
}

void send(provisioning::Manager& manager, std::string_view session, std::string_view payload,
          unsigned& request, std::uint64_t now = 1) {
    const auto split = payload.size() / 2;
    auto first = session_write(manager, request_id(request++), session, 0,
                               bytes(payload).first(split), false, now);
    CHECK(first.ok() && first.accepted_bytes == split);
    auto second = session_write(manager, request_id(request++), session, split,
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
    const auto applied = session_apply(f.manager, request_id(request++), session_a, 0, {}, 13);
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
    CHECK(session_cancel(f.manager, request_id(request++), session_b, 21,
                         provisioning::Transport::SoftAp)
              .ok());
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
    CHECK(session_cancel(f.manager, request_id(request++), session_a, 9).ok());
}

void malformed_oversize_and_ordering() {
    Fixture f;
    unsigned request = 50;
    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    CHECK(
        session_write(f.manager, request_id(request++), session_a, 1, bytes("{}"), true, 2).code ==
        provisioning::Code::OutOfOrder);
    CHECK(session_apply(f.manager, request_id(request++), session_a, 0, {}, 3).code ==
          provisioning::Code::Incomplete);
    CHECK(session_write(f.manager, request_id(request++), session_a, 0, bytes("{}"), true, 4).ok());
    CHECK(session_apply(f.manager, request_id(request++), session_a, 0, {}, 5).code ==
          provisioning::Code::Malformed);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 6)
              .ok());
    std::vector<std::uint8_t> large(provisioning::max_profile_bytes + 1, 'x');
    CHECK(session_write(f.manager, request_id(request++), session_b, 0, large, true, 7).code ==
          provisioning::Code::Oversize);
    CHECK(f.manager.status().state == provisioning::State::Failed);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 8)
              .ok());
    auto rejected = profile("REJECT");
    const auto rejected_payload = provisioning::serialize_profile(rejected);
    CHECK(session_write(f.manager, request_id(request++), session_a, 0, bytes(rejected_payload),
                        true, 9)
              .ok());
    CHECK(session_apply(f.manager, request_id(request++), session_a, 0, {}, 10).code ==
          provisioning::Code::CredentialInvalid);
    CHECK(f.store.sequence() == 0 && f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 11)
              .ok());
    const auto wrong_device = provisioning::serialize_profile(profile("A", other_device));
    CHECK(
        session_write(f.manager, request_id(request++), session_b, 0, bytes(wrong_device), true, 12)
            .ok());
    CHECK(session_apply(f.manager, request_id(request++), session_b, 0, {}, 13).code ==
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
    auto first = session_write(f.manager, write_id, session_a, 0, bytes(payload), true, 2);
    auto duplicate = session_write(f.manager, write_id, session_a, 0, bytes(payload), true, 3);
    CHECK(first.ok() && duplicate.ok() && duplicate.replayed);
    CHECK(f.manager.status().staged_bytes == payload.size());
    CHECK(session_apply(f.manager, request_id(request++), session_a, 1, {}, 4).code ==
          provisioning::Code::Conflict);
    const auto apply_id = request_id(request++);
    auto applied = session_apply(f.manager, apply_id, session_a, 0, {}, 5);
    auto replayed = session_apply(f.manager, apply_id, session_a, 0, {}, 6);
    CHECK(applied.ok() && replayed.ok() && replayed.replayed && f.store.sequence() == 1);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 7)
              .ok());
    const auto reused = request_id(request++);
    CHECK(session_write(f.manager, reused, session_b, 0, bytes("{"), false, 8).ok());
    CHECK(session_write(f.manager, reused, session_b, 1, bytes("}"), true, 9).code ==
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
    CHECK(
        session_write(f.manager, request_id(request++), session_a, 0, bytes("partial"), false, 1001)
            .ok());
    f.manager.poll(1001 + provisioning::session_timeout_ms);
    CHECK(f.manager.status().state == provisioning::State::Expired);
    CHECK(f.manager.status().staged_bytes == 0);

    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::SoftAp,
                    authorized(), 40000)
              .ok());
    CHECK(session_write(f.manager, request_id(request++), session_b, 0, bytes("secret"), false,
                        40001, provisioning::Transport::SoftAp)
              .ok());
    const auto cancel_id = request_id(request++);
    auto cancelled =
        session_cancel(f.manager, cancel_id, session_b, 40002, provisioning::Transport::SoftAp);
    auto duplicate =
        session_cancel(f.manager, cancel_id, session_b, 40003, provisioning::Transport::SoftAp);
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
        CHECK(session_write(f.manager, request_id(request++), session_a, i, std::span(&value, 1),
                            false, 400001 + i)
                  .ok());
    }
    const std::uint8_t excess = 'y';
    CHECK(session_write(f.manager, request_id(request++), session_a,
                        provisioning::fragment_capacity, std::span(&excess, 1), true, 400100)
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
    CHECK(session_write(f.manager, request_id(request++), session_a, 0, bytes(payload), true, 2)
              .ok());
    const std::array<provisioning::Activity, 6> blocked{{
        {.owned = true},
        {.output_known = false},
        {.output_active = true},
        {.armed = true},
        {.running = true},
        {.failed = true},
    }};
    for (const auto& activity : blocked) {
        CHECK(session_apply(f.manager, request_id(request++), session_a, 0, activity, 3).code ==
              provisioning::Code::Busy);
        CHECK(f.store.sequence() == 0 && f.manager.status().state == provisioning::State::Ready);
    }
    CHECK(session_apply(f.manager, request_id(request++), session_a, 0, {}, 4).ok());
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
    CHECK(
        session_write(f.manager, request_id(request++), session_a, 0, bytes(first), true, 2).ok());
    CHECK(session_apply(f.manager, request_id(request++), session_a, 0, {}, 3).ok());
    CHECK(f.manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 4)
              .ok());
    auto second = provisioning::serialize_profile(profile("B"));
    CHECK(
        session_write(f.manager, request_id(request++), session_b, 0, bytes(second), true, 5).ok());
    CHECK(session_apply(f.manager, request_id(request++), session_b, 1, {}, 6).ok());
    CHECK(f.store.sequence() == 2);
    CHECK(f.store.data().find("CA-B") != std::string::npos);
    CHECK(f.store.data().find("CA-A") == std::string::npos);

    CHECK(station_media.data == before);
    standalone::Store reloaded(station_media);
    CHECK(reloaded.load());
    CHECK(reloaded.config() && *reloaded.config() == *config);
    CHECK(reloaded.watermark() == 1'900'000'000'000'000'000ULL);
}

void command_adapter_contract() {
    Fixture f;
    provisioning::CommandAdapter ble(f.manager, device, provisioning::Transport::Ble);
    CHECK(ble.identity() == R"({"device_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","generation":0})");
    provisioning::CommandAdapter invalid_identity(f.manager, "invalid",
                                                  provisioning::Transport::Ble);
    CHECK(invalid_identity.identity().empty());
    unsigned request = 240;
    const auto open_id = request_id(request++);
    const auto opened = ble.handle(command("open", open_id), authorized(), {}, 1);
    CHECK(opened.code == provisioning::Code::Ok && opened.notify());
    CHECK(opened.notification.find("\"request_id\":\"" + open_id + "\"") != std::string::npos);
    CHECK(opened.notification.find("\"ok\":true") != std::string::npos);
    const auto duplicate_open = ble.handle(command("open", open_id), authorized(), {}, 2);
    CHECK(duplicate_open.code == provisioning::Code::Ok);
    CHECK(duplicate_open.notification.find("\"replayed\":true") != std::string::npos);

    const auto encoded = provisioning::serialize_profile(profile("wire"));
    std::size_t offset = 0;
    while (offset < encoded.size()) {
        const auto count =
            std::min<std::size_t>(provisioning::max_fragment_bytes, encoded.size() - offset);
        const auto payload = base64(bytes(encoded).subspan(offset, count));
        const bool final = offset + count == encoded.size();
        const auto extra = ",\"offset\":" + std::to_string(offset) +
                           ",\"final\":" + (final ? "true" : "false") + ",\"payload\":\"" +
                           payload + "\"";
        const auto wire_command = command("write", request_id(request++), session_a, device, extra);
        const auto written = ble.handle(wire_command, authorized(), {}, 2 + offset);
        CHECK(written.code == provisioning::Code::Ok);
        CHECK(written.notification.find("test-password") == std::string::npos);
        CHECK(written.notification.find("PRIVATE KEY") == std::string::npos);
        offset += count;
    }
    const auto apply_id = request_id(request++);
    const auto applied =
        ble.handle(command("apply", apply_id, session_a, device, ",\"expected_generation\":0"),
                   authorized(), {}, 10000);
    CHECK(applied.code == provisioning::Code::Ok);
    CHECK(applied.notification.find("\"generation\":1") != std::string::npos);
    CHECK(ble.identity() == R"({"device_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","generation":1})");

    provisioning::CommandAdapter softap(f.manager, device, provisioning::Transport::SoftAp);
    CHECK(softap.handle(command("open", request_id(request++), session_b), authorized(), {}, 10001)
              .code == provisioning::Code::Ok);
    CHECK(f.manager.status().transport == provisioning::Transport::SoftAp);
    CHECK(
        softap.handle(command("cancel", request_id(request++), session_b), authorized(), {}, 10002)
            .code == provisioning::Code::Ok);
}

void command_adapter_rejections_and_busy_state() {
    Fixture f;
    provisioning::CommandAdapter adapter(f.manager, device, provisioning::Transport::Ble);
    unsigned request = 300;
    CHECK(!adapter.handle("{", authorized(), {}, 1).notify());
    CHECK(
        !adapter.handle(std::string(provisioning::max_command_bytes + 1, 'x'), authorized(), {}, 1)
             .notify());
    const auto duplicate_id = request_id(request++);
    CHECK(!adapter
               .handle("{\"request_id\":\"" + duplicate_id + "\",\"request_id\":\"" + duplicate_id +
                           "\"}",
                       authorized(), {}, 1)
               .notify());
    CHECK(!adapter.handle(command("open", "bad"), authorized(), {}, 1).notify());
    const auto missing_id = request_id(request++);
    CHECK(adapter
              .handle("{\"version\":1,\"operation\":\"open\",\"request_id\":\"" + missing_id +
                          "\",\"device_id\":\"" + device + "\"}",
                      authorized(), {}, 1)
              .code == provisioning::Code::InvalidRequest);
    const auto operation_type_id = request_id(request++);
    CHECK(adapter
              .handle("{\"version\":1,\"operation\":1,\"request_id\":\"" + operation_type_id +
                          "\",\"session_id\":\"" + session_a + "\",\"device_id\":\"" + device +
                          "\"}",
                      authorized(), {}, 1)
              .code == provisioning::Code::InvalidRequest);

    auto escaped_operation = command("open", request_id(request++));
    escaped_operation.replace(escaped_operation.find("open"), 4,
                              std::string("o") + static_cast<char>(92) + "u0070en");
    CHECK(adapter.handle(escaped_operation, authorized(), {}, 1).code ==
          provisioning::Code::InvalidRequest);
    auto escaped_field = command("open", request_id(request++));
    escaped_field.replace(escaped_field.find("version"), 7,
                          std::string("vers") + static_cast<char>(92) + "u0069on");
    CHECK(adapter.handle(escaped_field, authorized(), {}, 1).code ==
          provisioning::Code::InvalidRequest);
    auto escaped_session = command("open", request_id(request++));
    escaped_session.replace(escaped_session.find(session_a), 1,
                            std::string(1, static_cast<char>(92)) + "u0031");
    CHECK(adapter.handle(escaped_session, authorized(), {}, 1).code ==
          provisioning::Code::InvalidRequest);

    auto version = command("open", request_id(request++));
    version.replace(version.find("\"version\":1"), 11, "\"version\":2");
    CHECK(adapter.handle(version, authorized(), {}, 2).code == provisioning::Code::InvalidRequest);
    CHECK(adapter
              .handle(command("open", request_id(request++), session_a, device, ",\"extra\":1"),
                      authorized(), {}, 3)
              .code == provisioning::Code::InvalidRequest);
    CHECK(adapter.handle(command("unknown", request_id(request++)), authorized(), {}, 4).code ==
          provisioning::Code::InvalidRequest);
    CHECK(adapter
              .handle(command("open", request_id(request++), session_a, other_device), authorized(),
                      {}, 5)
              .code == provisioning::Code::WrongDevice);
    auto unauthenticated = authorized();
    unauthenticated.authenticated = false;
    const auto rejected =
        adapter.handle(command("open", request_id(request++)), unauthenticated, {}, 6);
    CHECK(rejected.code == provisioning::Code::AuthenticationRequired);
    CHECK(rejected.notification.find("password") == std::string::npos);
    auto nonconfidential = authorized();
    nonconfidential.confidential = false;
    CHECK(adapter.handle(command("open", request_id(request++)), nonconfidential, {}, 6).code ==
          provisioning::Code::AuthenticationRequired);
    auto nonlocal = authorized();
    nonlocal.local = false;
    CHECK(adapter.handle(command("open", request_id(request++)), nonlocal, {}, 6).code ==
          provisioning::Code::AuthenticationRequired);
    auto anonymous = authorized();
    anonymous.principal.clear();
    CHECK(adapter.handle(command("open", request_id(request++)), anonymous, {}, 6).code ==
          provisioning::Code::AuthenticationRequired);
    CHECK(adapter.handle(command("open", request_id(request++)), authorized(), {}, 7).code ==
          provisioning::Code::Ok);

    const auto write_extra = ",\"offset\":0,\"final\":false,\"payload\":\"eA==\"";
    CHECK(adapter
              .handle(command("write", request_id(request++), session_a, device, write_extra),
                      unauthenticated, {}, 7)
              .code == provisioning::Code::AuthenticationRequired);
    auto other_principal = authorized();
    other_principal.principal = "other-operator";
    CHECK(adapter
              .handle(command("write", request_id(request++), session_a, device, write_extra),
                      other_principal, {}, 7)
              .code == provisioning::Code::AuthenticationRequired);
    provisioning::CommandAdapter cross_transport(f.manager, device,
                                                 provisioning::Transport::SoftAp);
    CHECK(cross_transport
              .handle(command("write", request_id(request++), session_a, device, write_extra),
                      authorized(), {}, 7)
              .code == provisioning::Code::AuthenticationRequired);
    CHECK(f.manager.status().staged_bytes == 0);
    CHECK(adapter.handle(command("cancel", request_id(request++)), unauthenticated, {}, 7).code ==
          provisioning::Code::AuthenticationRequired);
    CHECK(cross_transport
              .handle(command("cancel", request_id(request++), session_a), authorized(), {}, 7)
              .code == provisioning::Code::AuthenticationRequired);
    CHECK(f.manager.status().state == provisioning::State::Receiving);

    const std::array<std::string, 7> invalid_writes{{
        ",\"offset\":0,\"final\":true,\"payload\":\"\"",
        ",\"offset\":0,\"final\":true,\"payload\":\"Zg=\"",
        ",\"offset\":0,\"final\":true,\"payload\":\"Zh==\"",
        ",\"offset\":0,\"final\":true,\"payload\":\"Zg=A\"",
        ",\"offset\":-1,\"final\":true,\"payload\":\"eA==\"",
        ",\"offset\":\"0\",\"final\":true,\"payload\":\"eA==\"",
        ",\"offset\":0,\"final\":1,\"payload\":\"eA==\"",
    }};
    for (const auto& extra : invalid_writes)
        CHECK(adapter
                  .handle(command("write", request_id(request++), session_a, device, extra),
                          authorized(), {}, 8)
                  .code == provisioning::Code::InvalidRequest);
    CHECK(adapter
              .handle(command("write", request_id(request++), session_a, device,
                              ",\"offset\":" + std::to_string(provisioning::max_wire_integer) +
                                  ",\"final\":true,\"payload\":\"eA==\""),
                      authorized(), {}, 8)
              .code == provisioning::Code::OutOfOrder);
    CHECK(!adapter
               .handle(command("write", request_id(request++), session_a, device,
                               ",\"offset\":2147483648,\"final\":true,\"payload\":\"eA==\""),
                       authorized(), {}, 8)
               .notify());
    const std::string too_large_fragment(65, 'x');
    const auto large_extra =
        ",\"offset\":0,\"final\":true,\"payload\":\"" + base64(bytes(too_large_fragment)) + "\"";
    CHECK(adapter
              .handle(command("write", request_id(request++), session_a, device, large_extra),
                      authorized(), {}, 9)
              .code == provisioning::Code::InvalidRequest);
    CHECK(adapter
              .handle(command("write", request_id(request++), session_a, device,
                              ",\"offset\":1,\"final\":true,\"payload\":\"eA==\""),
                      authorized(), {}, 10)
              .code == provisioning::Code::OutOfOrder);
    CHECK(adapter.handle(command("cancel", request_id(request++)), authorized(), {}, 11).code ==
          provisioning::Code::Ok);

    CHECK(adapter.handle(command("open", request_id(request++)), authorized(), {}, 12).code ==
          provisioning::Code::Ok);
    const auto encoded = provisioning::serialize_profile(profile("busy-wire"));
    std::size_t offset = 0;
    while (offset < encoded.size()) {
        const auto count =
            std::min<std::size_t>(provisioning::max_fragment_bytes, encoded.size() - offset);
        const bool final = offset + count == encoded.size();
        const auto extra = ",\"offset\":" + std::to_string(offset) +
                           ",\"final\":" + (final ? "true" : "false") + ",\"payload\":\"" +
                           base64(bytes(encoded).subspan(offset, count)) + "\"";
        CHECK(adapter
                  .handle(command("write", request_id(request++), session_a, device, extra),
                          authorized(), {}, 13 + offset)
                  .code == provisioning::Code::Ok);
        offset += count;
    }
    CHECK(adapter
              .handle(command("apply", request_id(request++), session_a, device,
                              ",\"expected_generation\":0"),
                      other_principal, {}, 9999)
              .code == provisioning::Code::AuthenticationRequired);
    CHECK(cross_transport
              .handle(command("apply", request_id(request++), session_a, device,
                              ",\"expected_generation\":0"),
                      authorized(), {}, 9999)
              .code == provisioning::Code::AuthenticationRequired);
    CHECK(adapter
              .handle(command("apply", request_id(request++), session_a, device,
                              ",\"expected_generation\":" +
                                  std::to_string(provisioning::max_wire_integer)),
                      authorized(), {}, 9999)
              .code == provisioning::Code::Conflict);
    CHECK(!adapter
               .handle(command("apply", request_id(request++), session_a, device,
                               ",\"expected_generation\":2147483648"),
                       authorized(), {}, 9999)
               .notify());
    CHECK(adapter
              .handle(command("apply", request_id(request++), session_a, device,
                              ",\"expected_generation\":\"0\""),
                      authorized(), {}, 9999)
              .code == provisioning::Code::InvalidRequest);
    const std::array<provisioning::Activity, 6> blocked{{
        {.owned = true},
        {.output_known = false},
        {.output_active = true},
        {.armed = true},
        {.running = true},
        {.failed = true},
    }};
    for (const auto& busy_activity : blocked)
        CHECK(adapter
                  .handle(command("apply", request_id(request++), session_a, device,
                                  ",\"expected_generation\":0"),
                          authorized(), busy_activity, 10000)
                  .code == provisioning::Code::Busy);
    CHECK(f.store.sequence() == 0 && f.manager.status().state == provisioning::State::Ready);
    const auto conflicting_id = request_id(request++);
    provisioning::Activity owned;
    owned.owned = true;
    CHECK(adapter
              .handle(
                  command("apply", conflicting_id, session_a, device, ",\"expected_generation\":0"),
                  authorized(), owned, 10001)
              .code == provisioning::Code::Busy);
    CHECK(adapter.handle(command("cancel", conflicting_id), authorized(), {}, 10002).code ==
          provisioning::Code::Replay);
    CHECK(f.manager.status().state == provisioning::State::Failed &&
          f.manager.status().staged_bytes == 0);
}

void activation_handoff_and_fail_closed_policy() {
    MemoryMedia media;
    provisioning::ProfileStore store(media);
    Validator validator;
    Activator activator;
    CHECK(store.load());
    provisioning::Manager manager(store, validator, device, &activator);
    unsigned request = 400;
    const auto first = provisioning::serialize_profile(profile("activate-A"));
    CHECK(manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 1)
              .ok());
    send(manager, session_a, first, request, 2);
    const auto first_apply_id = request_id(request++);
    const auto first_result = session_apply(manager, first_apply_id, session_a, 0, {}, 4);
    CHECK(first_result.ok() && first_result.generation == 1);
    CHECK(activator.calls == 1 && activator.fail_closed_calls == 0 && activator.generation == 1);
    CHECK(activator.observed_ssid == "test-network-activate-A");
    const auto replayed = session_apply(manager, first_apply_id, session_a, 0, {}, 5);
    CHECK(replayed.ok() && replayed.replayed && activator.calls == 1);

    CHECK(manager
              .open(request_id(request++), session_b, device, provisioning::Transport::Ble,
                    authorized(), 6)
              .ok());
    send(manager, session_b, first, request, 7);
    CHECK(session_apply(manager, request_id(request++), session_b, 1, {}, 9).ok());
    CHECK(store.sequence() == 1 && activator.calls == 1);

    activator.succeed = false;
    const auto second = provisioning::serialize_profile(profile("activate-B"));
    CHECK(manager
              .open(request_id(request++), session_a, device, provisioning::Transport::Ble,
                    authorized(), 10)
              .ok());
    send(manager, session_a, second, request, 11);
    const auto failed_id = request_id(request++);
    const auto failed = session_apply(manager, failed_id, session_a, 1, {}, 13);
    CHECK(failed.code == provisioning::Code::ActivationFault && failed.generation == 2);
    CHECK(provisioning::code_name(failed.code) == "activation_fault");
    CHECK(manager.status().state == provisioning::State::Failed &&
          manager.status().staged_bytes == 0 && store.sequence() == 2);
    CHECK(activator.calls == 2 && activator.fail_closed_calls == 1 && activator.generation == 2);
    CHECK(store.data().find("CA-activate-B") != std::string::npos);
    CHECK(store.data().find("CA-activate-A") == std::string::npos);
    const auto failed_replay = session_apply(manager, failed_id, session_a, 1, {}, 14);
    CHECK(failed_replay.code == provisioning::Code::ActivationFault && failed_replay.replayed);
    CHECK(activator.calls == 2 && activator.fail_closed_calls == 1);
    provisioning::RuntimeProfile selected;
    CHECK(selected.load(store, device));
    CHECK(selected.generation() == 2 && selected.profile());
    CHECK(selected.profile()->ssid == "test-network-activate-B");
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
    CHECK(material.port == 18443 &&
          material.server_private_key.find("KEY-runtime") != material.server_private_key.npos);

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
    command_adapter_contract();
    command_adapter_rejections_and_busy_state();
    activation_handoff_and_fail_closed_policy();
    runtime_selection_and_overlay();
    std::cout << "provisioning tests passed\n";
}
