#include "network/softap_api.hpp"
#include "network_support.hpp"
#include "provisioning/access.hpp"
#include "provisioning/local_access.hpp"
#include "time/utc_discipline.hpp"

#include <array>

namespace {
using namespace wsprrypico;
constexpr std::string_view device = "00112233445566778899aabbccddeeff";
constexpr std::string_view hostname = "wsprrypico-0a60df.local";
constexpr std::string_view session = "11111111111111111111111111111111";

class AccessMemory final : public provisioning::AccessMedia {
  public:
    std::array<std::uint8_t, provisioning::access_media_size> bytes{};
    AccessMemory() {
        bytes.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> out) override {
        if (offset + out.size() > bytes.size())
            return false;
        std::copy_n(bytes.begin() + offset, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (offset % provisioning::access_slot_size ||
            offset + provisioning::access_slot_size > bytes.size())
            return false;
        std::fill_n(bytes.begin() + offset, provisioning::access_slot_size, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        if (page.size() != provisioning::access_page_size ||
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
class Bonds final : public provisioning::BondStore {
  public:
    bool erase(std::uint64_t) override {
        return true;
    }
    bool erase_all() override {
        return true;
    }
};
class Random final : public provisioning::RandomSource {
  public:
    std::uint8_t next = 1;
    bool fill(std::span<std::uint8_t> bytes) override {
        for (auto& byte : bytes)
            byte = next++;
        return true;
    }
};
std::uint64_t monotonic(void* context) {
    return *static_cast<std::uint64_t*>(context);
}

struct Fixture {
    std::uint64_t now = 1'000'000'000ULL;
    time::DisciplineConfig discipline_config{};
    time::UtcDiscipline clock;
    network_test::Flash flash;
    standalone::Store store{flash};
    standalone::DryRunEngine engine;
    network_test::Identity identities;
    wtp::JobService service;
    standalone::Scheduler scheduler;
    network_test::Network network;
    network::BrowserApi browser;
    AccessMemory access_media;
    provisioning::AccessStore access_store{access_media};
    Bonds bonds;
    Random random;
    provisioning::LocalIdentity identity =
        *provisioning::derive_local_identity(device, "02:11:22:0a:60:df");
    provisioning::LocalAccessController access;
    time::ControllerTimeArbiter time;
    provisioning::SoftApHttpAdmission admission;
    network::SoftApApi api;

    Fixture()
        : clock(monotonic, &now, discipline_config),
          service(clock, engine, identities, network_test::Fixture::physical_policy()),
          scheduler(store, service),
          browser(service, store, scheduler, network, std::string(device), "test-firmware"),
          access(access_store, bonds, random, std::string(device), service.status().boot_id,
                 identity),
          time(clock, monotonic, &now, std::string(device)),
          admission(access, std::string(device), std::string(hostname)),
          api(browser, admission, access, time, service, std::string(device), "test-firmware") {
        REQUIRE(store.load());
        REQUIRE(access_store.load());
        provisioning::AccessRecord record;
        record.epoch = 1;
        record.password = identity.default_password;
        REQUIRE(access_store.initialize(record));
        provisioning::scrub(record);
    }
};

network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    network::HttpRequest result;
    result.method = std::move(method);
    result.path = std::move(path);
    result.body = std::move(body);
    result.headers = {{"host", std::string(hostname)},
                      {"origin", "https://" + std::string(hostname)},
                      {"content-type", "application/json"},
                      {"x-wsprrypico-request", "1"},
                      {"x-wsprrypico-session", std::string(session)},
                      {"sec-fetch-site", "same-origin"}};
    return result;
}

void policy() {
    Fixture f;
    auto identity = request("GET", "/local/v1/identity");
    identity.headers.erase("origin");
    REQUIRE(
        f.api.handle(identity, provisioning::SoftApSurface::BlankReadOnly, hostname, 0, 1).status ==
        200);
    auto login = request("POST", "/local/v1/login",
                         "{\"version\":1,\"device_id\":\"" + std::string(device) +
                             "\",\"password\":\"wspr-0a60df\"}");
    REQUIRE(
        f.api.handle(login, provisioning::SoftApSurface::BlankReadOnly, hostname, 0, 2).status ==
        401);
    auto admitted =
        f.api.handle(login, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 1, 3);
    REQUIRE(admitted.status == 200);
    REQUIRE(admitted.set_cookie.starts_with("__Host-wsprrypico="));
    REQUIRE(admitted.wire_headers().find("Set-Cookie: __Host-wsprrypico=") != std::string::npos);
    const auto semicolon = admitted.set_cookie.find(';');
    const auto cookie = admitted.set_cookie.substr(0, semicolon);

    auto status = request("GET", "/local/v1/status");
    status.headers.erase("origin");
    REQUIRE(f.api.handle(status, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 2, 4)
                .status == 401);
    status.headers["cookie"] = cookie;
    REQUIRE(f.api.handle(status, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 2, 5)
                .status == 200);
    auto unbound_status = status;
    unbound_status.headers["x-wsprrypico-session"] = std::string(32, '8');
    REQUIRE(f.api
                .handle(unbound_status, provisioning::SoftApSurface::ProvisionedPreClock, hostname,
                        2, 16)
                .status == 200);
    auto config = request("GET", "/api/v1/config");
    config.headers.erase("origin");
    config.headers["cookie"] = cookie;
    REQUIRE(f.api.handle(config, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 3, 6)
                .status == 401);

    const auto time_body = "{\"version\":1,\"device_id\":\"" + std::string(device) +
                           "\",\"session_id\":\"" + std::string(session) +
                           "\",\"nonce\":\"22222222222222222222222222222222\"}";
    auto challenge = request("POST", "/local/v1/time/challenge", time_body);
    challenge.headers["cookie"] = cookie;
    REQUIRE(
        f.api.handle(challenge, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 4, 7)
            .status == 200);
    f.api.finish_request(7, false);
    auto submit =
        request("POST", "/local/v1/time/submit",
                time_body.substr(0, time_body.size() - 1) + ",\"utc_ns\":\"1800000000000000000\"}");
    submit.headers["cookie"] = cookie;
    REQUIRE(f.api.handle(submit, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 5, 8)
                .status == 409);

    challenge.body.replace(challenge.body.find(std::string(32, '2')), 32, std::string(32, '3'));
    REQUIRE(
        f.api.handle(challenge, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 6, 9)
            .status == 200);
    f.api.finish_request(9, true);
    submit.body.replace(submit.body.find(std::string(32, '2')), 32, std::string(32, '3'));
    f.now += 10'000'000ULL;
    REQUIRE(f.api.handle(submit, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 7, 10)
                .status == 200);
    REQUIRE(f.clock.snapshot().state == wtp::ClockState::Synchronized);

    auto caps = request("GET", "/api/v1/capabilities");
    caps.headers.erase("origin");
    caps.headers["cookie"] = cookie;
    const auto capabilities =
        f.api.handle(caps, provisioning::SoftApSurface::Normal, hostname, 8, 11);
    REQUIRE(capabilities.status == 200);
    REQUIRE(capabilities.body.find("\"softap\":true") != std::string::npos);
    REQUIRE(capabilities.body.find("\"ble\":true") != std::string::npos);

    auto hello = request("POST", "/api/v1/jobs",
                         "{\"session_id\":\"" + std::string(session) +
                             "\",\"request_id\":\"44444444444444444444444444444444\","
                             "\"operation\":\"HELLO\",\"body\":{\"versions\":[\"WTP/1\"],"
                             "\"client_name\":\"softap-test\",\"client_version\":\"1\"}}");
    hello.headers["cookie"] = cookie;
    REQUIRE(f.api.handle(hello, provisioning::SoftApSurface::Normal, hostname, 9, 12).status ==
            200);
    auto refreshed_status = status;
    refreshed_status.headers["x-wsprrypico-session"] = std::string(32, '8');
    const auto refreshed =
        f.api.handle(refreshed_status, provisioning::SoftApSurface::Normal, hostname, 10, 17);
    REQUIRE(refreshed.status == 200);
    REQUIRE(refreshed.body.find("\"wtp_session\":\"" + std::string(session) + "\"") !=
            std::string::npos);
    auto conflicting_status = request("GET", "/api/v1/status");
    conflicting_status.headers.erase("origin");
    conflicting_status.headers["cookie"] = cookie;
    conflicting_status.headers["x-wsprrypico-session"] = std::string(32, '8');
    REQUIRE(f.api.handle(conflicting_status, provisioning::SoftApSurface::Normal, hostname, 10, 18)
                .status == 409);
    hello.headers["x-wsprrypico-session"] = std::string(32, '9');
    REQUIRE(f.api.handle(hello, provisioning::SoftApSurface::Normal, hostname, 10, 13).status ==
            400);

    auto logout = request("POST", "/local/v1/logout", "{}");
    logout.headers["cookie"] = cookie;
    const auto logged_out =
        f.api.handle(logout, provisioning::SoftApSurface::Normal, hostname, 11, 14);
    REQUIRE(logged_out.status == 200);
    REQUIRE(logged_out.set_cookie.find("Max-Age=0") != std::string::npos);
    REQUIRE(f.api.handle(status, provisioning::SoftApSurface::Normal, hostname, 12, 15).status ==
            401);

    network::HttpResponse injected;
    injected.set_cookie = "safe=value\r\nX-Injected: true";
    REQUIRE(injected.wire_headers().find("X-Injected") == std::string::npos);
}

void expired_challenge_bookkeeping_is_reused() {
    Fixture f;
    auto login = request("POST", "/local/v1/login",
                         "{\"version\":1,\"device_id\":\"" + std::string(device) +
                             "\",\"password\":\"wspr-0a60df\"}");
    auto admitted =
        f.api.handle(login, provisioning::SoftApSurface::ProvisionedPreClock, hostname, 1, 1);
    REQUIRE(admitted.status == 200);
    const auto cookie = admitted.set_cookie.substr(0, admitted.set_cookie.find(';'));

    for (unsigned i = 0; i < 3; ++i) {
        const auto nonce = std::string(31, '2') + static_cast<char>('2' + i);
        auto challenge = request("POST", "/local/v1/time/challenge",
                                 "{\"version\":1,\"device_id\":\"" + std::string(device) +
                                     "\",\"session_id\":\"" + std::string(session) +
                                     "\",\"nonce\":\"" + nonce + "\"}");
        challenge.headers["cookie"] = cookie;
        REQUIRE(f.api
                    .handle(challenge, provisioning::SoftApSurface::ProvisionedPreClock, hostname,
                            2 + i, 2 + i)
                    .status == 200);
        f.api.finish_request(2 + i, true);
        f.now += 10'000'000'001ULL;
    }
}
} // namespace

int main() {
    policy();
    expired_challenge_bookkeeping_is_reused();
}
