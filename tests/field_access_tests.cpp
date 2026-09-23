#include "provisioning/access.hpp"
#include "provisioning/ble_session.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/gatt_framing.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/reset.hpp"
#include "provisioning/softap_http.hpp"
#include "time/controller_time.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <span>
#include <string>
#include <vector>

#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                    \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)

namespace {
using namespace wsprrypico;

class AccessMemory final : public provisioning::AccessMedia {
  public:
    std::array<std::uint8_t, provisioning::access_media_size> bytes;
    int fail_at = -1;
    int operation = 0;
    AccessMemory() {
        bytes.fill(255);
    }
    bool admitted() {
        return fail_at < 0 || operation++ != fail_at;
    }
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset + out.size() > bytes.size())
            return false;
        std::copy_n(bytes.begin() + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (!admitted() || offset % provisioning::access_slot_size ||
            offset + provisioning::access_slot_size > bytes.size())
            return false;
        std::fill_n(bytes.begin() + offset, provisioning::access_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (!admitted() || page.size() != provisioning::access_page_size ||
            offset % provisioning::access_page_size || offset + page.size() > bytes.size())
            return false;
        for (std::size_t i = 0; i < page.size(); ++i) {
            if ((bytes[offset + i] & page[i]) != page[i])
                return false;
            bytes[offset + i] &= page[i];
        }
        return true;
    }
};

class ProfileMemory final : public provisioning::Media {
  public:
    std::array<std::uint8_t, provisioning::profile_media_size> bytes;
    int fail_at = -1;
    int operation = 0;
    ProfileMemory() {
        bytes.fill(255);
    }
    bool admitted() {
        return fail_at < 0 || operation++ != fail_at;
    }
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset + out.size() > bytes.size())
            return false;
        std::copy_n(bytes.begin() + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (!admitted() || offset % provisioning::profile_slot_size ||
            offset + provisioning::profile_slot_size > bytes.size())
            return false;
        std::fill_n(bytes.begin() + offset, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (!admitted() || page.size() != provisioning::profile_page_size ||
            offset % provisioning::profile_page_size || offset + page.size() > bytes.size())
            return false;
        for (std::size_t i = 0; i < page.size(); ++i) {
            if ((bytes[offset + i] & page[i]) != page[i])
                return false;
            bytes[offset + i] &= page[i];
        }
        return true;
    }
};

class Bonds final : public provisioning::BondStore {
  public:
    bool erase_result = true;
    bool erase_all_result = true;
    std::vector<std::uint64_t> erased;
    unsigned all = 0;
    bool erase(std::uint64_t peer) override {
        erased.push_back(peer);
        return erase_result;
    }
    bool erase_all() override {
        ++all;
        return erase_all_result;
    }
};

class Random final : public provisioning::RandomSource {
  public:
    std::uint8_t next = 1;
    bool fill(std::span<std::uint8_t> bytes) override {
        for (auto& value : bytes)
            value = next++;
        return true;
    }
};

class RejectingValidator final : public provisioning::CredentialValidator {
  public:
    bool validate(const provisioning::Profile&) override { return false; }
};

class ResetFixture final : public provisioning::ResetTargets {
  public:
    provisioning::Activity current{};
    std::array<std::uint8_t, 16 * 1024> operational{};
    bool operation_result = true;
    bool bond_result = true;
    bool operation_done = false;
    bool bond_done = false;
    ResetFixture() {
        operational.fill(0x5a);
    }
    provisioning::Activity activity() const override {
        return current;
    }
    bool erase_operational() override {
        if (!operation_result)
            return false;
        operational.fill(255);
        operation_done = true;
        return true;
    }
    bool operational_erased() const override {
        return operation_done &&
               std::all_of(operational.begin(), operational.end(),
                           [](std::uint8_t value) { return value == 255; });
    }
    bool erase_bonds() override {
        if (!bond_result)
            return false;
        bond_done = true;
        return true;
    }
    bool bonds_erased() const override {
        return bond_done;
    }
};

class Led final : public provisioning::IndicatorOutput {
  public:
    bool result = true;
    std::vector<bool> writes;
    bool write(bool on) override {
        writes.push_back(on);
        return result;
    }
};

constexpr std::string_view device = "00112233445566778899aabbccddeeff";

provisioning::RequestBinding binding(std::string operation = "access") {
    provisioning::RequestBinding value;
    value.device_id = device;
    value.principal = "operator-a";
    value.session_id = "session-a";
    value.operation = std::move(operation);
    value.nonce = "nonce-a";
    const std::string parameters = "canonical-parameters";
    value.parameters = wtp::sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(parameters.data()), parameters.size()));
    return value;
}

provisioning::AccessRecord initial_record(const provisioning::LocalIdentity& identity) {
    provisioning::AccessRecord record;
    record.epoch = 1;
    record.password = identity.default_password;
    return record;
}

void identity_and_journal() {
    const auto identity = provisioning::derive_local_identity(device, "02:11:22:0A:60:DF");
    CHECK(identity);
    CHECK(identity->suffix == "0a60df");
    CHECK(identity->hostname == "wsprrypico-0a60df.local");
    CHECK(identity->advertising_name == "WsprryPico-0a60df");
    CHECK(identity->softap_ssid == "WsprryPico-0a60df");
    CHECK(identity->default_password == "wspr-0a60df");
    CHECK(!provisioning::derive_local_identity("A", "02:11:22:0a:60:df"));
    CHECK(!provisioning::derive_local_identity(device, "00:00:00:00:00:00"));
    CHECK(!provisioning::derive_local_identity(device, "01:11:22:0a:60:df"));
    CHECK(!provisioning::derive_local_identity(device, "0211220a60df"));
    CHECK(!provisioning::derive_local_identity(device, "02-11-22-0a-60-df"));
    CHECK(!provisioning::derive_local_identity(device, "02:11:22:0a:60-df"));
    CHECK(!provisioning::valid_local_password("short"));
    CHECK(provisioning::valid_local_password(identity->default_password));

    AccessMemory media;
    provisioning::AccessStore store(media);
    CHECK(store.load());
    CHECK(store.state() == provisioning::AccessStoreState::Erased);
    auto record = initial_record(*identity);
    CHECK(store.initialize(record));
    CHECK(store.sequence() == 1);
    CHECK(store.record()->password == "wspr-0a60df");
    provisioning::AccessStore reloaded(media);
    CHECK(reloaded.load());
    CHECK(*reloaded.record() == record);

    auto replacement = record;
    replacement.password = "field-day-secret";
    replacement.default_password = false;
    ++replacement.epoch;
    for (int fail = 0; fail < 4; ++fail) {
        AccessMemory interrupted = media;
        provisioning::AccessStore attempt(interrupted);
        CHECK(attempt.load());
        interrupted.operation = 0;
        interrupted.fail_at = fail;
        CHECK(!attempt.replace(replacement));
        interrupted.fail_at = -1;
        provisioning::AccessStore recovered(interrupted);
        CHECK(recovered.load());
        CHECK(recovered.record()->password == record.password);
        CHECK(recovered.record()->epoch == 1);
    }
    AccessMemory complete = media;
    provisioning::AccessStore changed(complete);
    CHECK(changed.load());
    CHECK(changed.replace(replacement));
    complete.bytes[provisioning::access_slot_size + provisioning::access_page_size + 4] ^= 1;
    provisioning::AccessStore corrupt(complete);
    CHECK(!corrupt.load());
    CHECK(corrupt.state() == provisioning::AccessStoreState::Fault);

    AccessMemory interrupted_initial;
    interrupted_initial.fail_at = 2;
    provisioning::AccessStore first(interrupted_initial);
    CHECK(first.load());
    CHECK(!first.initialize(record));
    interrupted_initial.fail_at = -1;
    provisioning::AccessStore ambiguous(interrupted_initial);
    CHECK(!ambiguous.load());
    CHECK(ambiguous.state() == provisioning::AccessStoreState::Fault);
    provisioning::scrub(record);
    provisioning::scrub(replacement);
}

void profile_selection() {
    ProfileMemory media;
    provisioning::ProfileStore store(media);
    CHECK(store.load());
    CHECK(store.source() == provisioning::ProfileSource::LegacyBootstrap);
    CHECK(store.select(provisioning::ProfileSource::Unprovisioned));
    provisioning::ProfileStore tombstone(media);
    CHECK(tombstone.load());
    CHECK(tombstone.source() == provisioning::ProfileSource::Unprovisioned);
    CHECK(tombstone.data().empty());
    CHECK(tombstone.select(provisioning::ProfileSource::BuildBundle));
    provisioning::ProfileStore bundle(media);
    CHECK(bundle.load());
    CHECK(bundle.source() == provisioning::ProfileSource::BuildBundle);
    CHECK(!bundle.select(provisioning::ProfileSource::LegacyBootstrap));
    CHECK(!bundle.select(provisioning::ProfileSource::Unprovisioned, "unexpected"));
}

struct AccessFixture {
    AccessMemory media;
    provisioning::AccessStore store{media};
    Bonds bonds;
    Random random;
    provisioning::LocalIdentity identity =
        *provisioning::derive_local_identity(device, "02:11:22:0a:60:df");
    provisioning::LocalAccessController controller{store, bonds, random, std::string(device),
                                                    "boot-a", identity};
    AccessFixture() {
        CHECK(store.load());
        auto record = initial_record(identity);
        CHECK(store.initialize(record));
        provisioning::scrub(record);
    }
};

void access_policy() {
    AccessFixture collision;
    auto first_token =
        collision.controller.softap_login(collision.identity.default_password, 0);
    CHECK(first_token.code == provisioning::AccessCode::Ok);
    collision.random.next = 1;
    CHECK(collision.controller.softap_login(collision.identity.default_password, 1).code ==
          provisioning::AccessCode::Conflict);
    CHECK(collision.controller.live_softap_sessions(1) == 1);

    AccessFixture f;
    auto proof = binding("enroll");
    auto oversized_binding = proof;
    oversized_binding.nonce.assign(65, 'n');
    CHECK(f.controller.prove_password(f.identity.default_password, oversized_binding, 0) ==
          provisioning::AccessCode::Invalid);
    CHECK(f.controller.prove_password("wrong-password", proof, 0) ==
          provisioning::AccessCode::AuthenticationRequired);
    CHECK(f.controller.confirm_local(proof, 0) == provisioning::AccessCode::Ok);
    CHECK(f.controller.open_enrollment(proof, {}, 0) == provisioning::AccessCode::Ok);
    CHECK(f.controller.enrollment_open(119'999));
    CHECK(!f.controller.enrollment_open(120'000));

    proof.nonce = "nonce-b";
    CHECK(f.controller.confirm_local(proof, 200'000) == provisioning::AccessCode::Ok);
    CHECK(f.controller.open_enrollment(proof, {}, 200'000) == provisioning::AccessCode::Ok);
    CHECK(f.controller.ble_connect(1, true, true, std::string(65, 's'), 200'001).code ==
          provisioning::AccessCode::AuthenticationRequired);
    CHECK(f.controller.ble_connect(1, false, true, "gatt-a", 200'001).code ==
          provisioning::AccessCode::AuthenticationRequired);
    auto provisional = f.controller.ble_connect(1, true, true, "gatt-a", 200'001);
    CHECK(provisional.code == provisioning::AccessCode::Ok && provisional.provisional);
    CHECK(f.controller.ble_authorize("wrong-password", 200'002).code ==
          provisioning::AccessCode::AuthenticationRequired);
    CHECK(f.bonds.erased.back() == 1);

    proof.nonce = "nonce-c";
    CHECK(f.controller.confirm_local(proof, 330'000) == provisioning::AccessCode::Ok);
    CHECK(f.controller.open_enrollment(proof, {}, 330'000) == provisioning::AccessCode::Ok);
    CHECK(f.controller.ble_connect(2, true, true, "gatt-b", 330'001).code ==
          provisioning::AccessCode::Ok);
    auto promoted = f.controller.ble_authorize(f.identity.default_password, 330'002);
    CHECK(promoted.code == provisioning::AccessCode::Ok);
    CHECK(!promoted.principal.empty());
    CHECK(f.store.record()->bond_count == 1);
    CHECK(f.controller.ble_authorization().authenticated);
    CHECK(!f.controller.ble_disconnect());
    CHECK(f.controller.ble_connect(2, true, false, "gatt-return", 500'000).code ==
          provisioning::AccessCode::Ok);
    CHECK(f.controller.ble_authorization().principal == promoted.principal);
    f.controller.ble_disconnect();

    std::array<std::string, provisioning::softap_session_capacity> tokens;
    for (auto& token : tokens) {
        auto login = f.controller.softap_login(f.identity.default_password, 600'000);
        CHECK(login.code == provisioning::AccessCode::Ok);
        token = login.token;
        CHECK(provisioning::LocalAccessController::cookie_header(token) ==
              "__Host-wsprrypico=" + token +
                  "; Path=/; Secure; HttpOnly; SameSite=Strict");
    }
    CHECK(f.controller.softap_login(f.identity.default_password, 600'000).code ==
          provisioning::AccessCode::Capacity);
    CHECK(f.controller.bind_softap_session(tokens[0], std::string(65, 's'), 600'001) ==
          provisioning::AccessCode::Invalid);
    CHECK(f.controller.bind_softap_session(tokens[0], "wtp-a", 600'001) ==
          provisioning::AccessCode::Ok);
    CHECK(f.controller.bind_softap_session(tokens[0], "wtp-b", 600'002) ==
          provisioning::AccessCode::Conflict);
    auto ordinary = f.controller.softap_authorize(tokens[0], provisioning::SoftApOperation::Status,
                                                   "wtp-a", {}, 600'003);
    CHECK(ordinary.code == provisioning::AccessCode::Ok && !ordinary.owner_only_grace);
    CHECK(f.controller.softap_authorize(tokens[1], provisioning::SoftApOperation::Status, "", {},
                                        600'000 + provisioning::softap_inactivity_ms)
              .code == provisioning::AccessCode::Expired);

    AccessFixture grace;
    auto login = grace.controller.softap_login(grace.identity.default_password, 0);
    CHECK(login.code == provisioning::AccessCode::Ok);
    CHECK(grace.controller.bind_softap_session(login.token, "owned", 1) ==
          provisioning::AccessCode::Ok);
    provisioning::Activity running{.owned = true, .armed = true};
    auto owner = grace.controller.softap_authorize(
        login.token, provisioning::SoftApOperation::Status, "owned", running,
        provisioning::softap_absolute_ms);
    CHECK(owner.code == provisioning::AccessCode::Ok && owner.owner_only_grace);
    CHECK(grace.controller
              .softap_authorize(login.token, provisioning::SoftApOperation::Load, "owned", running,
                                provisioning::softap_absolute_ms + 1)
              .code == provisioning::AccessCode::Expired);

    auto change = binding("password-change");
    CHECK(f.controller.prove_password(f.identity.default_password, change, 700'000) ==
          provisioning::AccessCode::Ok);
    CHECK(f.controller.change_password("replacement-pass", change, {}, 700'001) ==
          provisioning::AccessCode::ConfirmationRequired);
    change.nonce = "change-two";
    CHECK(f.controller.prove_password(f.identity.default_password, change, 700'010) ==
          provisioning::AccessCode::Ok);
    CHECK(f.controller.confirm_local(change, 700'011) == provisioning::AccessCode::Ok);
    CHECK(f.controller.change_password("replacement-pass", change, {}, 700'012) ==
          provisioning::AccessCode::Ok);
    CHECK(f.store.record()->epoch == 2);
    CHECK(!f.store.record()->default_password);
    CHECK(f.store.record()->bond_count == 0);
    CHECK(f.controller.live_softap_sessions(700'013) == 0);
    CHECK(f.bonds.all == 1);
    auto field_mode = binding("field-mode");
    CHECK(f.controller.prove_password("replacement-pass", field_mode, 700'020) ==
          provisioning::AccessCode::Ok);
    provisioning::Activity busy{.owned = true};
    CHECK(f.controller.set_field_mode(true, field_mode, busy, 700'021) ==
          provisioning::AccessCode::Busy);
    CHECK(f.controller.set_field_mode(true, field_mode, {}, 700'022) ==
          provisioning::AccessCode::Ok);
    CHECK(f.store.record()->field_mode);

    auto custom_enroll = binding("custom-enroll");
    CHECK(f.controller.confirm_local(custom_enroll, 800000) == provisioning::AccessCode::Ok);
    CHECK(f.controller.open_enrollment(custom_enroll, {}, 800001) ==
          provisioning::AccessCode::Ok);

    AccessFixture protected_owner;
    auto protected_login = protected_owner.controller.softap_login(
        protected_owner.identity.default_password, 0);
    CHECK(protected_login.code == provisioning::AccessCode::Ok);
    CHECK(protected_owner.controller.softap_login(
              protected_owner.identity.default_password,
              provisioning::softap_absolute_ms,
              protected_login.principal)
              .code == provisioning::AccessCode::Ok);
    CHECK(protected_owner.controller.live_softap_sessions(
              provisioning::softap_absolute_ms, protected_login.principal) == 2);
}

provisioning::Activity idle_activity(void*) {
    return {};
}

std::uint64_t fixture_monotonic(void* context) {
    return *static_cast<std::uint64_t*>(context);
}

void ble_command_policy() {
    AccessFixture f;
    auto enroll = binding("ble-enroll");
    CHECK(f.controller.confirm_local(enroll, 0) == provisioning::AccessCode::Ok);
    CHECK(f.controller.open_enrollment(enroll, {}, 0) == provisioning::AccessCode::Ok);
    ProfileMemory profile_media;
    provisioning::ProfileStore profile_store(profile_media);
    CHECK(profile_store.load());
    RejectingValidator validator;
    provisioning::Manager manager(profile_store, validator, std::string(device));
    provisioning::CommandAdapter command(manager, std::string(device),
                                          provisioning::Transport::Ble);
    std::uint64_t now_ns = 1'000'000'000ULL;
    time::DisciplineConfig time_config;
    time_config.synchronized_for_ns = 90'000'000'000ULL;
    time_config.holdover_for_ns = 180'000'000'000ULL;
    time_config.max_observation_age_ns = 90'000'000'000ULL;
    time_config.max_uncertainty_ns = time::standalone_max_uncertainty_ns;
    time::UtcDiscipline discipline(fixture_monotonic, &now_ns, time_config);
    time::ControllerTimeArbiter arbiter(discipline, fixture_monotonic, &now_ns,
                                        std::string(device));
    Led led;
    provisioning::IndicatorController indicator(led, std::string(device));
    provisioning::BleCommandSession session(f.controller, command, manager,
                                             std::string(device), idle_activity, nullptr);
    session.field_controls(&arbiter, &indicator);
    CHECK(session.connected(9, true, true, "link-a", 1));
    const std::string open =
        "{\"version\":1,\"operation\":\"open\","
        "\"request_id\":\"11111111111111111111111111111111\","
        "\"session_id\":\"22222222222222222222222222222222\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\"}";
    CHECK(session.handle(open, 2).code == provisioning::Code::AuthenticationRequired);
    const std::string unauthorized_identify =
        "{\"version\":1,\"operation\":\"identify\","
        "\"request_id\":\"55555555555555555555555555555555\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\"}";
    CHECK(session.handle(unauthorized_identify, 2).code ==
          provisioning::Code::AuthenticationRequired);
    const std::string authorize =
        "{\"version\":1,\"operation\":\"authorize\","
        "\"request_id\":\"33333333333333333333333333333333\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\","
        "\"password\":\"wspr-0a60df\"}";
    const auto admitted = session.handle(authorize, 3);
    CHECK(admitted.code == provisioning::Code::Ok);
    session.response_delivered(3);
    CHECK(session.authorized());
    CHECK(!session.principal().empty());
    const std::string identify =
        "{\"version\":1,\"operation\":\"identify\","
        "\"request_id\":\"66666666666666666666666666666666\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\"}";
    CHECK(session.handle(identify, 4).code == provisioning::Code::Ok);
    auto wrong_field_session = identify;
    wrong_field_session.replace(
        wrong_field_session.find("44444444444444444444444444444444"), 32,
        "44444444444444444444444444444445");
    wrong_field_session.replace(
        wrong_field_session.find("66666666666666666666666666666666"), 32,
        "66666666666666666666666666666667");
    CHECK(session.handle(wrong_field_session, 4).code ==
          provisioning::Code::AuthenticationRequired);
    indicator.poll(4);
    CHECK(indicator.status(4).pattern == provisioning::IndicatorPattern::Identify);
    const std::string challenge =
        "{\"version\":1,\"operation\":\"time_challenge\","
        "\"request_id\":\"88888888888888888888888888888888\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\","
        "\"nonce\":\"phone-sample-1\"}";
    CHECK(session.handle(challenge, 5).code == provisioning::Code::Ok);
    // Starting the final response indication, not command receipt, starts the
    // conservative latency charged to the controller-time uncertainty budget.
    now_ns += 400'000'000ULL;
    session.response_started(5);
    now_ns += 10'000'000ULL;
    const std::string submit =
        "{\"version\":1,\"operation\":\"time_submit\","
        "\"request_id\":\"99999999999999999999999999999999\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\","
        "\"nonce\":\"phone-sample-1\","
        "\"utc_ns\":\"1800000000000000000\"}";
    CHECK(session.handle(submit, 6).code == provisioning::Code::Ok);
    session.response_delivered(6);
    const std::string field_status =
        "{\"version\":1,\"operation\":\"field_status\","
        "\"request_id\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\","
        "\"session_id\":\"44444444444444444444444444444444\","
        "\"device_id\":\"00112233445566778899aabbccddeeff\"}";
    const auto field = session.handle(field_status, 7);
    CHECK(field.code == provisioning::Code::Ok);
    CHECK(field.notification.find("\"time_source\":\"controller\"") != std::string::npos);
    CHECK(field.notification.size() <= provisioning::max_notification_bytes);
    CHECK(session.handle(open, 4).code == provisioning::Code::Replay);
    auto admitted_open = open;
    admitted_open.replace(admitted_open.find("11111111111111111111111111111111"), 32,
                          "55555555555555555555555555555555");
    CHECK(session.handle(admitted_open, 5).code == provisioning::Code::Ok);
    session.disconnected();
    CHECK(!session.authorized());
    CHECK(f.store.record()->bond_count == 1);

    provisioning::BleCommandSession returning(f.controller, command, manager,
                                               std::string(device), idle_activity, nullptr);
    returning.field_controls(&arbiter, &indicator);
    CHECK(returning.connected(9, true, false, "link-return", 6));
    CHECK(returning.authorized());
    auto retained_authorize = authorize;
    retained_authorize.replace(retained_authorize.find("wspr-0a60df"), 11,
                               "wrong-value");
    CHECK(returning.handle(retained_authorize, 7).code == provisioning::Code::Ok);
    CHECK(returning.authorized());
    auto abandoned_challenge = challenge;
    abandoned_challenge.replace(
        abandoned_challenge.find("88888888888888888888888888888888"), 32,
        "88888888888888888888888888888889");
    abandoned_challenge.replace(abandoned_challenge.find("phone-sample-1"), 14,
                                "disconnect-one");
    CHECK(returning.handle(abandoned_challenge, 8).code == provisioning::Code::Ok);
    returning.response_started(8);
    returning.disconnected();

    provisioning::BleCommandSession after_disconnect(
        f.controller, command, manager, std::string(device), idle_activity, nullptr);
    after_disconnect.field_controls(&arbiter, &indicator);
    CHECK(after_disconnect.connected(9, true, false, "link-after-disconnect", 9));
    CHECK(after_disconnect.handle(retained_authorize, 10).code == provisioning::Code::Ok);
    auto next_challenge = abandoned_challenge;
    next_challenge.replace(next_challenge.find("88888888888888888888888888888889"), 32,
                           "8888888888888888888888888888888a");
    next_challenge.replace(next_challenge.find("disconnect-one"), 14, "disconnect-two");
    CHECK(after_disconnect.handle(next_challenge, 11).code == provisioning::Code::Ok);
    after_disconnect.disconnected();
}

void framing_policy() {
    std::vector<std::uint8_t> message(provisioning::gatt_frame_payload_bytes * 3 + 1);
    for (std::size_t i = 0; i < message.size(); ++i)
        message[i] = static_cast<std::uint8_t>(i);
    const auto frames = provisioning::gatt_frames(message);
    CHECK(frames.size() == 4);
    provisioning::GattFrameReceiver receiver(message.size());
    for (std::size_t i = 0; i < frames.size(); ++i)
        CHECK(receiver.receive(frames[i]) ==
              (i + 1 == frames.size() ? provisioning::FrameResult::Complete
                                      : provisioning::FrameResult::Pending));
    CHECK(std::equal(receiver.message().begin(), receiver.message().end(), message.begin()));
    receiver.reset();
    CHECK(receiver.message().empty());
    CHECK(receiver.receive(frames[1]) == provisioning::FrameResult::OutOfOrder);
    CHECK(receiver.receive(frames[0]) == provisioning::FrameResult::Pending);
    CHECK(receiver.receive(frames[0]) == provisioning::FrameResult::OutOfOrder);
    provisioning::GattFrameReceiver bounded(10);
    CHECK(bounded.receive(frames[0]) == provisioning::FrameResult::Oversize);
    auto malformed = frames[0];
    malformed[3] = 1;
    CHECK(receiver.receive(malformed) == provisioning::FrameResult::Invalid);
    CHECK(provisioning::gatt_frames({}).empty());
    std::vector<std::uint8_t> oversized(
        provisioning::gatt_frame_payload_bytes * provisioning::gatt_frame_count + 1);
    CHECK(provisioning::gatt_frames(oversized).empty());
}

void softap_http_policy() {
    AccessFixture f;
    provisioning::SoftApHttpAdmission admission(
        f.controller, std::string(device), f.identity.hostname);
    network::HttpRequest login;
    login.method = "POST";
    login.path = "/local/v1/login";
    login.body =
        "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
        "\"password\":\"wspr-0a60df\"}";
    login.headers = {{"host", f.identity.hostname},
                     {"origin", "https://" + f.identity.hostname},
                     {"content-type", "application/json"},
                     {"x-wsprrypico-request", "1"},
                     {"sec-fetch-site", "same-origin"}};

    CHECK(admission.login(login, provisioning::SoftApSurface::BlankReadOnly, "", 0).response.status ==
          401);
    auto wrong_origin = login;
    wrong_origin.headers["origin"] = "https://attacker.local";
    CHECK(admission.login(wrong_origin, provisioning::SoftApSurface::Normal, "", 0).response.status ==
          400);
    auto response =
        admission.login(login, provisioning::SoftApSurface::ProvisionedPreClock, "", 1);
    CHECK(response.response.status == 200);
    CHECK(response.set_cookie.starts_with("__Host-wsprrypico="));
    CHECK(response.set_cookie.ends_with("; Path=/; Secure; HttpOnly; SameSite=Strict"));
    CHECK(response.wire_headers().find("Set-Cookie: " + response.set_cookie + "\r\n") !=
          std::string::npos);

    const auto separator = response.set_cookie.find(';');
    network::HttpRequest request;
    request.method = "GET";
    request.path = "/api/v1/status";
    request.headers = {{"host", f.identity.hostname},
                       {"cookie", response.set_cookie.substr(0, separator)},
                       {"sec-fetch-site", "same-origin"}};
    const auto status = admission.authorize(
        request, provisioning::SoftApSurface::ProvisionedPreClock,
        provisioning::SoftApOperation::Status, "softap-session", {}, 2);
    CHECK(status.code == provisioning::AccessCode::Ok);
    CHECK(status.authorization.authenticated && status.authorization.confidential &&
          status.authorization.local && !status.authorization.principal.empty());
    CHECK(admission.authorize(
              request, provisioning::SoftApSurface::ProvisionedPreClock,
              provisioning::SoftApOperation::Status, "different-session", {}, 2)
              .code == provisioning::AccessCode::Conflict);
    CHECK(admission.authorize(
              request, provisioning::SoftApSurface::ProvisionedPreClock,
              provisioning::SoftApOperation::Load, "softap-session", {}, 3)
              .code == provisioning::AccessCode::AuthenticationRequired);

    auto ambiguous = request;
    ambiguous.headers["cookie"] += "; another=value";
    CHECK(admission.authorize(ambiguous, provisioning::SoftApSurface::Normal,
                              provisioning::SoftApOperation::Status,
                              "softap-session", {}, 4)
              .code == provisioning::AccessCode::AuthenticationRequired);

    network::HttpRequest logout = request;
    logout.method = "POST";
    logout.path = "/local/v1/logout";
    logout.body = "{}";
    logout.headers["origin"] = "https://" + f.identity.hostname;
    logout.headers["content-type"] = "application/json";
    logout.headers["x-wsprrypico-request"] = "1";
    CHECK(admission.logout(logout, provisioning::SoftApSurface::Normal,
                           "softap-session", {}, 5) == provisioning::AccessCode::Ok);
    CHECK(admission.authorize(request, provisioning::SoftApSurface::Normal,
                              provisioning::SoftApOperation::Status,
                              "softap-session", {}, 6)
              .code == provisioning::AccessCode::Expired);

    provisioning::SoftApHttpResponse injected;
    injected.set_cookie = "safe=value\r\nX-Injected: true";
    CHECK(injected.wire_headers().find("X-Injected") == std::string::npos);
}

void runtime_policy() {
    AccessMemory media;
    provisioning::AccessStore store(media);
    CHECK(store.load());
    const auto identity = *provisioning::derive_local_identity(device, "02:11:22:0a:60:df");
    auto record = initial_record(identity);
    CHECK(store.initialize(record));
    provisioning::scrub(record);
    provisioning::SoftApCoordinator ap(store);
    ap.station(false, 0);
    CHECK(!ap.poll(provisioning::softap_fallback_ms - 1));
    CHECK(ap.poll(provisioning::softap_fallback_ms));
    ap.ready(true);
    CHECK(ap.status(provisioning::softap_fallback_ms).ready);
    ap.station(true, provisioning::softap_fallback_ms + 1);
    CHECK(ap.poll(provisioning::softap_fallback_ms +
                  provisioning::softap_station_stable_ms));
    CHECK(!ap.poll(provisioning::softap_fallback_ms +
                   provisioning::softap_station_stable_ms + 1));
    CHECK(ap.request_join_grace(100'000));
    CHECK(!ap.request_join_grace(100'001));
    CHECK(ap.poll(100'001));
    ap.no_profile(true);
    CHECK(ap.surface(false) == provisioning::SoftApSurface::BlankReadOnly);
    ap.no_profile(false);
    CHECK(ap.surface(false) == provisioning::SoftApSurface::ProvisionedPreClock);
    CHECK(ap.surface(true) == provisioning::SoftApSurface::Normal);

    Led led;
    provisioning::IndicatorController indicator(led, std::string(device));
    CHECK(indicator.identify("identify-a", device, false, true, 0) ==
          provisioning::IndicatorCode::AuthenticationRequired);
    CHECK(indicator.identify("identify-a", "wrong", true, true, 0) ==
          provisioning::IndicatorCode::Invalid);
    indicator.softap_ready(true);
    indicator.poll(0);
    CHECK(led.writes.back());
    indicator.poll(200);
    CHECK(!led.writes.back());
    CHECK(indicator.identify("identify-a", device, true, true, 1'000) ==
          provisioning::IndicatorCode::Ok);
    CHECK(indicator.identify("identify-a", device, true, true, 1'100) ==
          provisioning::IndicatorCode::Ok);
    CHECK(indicator.identify("identify-b", device, true, true, 1'100) ==
          provisioning::IndicatorCode::Busy);
    indicator.poll(1'000);
    CHECK(led.writes.back());
    indicator.poll(1'150);
    CHECK(!led.writes.back());
    indicator.poll(1'300);
    CHECK(led.writes.back());
    indicator.poll(11'000);
    CHECK(indicator.status(11'000).pattern == provisioning::IndicatorPattern::SoftApReady);
    CHECK(indicator.identify("identify-a", device, true, true, 11001) ==
          provisioning::IndicatorCode::Ok);
    CHECK(indicator.status(11001).pattern == provisioning::IndicatorPattern::SoftApReady);
}

void reset_policy() {
    const auto identity = *provisioning::derive_local_identity(device, "02:11:22:0a:60:df");
    AccessMemory access_media;
    provisioning::AccessStore access(access_media);
    CHECK(access.load());
    auto access_record = initial_record(identity);
    CHECK(access.initialize(access_record));
    access_record.bonds[0] = 7;
    access_record.bond_count = 1;
    CHECK(access.replace(access_record));
    provisioning::scrub(access_record);
    ProfileMemory profile_media;
    provisioning::ProfileStore profiles(profile_media);
    CHECK(profiles.load());
    const std::string legacy = "legacy-profile";
    CHECK(profiles.replace(legacy));
    ResetFixture targets;
    const auto preserved = targets.operational;
    provisioning::ResetCoordinator reset(access, profiles, targets, identity);
    const std::string request = "reset-request";
    const auto digest = wtp::sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(request.data()), request.size()));
    CHECK(reset.begin(provisioning::ResetLevel::Provisioning,
                      provisioning::ProfileSource::Unprovisioned, digest) ==
          provisioning::ResetResult::Pending);
    targets.bond_result = false;
    CHECK(reset.resume() == provisioning::ResetResult::TargetFault);
    CHECK(reset.pending());
    CHECK(access.record()->ble_disabled);
    CHECK(profiles.source() == provisioning::ProfileSource::Unprovisioned);
    CHECK(targets.operational == preserved);
    targets.bond_result = true;
    CHECK(reset.resume() == provisioning::ResetResult::Complete);
    CHECK(!reset.pending());
    CHECK(access.record()->epoch == 2);
    CHECK(access.record()->default_password);
    CHECK(access.record()->field_mode);
    CHECK(access.record()->bond_count == 0);
    CHECK(!access.record()->ble_disabled);
    CHECK(targets.operational == preserved);

    const std::string full_request = "full-reset-request";
    const auto full_digest = wtp::sha256(std::span(
        reinterpret_cast<const std::uint8_t*>(full_request.data()), full_request.size()));
    targets.bond_done = false;
    CHECK(reset.begin(provisioning::ResetLevel::Full,
                      provisioning::ProfileSource::Unprovisioned, full_digest) ==
          provisioning::ResetResult::Pending);
    CHECK(reset.resume() == provisioning::ResetResult::Complete);
    CHECK(targets.operational_erased());
    CHECK(!access.record()->field_mode);
}

std::uint64_t clock_now = 0;
std::uint64_t monotonic(void*) {
    return clock_now;
}

void controller_time_policy() {
    time::DisciplineConfig config;
    config.synchronized_for_ns = 90'000'000'000ULL;
    config.holdover_for_ns = 180'000'000'000ULL;
    config.max_observation_age_ns = 90'000'000'000ULL;
    config.max_uncertainty_ns = time::standalone_max_uncertainty_ns;
    time::UtcDiscipline discipline(monotonic, nullptr, config);
    time::ControllerTimeArbiter arbiter(discipline, monotonic, nullptr, std::string(device));
    constexpr std::uint64_t utc = 1'800'000'000'000'000'000ULL;
    clock_now = 1'000'000'000ULL;
    CHECK(arbiter.challenge(std::string(65, 'p'), "session-a", device, "nonce-a").code ==
          time::ControllerTimeCode::AuthenticationRequired);
    CHECK(arbiter.challenge("phone-a", std::string(65, 's'), device, "nonce-a").code ==
          time::ControllerTimeCode::AuthenticationRequired);
    CHECK(arbiter.challenge("phone-a", "session-a", device, std::string(65, 'n')).code ==
          time::ControllerTimeCode::AuthenticationRequired);
    auto challenge = arbiter.challenge("phone-a", "session-a", device, "nonce-a");
    CHECK(challenge.code == time::ControllerTimeCode::Ok);
    clock_now += 400'000'000ULL;
    CHECK(!arbiter.challenge_response_started("phone-b", "session-a", device, "nonce-a"));
    CHECK(arbiter.challenge_response_started("phone-a", "session-a", device, "nonce-a"));
    clock_now += 10'000'000ULL;
    CHECK(arbiter.submit("phone-a", "session-a", device, "nonce-a", utc) ==
          time::ControllerTimeCode::Ok);
    CHECK(arbiter.status().source == time::ActiveTimeSource::Controller);
    CHECK(arbiter.challenge("phone-a", "cancel-a", device, "cancel-nonce").code ==
          time::ControllerTimeCode::Ok);
    arbiter.cancel_challenge("phone-b", "cancel-a");
    CHECK(arbiter.challenge("phone-a", "blocked", device, "blocked-nonce").code ==
          time::ControllerTimeCode::SourceBusy);
    arbiter.cancel_challenge("phone-a", "cancel-a");
    CHECK(arbiter.challenge("phone-b", "session-b", device, "nonce-b").code ==
          time::ControllerTimeCode::Ok);
    clock_now += 10'000'000ULL;
    CHECK(arbiter.submit("phone-b", "session-b", device, "nonce-b", utc + 10'000'000ULL) ==
          time::ControllerTimeCode::SourceBusy);

    const auto sample = clock_now;
    CHECK(arbiter.observe(time::ObservationSource::Sntp, utc + 10'000'000ULL, sample,
                          10'000'000ULL, wtp::LeapState::Normal));
    CHECK(arbiter.status().source == time::ActiveTimeSource::Sntp);
    CHECK(arbiter.challenge("phone-a", "session-a", device, "nonce-c").code ==
          time::ControllerTimeCode::Ok);
    clock_now += 1'000'000ULL;
    CHECK(arbiter.submit("phone-a", "session-a", device, "nonce-c", utc) ==
          time::ControllerTimeCode::SourceBusy);

    clock_now += 91'000'000'000ULL;
    CHECK(arbiter.challenge("phone-a", "session-a", device, "nonce-d").code ==
          time::ControllerTimeCode::Ok);
    clock_now += 1'000'000ULL;
    CHECK(arbiter.submit("phone-a", "session-a", device, "nonce-d",
                         utc + 91'001'000'000ULL) == time::ControllerTimeCode::Ok);
    CHECK(arbiter.challenge("phone-a", "session-a", device, "nonce-e").code ==
          time::ControllerTimeCode::Ok);
    clock_now += 1'000'000ULL;
    CHECK(arbiter.submit("phone-a", "session-a", device, "nonce-e",
                         utc + 120'000'000'000ULL) ==
          time::ControllerTimeCode::Disagreement);
    CHECK(arbiter.status().disagreement);
    for (unsigned i = 0; i < 2; ++i) {
        const auto nonce = "recover-" + std::to_string(i);
        CHECK(arbiter.challenge("phone-a", "session-a", device, nonce).code ==
              time::ControllerTimeCode::Ok);
        clock_now += 1'000'000ULL;
        const auto result = arbiter.submit("phone-a", "session-a", device, nonce,
                                           utc + 120'000'000'000ULL + i * 1'000'000ULL);
        CHECK(result == (i ? time::ControllerTimeCode::Ok
                           : time::ControllerTimeCode::Disagreement));
    }
    CHECK(arbiter.status().source == time::ActiveTimeSource::Controller);
    arbiter.invalidate(time::ObservationSource::Sntp);
    CHECK(arbiter.status().source == time::ActiveTimeSource::Controller);
    clock_now += time::controller_source_lifetime_ns + 1;
    CHECK(arbiter.status().source == time::ActiveTimeSource::None);
}
} // namespace

int main() {
    identity_and_journal();
    profile_selection();
    access_policy();
    ble_command_policy();
    framing_policy();
    softap_http_policy();
    runtime_policy();
    reset_policy();
    controller_time_policy();
    std::cout << "field access tests passed\n";
}
