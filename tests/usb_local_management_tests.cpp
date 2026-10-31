#include "application/resources.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"

using namespace wsprrypico;
using namespace network_test;
namespace {
constexpr auto device = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
struct Media : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> data{};
    unsigned writes = 0, fail_at = 0;
    Media() {
        data.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> bytes) override {
        if (at > data.size() || bytes.size() > data.size() - at)
            return false;
        std::copy_n(data.begin() + at, bytes.size(), bytes.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        if (at > data.size() - provisioning::profile_slot_size)
            return false;
        std::fill_n(data.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> bytes) override {
        if (++writes == fail_at)
            return false;
        if (at > data.size() || bytes.size() > data.size() - at)
            return false;
        for (std::size_t i = 0; i < bytes.size(); ++i)
            data[at + i] &= bytes[i];
        return true;
    }
};
struct Platform : provisioning::ConsumerClaimCommitPlatform {
    bool safe_to_commit() override {
        return false;
    } // USB authority is independent.
    std::uint64_t monotonic_now_ms() override {
        return 100;
    }
    bool station_ready(std::string_view) override {
        return false;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return {};
    }
    std::string_view local_hostname() override {
        return "default.local";
    }
    bool valid_owner_point(std::string_view) override {
        return false;
    }
    bool generate_tls(std::string_view, std::string_view, std::uint64_t,
                      provisioning::ConsumerTls&) override {
        return false;
    }
    bool valid_tls(const provisioning::ConsumerTls&, std::string_view, std::uint64_t) override {
        return false;
    }
};
struct Test {
    Fixture f;
    Flash draft_flash;
    standalone::Progress progress{draft_flash};
    Media media;
    provisioning::ProfileStore profiles{media};
    provisioning::RuntimeProfile runtime;
    Platform platform;
    provisioning::HostnameSettings hostname{profiles, runtime,         platform,
                                            device,   "default.local", "default.local"};
    provisioning::LocalSettings settings{profiles, runtime, f.store,
                                         progress, device,  "default.local"};
    network::LocalUsbApi usb{f.api};
    Test() {
        REQUIRE(progress.load());
        REQUIRE(profiles.load());
        REQUIRE(runtime.load(profiles, device, provisioning::BuildBundleState::Absent));
        f.api.consumer_config(runtime);
        f.api.hostname_settings(hostname);
        f.api.progress_settings(progress);
        f.api.local_usb_settings(settings);
    }
    std::string envelope(std::string_view schema, std::string_view field, std::string_view value) {
        return "{\"schema\":" + wtp::json::quote(schema) +
               ",\"target\":" + application::target(device, f.service.status().boot_id) + ',' +
               wtp::json::quote(field) + ':' + std::string(value) + '}';
    }
    network::HttpResponse request(std::string method, std::string path, std::string body = {},
                                  std::string rev = "current") {
        network::HttpRequest r;
        r.method = std::move(method);
        r.path = std::move(path);
        r.body = std::move(body);
        if (!rev.empty())
            r.headers["if-match"] = rev == "current" ? f.api.revision() : rev;
        return usb.handle(network_test::control_request(r), 100);
    }
    network::HttpResponse wifi(std::string_view json) {
        return request(json == "null" ? "DELETE" : "PUT", "/api/usb/v1/wifi",
                       envelope("wifi", "wifi", json));
    }
};
constexpr auto network1 =
    R"({"ssid":"test-network","password":"test-password","time_server":"192.0.2.1"})";
constexpr auto network2 =
    R"({"ssid":"new-network","password":"new-password","time_server":"pool.ntp.org"})";
void blank_usb_workflow() {
    Test t;
    auto hostname = t.request("GET", "/api/control/v1/hostname");
    REQUIRE(hostname.status == 200 &&
            hostname.body_text().find("\"writable\":true") != hostname.body_text().npos);
    auto response = t.request("PUT", "/api/control/v1/hostname",
                              t.envelope("hostname", "hostname", "\"bad\""));
    REQUIRE(response.status == 400 && t.profiles.sequence() == 0);
    REQUIRE(t.request("PUT", "/api/control/v1/hostname",
                      t.envelope("hostname", "hostname", "\"usb-pico.local\""))
                .status == 200);
    REQUIRE(t.runtime.consumer_profile()->usb_managed &&
            t.runtime.consumer_profile()->ssid.empty());
    REQUIRE(t.runtime.consumer_profile()->callsign.empty());
    const auto blank_app = t.request("GET", "/api/control/v1/application");
    REQUIRE(blank_app.status == 200);
    const auto blank_json = wtp::json::parse(blank_app.body_view());
    REQUIRE(blank_json && blank_json->get("station")->get("station")->raw == "null");
    REQUIRE(!blank_json->get("capabilities")->get("management_carrier"));
    REQUIRE(std::string(blank_json->get("capabilities")->get("unavailable")->raw)
                .find("usb_json_management") == std::string::npos);
    const auto usb_caps = t.request("GET", "/api/control/v1/capabilities");
    const auto usb_caps_json = wtp::json::parse(usb_caps.body_view());
    REQUIRE(usb_caps_json &&
            !usb_caps_json->get("application_resources")->get("management_carrier"));
    const auto management = t.request("GET", "/api/control/v1/management");
    const auto management_json = wtp::json::parse(management.body_view());
    REQUIRE(management_json && usb_caps_json->get("management_carriers")->get("schema")->string() ==
                                   management_json->get("schema")->string());
    REQUIRE(management_json->get("limits")->get("idle_ms")->raw == "1800000");
    REQUIRE(management_json->get("limits")->get("absolute_ms")->raw == "28800000");
    REQUIRE(application::capabilities().find("management_carrier") == std::string::npos);
    REQUIRE(application::capabilities().find("usb_json_management") == std::string::npos);
    REQUIRE(blank_json->get("station")->get("saved_generation")->raw == "null");
    REQUIRE(blank_json->get("hardware")->get("saved")->raw == "null");
    REQUIRE(blank_json->get("wspr_plan")->raw == "null");
    auto no_wifi = *standalone::parse_config(config);
    no_wifi.ssid.clear();
    no_wifi.password.clear();
    no_wifi.ntp_ipv4 = standalone::default_time_server;
    response = t.request("POST", "/api/control/v1/config/update", network_test::configuration_update(standalone::serialize_config(no_wifi)));
    if (response.status != 200)
        std::cerr << response.status << " " << response.body_text() << "\n";
    REQUIRE(response.status == 200);
    REQUIRE(t.f.store.config() && t.f.store.config()->ssid.empty());
    REQUIRE(t.runtime.consumer_profile()->callsign.empty());
    REQUIRE(t.runtime.overlay(*t.f.store.config())->callsign == "AA0NT");
    REQUIRE(t.request("GET", "/api/control/v1/config").body_text().find("\"password\":null") !=
            std::string::npos);
    REQUIRE(t.request("GET", "/api/control/v1/management").body_text().find("management") !=
            std::string::npos);
    REQUIRE(t.wifi(network1).status == 200);
    const auto first = t.f.api.revision();
    REQUIRE(t.request("PUT", "/api/usb/v1/wifi", t.envelope("wifi", "wifi", network2),
                      "stale")
                .status == 412);
    REQUIRE(
        t.wifi(R"({"ssid":"new-network","password":null,"time_server":"pool.ntp.org"})").status ==
        400);
    REQUIRE(
        t.wifi(R"({"ssid":"test-network","password":null,"time_server":"pool.ntp.org"})").status ==
        200);
    REQUIRE(t.runtime.consumer_profile()->password == "test-password");
    REQUIRE(t.f.api.revision() != first);
    REQUIRE(t.wifi(network2).status == 200);
    REQUIRE(t.wifi("null").status == 200);
    REQUIRE(t.f.store.config()->ssid.empty() && t.runtime.consumer_profile()->ssid.empty());
    REQUIRE(t.request("GET", "/api/usb/v1/wifi").body_text().find("\"wifi\":null") != std::string::npos);
    const auto fields = t.progress.fields(false);
    REQUIRE(fields.find("test-password") == std::string::npos &&
            fields.find("new-password") == std::string::npos);
    const auto candidate = t.progress.candidate(t.f.store.config());
    REQUIRE(candidate && candidate->ssid.empty() && candidate->password.empty());
    provisioning::ProfileStore cold(t.media);
    provisioning::RuntimeProfile cold_runtime;
    REQUIRE(cold.load() && cold_runtime.load(cold, device, provisioning::BuildBundleState::Absent));
    REQUIRE(cold_runtime.consumer_profile()->ssid.empty());
    REQUIRE(cold_runtime.consumer_profile()->tls.hostname == "usb-pico.local");
    REQUIRE(t.wifi(network1).status == 200);
    REQUIRE(t.runtime.consumer_profile()->ssid == "test-network");
}
void preserves_state_and_network_policy() {
    Test t;
    REQUIRE(t.f.scheduler.command("CONFIG " + config).find("true") != std::string::npos);
    REQUIRE(t.f.store.reserve(1'800'000'000'000'000'000ULL));
    REQUIRE(t.f.scheduler.command("STOP").find("true") != std::string::npos);
    const auto previous = *t.f.store.config();
    const auto watermark = t.f.store.watermark();
    REQUIRE(t.wifi(network1).status == 200);
    REQUIRE(t.f.scheduler.reboot_required());
    REQUIRE(t.wifi("null").status == 200);
    REQUIRE(t.f.scheduler.reboot_required());
    const auto shared_app = t.request("GET", "/api/control/v1/application");
    const auto app_json = wtp::json::parse(shared_app.body_view());
    REQUIRE(app_json && app_json->get("reboot_required")->raw == "true");
    const auto shared_status = t.request("GET", "/api/control/v1/status");
    const auto status_json = wtp::json::parse(shared_status.body_view());
    REQUIRE(status_json && status_json->get("standalone")->get("reboot_required")->raw == "true");
    REQUIRE(t.request("POST", "/api/control/v1/config/update", network_test::configuration_update(standalone::serialize_config(*t.f.store.config())))
                .status == 200);
    REQUIRE(t.f.scheduler.reboot_required()); // Config save cannot erase the profile latch.
    const auto& after = *t.f.store.config();
    REQUIRE(after.schedules == previous.schedules && after.pins == previous.pins);
    REQUIRE(after.callsign == previous.callsign && after.locator == previous.locator);
    REQUIRE(t.f.store.watermark() == watermark);
    REQUIRE(t.f.scheduler.status().find("\"suspended\":true") != std::string::npos);
    auto r = network::HttpRequest{};
    r.method = "GET";
    r.path = "/api/usb/v1/wifi";
    REQUIRE(t.f.api.handle(network_test::control_request(r), "network", "127.0.0.1").status == 403);
    r.headers["host"] = "127.0.0.1";
    REQUIRE(t.f.api.handle(network_test::control_request(r), "network", "127.0.0.1").status == 404);
    const auto old = t.profiles.data();
    auto invalid = t.envelope("wifi", "wifi", network1);
    invalid.replace(invalid.find(device), 32, std::string(32, 'b'));
    REQUIRE(t.request("PUT", "/api/usb/v1/wifi", invalid).status == 409 &&
            t.profiles.data() == old);
}
provisioning::ConsumerProfile legacy_consumer() {
    provisioning::ConsumerProfile profile;
    profile.device_id = device;
    profile.ssid = "test-network";
    profile.password = "test-password";
    profile.time_server = "192.0.2.1";
    profile.callsign = "AA0NT";
    profile.locator = "EM18";
    profile.power_dbm = 37;
    profile.tls_pending = true;
    profile.tls.hostname = "retained.local";
    profile.request_sha256 = std::string(64, 'a');
    return profile;
}
void legacy_station_migration() {
    Test t;
    auto profile = legacy_consumer();
    REQUIRE(t.profiles.select(provisioning::ProfileSource::ConsumerProfile,
                              provisioning::serialize_consumer_profile(profile)));
    REQUIRE(t.runtime.load(t.profiles, device, provisioning::BuildBundleState::Absent));
    auto candidate = *standalone::parse_config(config);
    candidate.wspr_dial_frequency_hz = 14'095'600;
    candidate.gpio_drive_ma = 12;
    candidate.pins.amplifier_active_high = false;
    candidate.callsign = "AB1CD";
    candidate.locator = "EM19";
    candidate.schedules = {{240, 120}};
    const auto changed =
        t.request("POST", "/api/control/v1/config/update", network_test::configuration_update(standalone::serialize_config(candidate)));
    REQUIRE(changed.status == 200);
    REQUIRE(t.runtime.consumer_profile()->usb_managed);
    REQUIRE(t.runtime.consumer_profile()->callsign.empty());
    REQUIRE(t.f.store.config() == candidate);
    REQUIRE(t.runtime.overlay(*t.f.store.config()) == candidate);
    REQUIRE(t.f.api.saved_station_json().find(candidate.callsign) != std::string::npos);
    REQUIRE(t.runtime.consumer_profile()->tls == profile.tls);
    candidate.manual_correction_ppb = -1234;
    candidate.ntp_rf_calibration = true;
    REQUIRE(t.f.store.save(candidate));
    REQUIRE(t.runtime.overlay(candidate) == candidate);
    REQUIRE(t.wifi("null").status == 200);
    REQUIRE(t.f.store.config()->manual_correction_ppb == -1234);
    REQUIRE(t.f.store.config()->ntp_rf_calibration);
    REQUIRE(t.f.store.config()->callsign == candidate.callsign);
    REQUIRE(t.f.store.config()->schedules == candidate.schedules);
    REQUIRE(t.runtime.consumer_profile()->tls == profile.tls);
    Test no_base;
    REQUIRE(no_base.profiles.select(provisioning::ProfileSource::ConsumerProfile,
                                    provisioning::serialize_consumer_profile(legacy_consumer())));
    REQUIRE(no_base.runtime.load(no_base.profiles, device, provisioning::BuildBundleState::Absent));
    REQUIRE(no_base.wifi("null").status == 200);
    REQUIRE(no_base.f.store.config() && no_base.f.store.config()->callsign == "AA0NT");
}
void engineering_network_preserves_trust() {
    Test t;
    provisioning::Profile profile;
    profile.device_id = device;
    profile.ssid = "engineering-net";
    profile.password = "engineering-password";
    profile.time_server = "192.0.2.2";
    profile.hostname = "certified.local";
    profile.port = 443;
    profile.server_certificate = "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
    profile.server_private_key = "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
    profile.client_ca = profile.server_certificate;
    REQUIRE(t.profiles.replace(provisioning::serialize_profile(profile)));
    REQUIRE(t.runtime.load(t.profiles, device, provisioning::BuildBundleState::Absent));
    REQUIRE(t.wifi("null").status == 200);
    const auto* retained = t.runtime.profile();
    REQUIRE(retained && retained->ssid.empty() && retained->password.empty() &&
            retained->usb_managed);
    REQUIRE(retained->hostname == profile.hostname &&
            retained->server_private_key == profile.server_private_key);
    REQUIRE(retained->server_certificate == profile.server_certificate &&
            retained->client_ca == profile.client_ca);
    REQUIRE(t.request("PUT", "/api/control/v1/hostname",
                      t.envelope("hostname", "hostname", "\"other.local\""))
                .status == 409);
    REQUIRE(t.wifi(network2).status == 200);
    REQUIRE(t.runtime.profile()->server_private_key == profile.server_private_key);
}
void saved_progress_explicit_usb_application() {
    Test t;
    REQUIRE(t.request("PUT", "/api/control/v1/hostname",
                      t.envelope("hostname", "hostname", "\"progress.local\""))
                .status == 200);
    const auto save = [&](std::string_view fields) {
        auto body = t.envelope("progress", "fields", fields);
        body.pop_back();
        body += ",\"request_id\":\"" + std::string(32, '1') + "\"}";
        return t.request("POST", "/api/control/v1/progress/update", body);
    };
    REQUIRE(save(R"({"callsign":"AA0NT"})").status == 200);
    REQUIRE(!t.f.store.config());
    const auto incomplete = t.request("GET", "/api/control/v1/progress");
    const auto incomplete_json = wtp::json::parse(incomplete.body_view());
    REQUIRE(incomplete_json && incomplete_json->get("station_complete")->raw == "false");
    REQUIRE(incomplete_json->get("applied_station")->raw == "null");
    REQUIRE(save(R"({"locator":"EM18","power_dbm":20})").status == 200);
    const auto before_apply_profile = t.profiles.data();
    const auto before_apply_sequence = t.f.store.config_sequence();
    network::HttpRequest read;
    read.method = "GET";
    read.path = "/api/control/v1/progress";
    read.headers["host"] = "127.0.0.1";
    const auto observed = t.f.api.handle(network_test::control_request(read), "network-consumer", "127.0.0.1", 99,
                                         network::ManagementCarrier::ConsumerStation);
    REQUIRE(observed.status == 200);
    const auto observed_json = wtp::json::parse(observed.body_view());
    REQUIRE(observed_json && observed_json->get("station_complete")->raw == "true");
    REQUIRE(observed_json->get("applied_station")->raw == "null");
    t.f.scheduler.poll();
    REQUIRE(!t.f.store.config() && t.f.store.config_sequence() == before_apply_sequence);
    REQUIRE(t.profiles.data() == before_apply_profile);
    const auto application = [&](std::string_view revision) {
        return t.envelope("progress", "application",
                          "{\"draft_revision\":" + wtp::json::quote(revision) +
                              ",\"domain\":\"station\"}");
    };
    REQUIRE(t.request("POST", "/api/control/v1/progress/apply", application("0")).status == 400);
    REQUIRE(!t.f.store.config());
    REQUIRE(t.request("POST", "/api/control/v1/progress/apply",
                      application(std::to_string(t.progress.sequence())))
                .status == 200);
    REQUIRE(t.f.store.config() && t.f.store.config()->callsign == "AA0NT");
    REQUIRE(t.f.store.config()->ssid.empty() && t.f.store.config()->password.empty());
    REQUIRE(!t.f.store.config()->enabled && t.f.store.config()->schedules == std::vector<standalone::Schedule>({{600, 0}}));
    REQUIRE(t.runtime.consumer_profile()->usb_managed);
    // Network observers cannot turn a draft into a consumer station-identity
    // edit. The USB carrier can explicitly apply the same reviewed draft.
    REQUIRE(save(R"({"callsign":"AB1CD"})").status == 200);
    const auto applied = *t.f.store.config();
    const auto profile = t.profiles.data();
    network::HttpRequest apply;
    apply.method = "POST";
    apply.path = "/api/control/v1/progress/apply";
    apply.body = application(std::to_string(t.progress.sequence()));
    apply.headers = {{"host", "127.0.0.1"},
                     {"origin", "https://127.0.0.1"},
                     {"content-type", "application/json"},
                     {"x-wsprrypico-request", "1"},
                     {"if-match", t.f.api.revision()}};
    REQUIRE(t.f.api
                .handle(network_test::control_request(apply), "network-consumer", "127.0.0.1", 101,
                        network::ManagementCarrier::ConsumerStation)
                .status == 409);
    REQUIRE(t.f.store.config() == applied && t.profiles.data() == profile);
    REQUIRE(t.request("POST", apply.path, apply.body).status == 200);
    REQUIRE(t.f.store.config()->callsign == "AB1CD");
}
void network_only_and_factory_profiles() {
    Test network_only;
    provisioning::NetworkProfile network_profile{device, "network-only", "network-password",
                                                 "pool.ntp.org"};
    REQUIRE(network_only.profiles.select(provisioning::ProfileSource::NetworkOnly,
                                         provisioning::serialize_network_profile(network_profile)));
    REQUIRE(network_only.runtime.load(network_only.profiles, device,
                                      provisioning::BuildBundleState::Absent));
    REQUIRE(network_only.wifi("null").status == 200);
    REQUIRE(network_only.runtime.consumer_profile() &&
            network_only.runtime.consumer_profile()->usb_managed);
    REQUIRE(network_only.runtime.consumer_profile()->ssid.empty());
    REQUIRE(!network_only.f.store.config()); // No invented station from network-only authority.
    Test factory;
    REQUIRE(
        factory.runtime.load(factory.profiles, device, provisioning::BuildBundleState::Matching));
    provisioning::Profile bundle;
    bundle.device_id = device;
    bundle.ssid = "factory-network";
    bundle.password = "factory-password";
    bundle.time_server = "192.0.2.1";
    bundle.hostname = "certified.local";
    bundle.port = 443;
    bundle.server_certificate = "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
    bundle.server_private_key = "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
    bundle.client_ca = bundle.server_certificate;
    factory.settings.factory_profile(bundle);
    REQUIRE(factory.wifi("null").status == 200);
    REQUIRE(factory.runtime.profile() && factory.runtime.profile()->ssid.empty());
    REQUIRE(factory.runtime.profile()->server_certificate == bundle.server_certificate);
    REQUIRE(factory.runtime.profile()->server_private_key == bundle.server_private_key);
    REQUIRE(factory.runtime.profile()->client_ca == bundle.client_ca);
    REQUIRE(factory.runtime.profile()->hostname == bundle.hostname);
    REQUIRE(factory.wifi(network1).status == 200);
    auto retained = *factory.runtime.profile();
    retained.usb_managed = false;
    REQUIRE(provisioning::serialize_profile(retained).size() == factory.profiles.data().size());
    auto old = legacy_consumer();
    const auto old_size = provisioning::serialize_consumer_profile(old).size();
    old.usb_managed = true;
    old.callsign.clear();
    old.locator.clear();
    old.power_dbm = 0;
    REQUIRE(provisioning::serialize_consumer_profile(old).size() < old_size);
}
void profile_power_cuts() {
    for (unsigned page = 1; page <= 6; ++page) {
        Test t;
        REQUIRE(t.wifi(network1).status == 200);
        t.media.fail_at = t.media.writes + page;
        const auto response = t.wifi("null");
        provisioning::ProfileStore cold(t.media);
        provisioning::RuntimeProfile runtime;
        REQUIRE(cold.load() && runtime.load(cold, device, provisioning::BuildBundleState::Absent));
        REQUIRE(runtime.consumer_profile());
        if (response.status == 200)
            REQUIRE(runtime.consumer_profile()->ssid.empty());
        else
            REQUIRE(runtime.consumer_profile()->ssid == "test-network");
        if (runtime.consumer_profile()->ssid.empty()) {
            const auto applied = t.progress.candidate(t.f.store.config());
            if (applied)
                REQUIRE(applied->ssid.empty());
        }
    }
}
} // namespace
int main() {
    blank_usb_workflow();
    preserves_state_and_network_policy();
    legacy_station_migration();
    engineering_network_preserves_trust();
    saved_progress_explicit_usb_application();
    network_only_and_factory_profiles();
    profile_power_cuts();
}
