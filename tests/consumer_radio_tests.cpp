#include "application/resources.hpp"
#include "network/bootstrap_codec.hpp"
#include "network/consumer_radio.hpp"
#include "network/public_read.hpp"
#include "network_support.hpp"
#include "provisioning/consumer_profile.hpp"
#include "rf/stream_engine.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#include <cassert>
using namespace wsprrypico;
using namespace network_test;
namespace {
constexpr auto device = "11111111111111111111111111111111";
constexpr auto boot = "22222222222222222222222222222222";
std::map<void*, std::size_t> message_pages;
std::size_t message_page_bytes = 0;
struct Media : provisioning::Media {
    std::array<std::uint8_t, 16384> data{};
    Media() {
        data.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        std::copy_n(data.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        std::fill_n(data.begin() + at, 8192, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        std::copy(in.begin(), in.end(), data.begin() + at);
        return true;
    }
};
struct Random : provisioning::RandomSource {
    unsigned next = 1;
    bool fill(std::span<std::uint8_t> bytes) override {
        for (auto& b : bytes)
            b = next++;
        return true;
    }
};
struct Crypto : network::ConsumerRadioCrypto {
    network::ConsumerRadioBinding binding{};
    bool password_ok = true, tag_ok = true;
    bool begin() override {
        return true;
    }
    std::array<std::uint8_t, 32> public_key() const override {
        return {};
    }
    bool authenticate(wtp::FrameBuffer&, const network::ConsumerRadioBinding& b,
                      std::string_view password) override {
        assert(password == "test-password");
        binding = b;
        return password_ok;
    }
    std::optional<wtp::InputView> open(wtp::FrameBuffer& p, const network::ConsumerRadioBinding&,
                                       std::uint64_t) override {
        if (!tag_ok)
            return {};
        return p.view().substr(28, p.size() - 44);
    }
    std::optional<network::HttpResponse> seal_parts(std::span<const wtp::InputView> parts,
                                                    const network::ConsumerRadioBinding&,
                                                    std::uint64_t) override {
        std::string text;
        for (const auto part : parts)
            text += std::string(part);
        return network::HttpResponse{200, std::move(text), "application/json", {}};
    }
    std::optional<network::HttpResponse> seal_buffer(wtp::OutputBuffer plaintext,
                                                     const network::ConsumerRadioBinding& binding,
                                                     std::uint64_t sequence) override {
        const auto view = plaintext.view();
        return seal_parts(std::span(&view, 1), binding, sequence);
    }
    void clear() override {}
};
network::HttpRequest request(std::string path, std::string body = {}, bool binary = false) {
    network::HttpRequest r{
        "POST",
        std::move(path),
        std::move(body),
        {{"host", "192.168.4.1"},
         {"origin", "http://192.168.4.1"},
         {"content-type", binary ? "application/octet-stream" : "application/json"},
         {"x-wsprrypico-radio", "1"}}};
    if (binary) {
        r.buffered_body = std::make_shared<wtp::FrameBuffer>();
        assert(r.buffered_body->reserve(r.body.size()));
        r.buffered_body->append(wtp::InputView(r.body));
        r.body.clear();
    }
    return r;
}
struct Test {
    Fixture fixture;
    Media media;
    provisioning::ProfileStore store{media};
    provisioning::RuntimeProfile runtime;
    Random random;
    Crypto crypto, crypto2, crypto3;
    network::ConsumerRadioApi api{
        fixture.api, store, runtime, random, {&crypto, &crypto2, &crypto3}, device, boot};
    std::uint64_t now = 1000, sequence = 1, transaction = 100;
    std::string authority = "192.168.4.1";
    network::ConsumerInterface interface = network::ConsumerInterface::AccessPoint;
    network::HttpResponse send(network::HttpRequest r, std::uint64_t tx) {
        r.headers["host"] = authority;
        r.headers["origin"] = "http://" + authority;
        return api.handle(r, now, tx, interface);
    }
    Test(bool network_only = false, wtp::RfEngine* engine = nullptr)
        : fixture(0, std::string(32, 'a'), engine) {
        provisioning::ConsumerProfile profile;
        profile.device_id = device;
        profile.owner_epoch = 0;
        profile.ssid = "test-network";
        profile.password = "test-password";
        profile.time_server = "192.0.2.1";
        profile.callsign = "AA0NT";
        profile.locator = "EM18";
        profile.power_dbm = 37;
        profile.tls_pending = true;
        profile.tls.hostname = "wsprrypico-0a60df.local";
        profile.request_sha256 = std::string(64, 'a');
        assert(store.load());
        if (network_only)
            assert(
                store.select(provisioning::ProfileSource::NetworkOnly,
                             provisioning::serialize_network_profile(
                                 {device, profile.ssid, profile.password, profile.time_server})));
        else
            assert(store.select(provisioning::ProfileSource::ConsumerProfile,
                                provisioning::serialize_consumer_profile(profile)));
        assert(runtime.load(store, device, provisioning::BuildBundleState::Absent));
        fixture.api.consumer_config(runtime);
        if (!network_only)
            assert(fixture.scheduler.command("CONFIG " + config).find("true") != std::string::npos);
        api.admission(runtime.control_healthy(store) && runtime.consumer_browser_selected(store));
        api.listeners(true, "192.168.1.53", "wsprrypico-0a60df.local");
        assert(fixture.store.reserve(1791970000000000000ULL));
    }
    network::HttpResponse start() {
        return send(
            request(
                "/api/consumer/v1/start",
                R"({"version":1,"device_id":"11111111111111111111111111111111","boot_id":"22222222222222222222222222222222","generation":"1","public_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","nonce":"00000000000000000000000000000000"})"),
            transaction++);
    }
    void login() {
        sequence = 1;
        auto result = start();
        assert(result.status == 200);
        const auto root = wtp::json::parse(result.body);
        std::array<std::uint8_t, 16> session{};
        assert(network::bootstrap_unhex(root->get("session_id")->string(), session));
        auto h = network::consumer_radio_header(session, 0);
        std::string packet(h.begin(), h.end());
        packet.resize(44);
        assert(send(request("/api/consumer/v1/finish", packet, true), transaction++).status == 200);
    }
    network::HttpResponse call(std::string method, std::string path, std::string body = "null",
                               std::string revision = {}) {
        auto h = network::consumer_radio_header(crypto.binding.session, sequence++);
        std::string packet(h.begin(), h.end());
        packet += "{\"method\":" + wtp::json::quote(method) +
                  ",\"path\":" + wtp::json::quote(path) +
                  ",\"if_match\":" + (revision.empty() ? "null" : wtp::json::quote(revision)) +
                  ",\"body\":" + body + "}";
        packet.resize(packet.size() + 16);
        return send(request("/api/consumer/v1/request", packet, true), transaction++);
    }
};
network::HttpResponse read_public(Test& test) {
    auto get = request("/api/consumer/v1/status");
    get.method = "GET";
    return test.send(std::move(get), test.transaction++);
}
} // namespace
int main() {
    {
        Test t;
        auto read = [&](std::string path, std::string method = "GET", std::string body = {}) {
            auto r = request(std::move(path), std::move(body));
            r.method = std::move(method);
            return t.send(std::move(r), t.transaction++);
        };
        const auto revision = t.fixture.store.config_sequence();
        const auto caps = read("/api/consumer/v1/read");
        const auto root = wtp::json::parse(caps.body);
        assert(caps.status == 200 && root &&
               wtp::json::fields(*root, {"schema", "target", "prefix", "resources"}));
        assert(root->get("schema")->string() == "pico-public-read/1");
        assert(root->get("resources")->elements().size() == network::public_read_resources.size());
        const auto config_read = read("/api/consumer/v1/read/config/4");
        assert(config_read.status == 200 && config_read.body.find("AA0NT") != std::string::npos);
        assert(config_read.body.find("test-password") == std::string::npos);
        const auto operations = read("/api/consumer/v1/read/operations");
        assert(operations.status == 200 &&
               operations.body.find("transmitter-operations/1") != std::string::npos);
        for (const auto resource : network::public_read_resources) {
            const auto path = "/api/consumer/v1/read/" + std::string(resource);
            for (const auto method : {"POST", "PUT", "DELETE"})
                assert(read(path, method, "{\"enabled\":true}").status == 405);
        }
        for (const auto suffix :
             {"jobs", "restart", "progress/apply", "pins/validate", "config/update", "../jobs"})
            assert(read("/api/consumer/v1/read/" + std::string(suffix)).status == 404);
        assert(read("/api/consumer/v1/read/config", "GET", "{}").status == 400);
        auto cross_site = request("/api/consumer/v1/read/config");
        cross_site.method = "GET";
        cross_site.headers["origin"] = "http://other.example";
        assert(t.api.handle(cross_site, t.now, t.transaction++).status == 403);
        assert(!t.api.active(t.now) && t.fixture.store.config_sequence() == revision);
        assert(t.fixture.service.status().state == wtp::State::Empty);
    }
    {
        Test t;
        auto response = read_public(t);
        assert(response.status == 200);
        const auto value = wtp::json::parse(response.body);
        assert(value && wtp::json::fields(*value, {"schema", "device_id", "boot_id", "state",
                                                   "output_active", "owned", "clock_state",
                                                   "utc_now_ns", "uncertainty_ns", "engine"}));
        assert(value->get("schema")->string() == "transmitter-public-status/1");
        assert(value->get("state")->string() == "empty");
        assert(value->get("output_active")->raw == "false");
        assert(value->get("owned")->raw == "false");
        assert(response.body.find("owner_id") == std::string::npos);
        assert(response.body.find("test-password") == std::string::npos);
        assert(response.body.find("AA0NT") == std::string::npos);
        assert(!t.api.active(t.now));
        auto forged = request("/api/consumer/v1/status");
        forged.method = "GET";
        forged.headers["host"] = "evil.example";
        assert(t.api.handle(forged, t.now, t.transaction++).status == 403);
        forged.headers["host"] = "192.168.4.1";
        forged.headers["origin"] = "http://evil.example";
        assert(t.api.handle(forged, t.now, t.transaction++).status == 403);
        assert(t.send(request("/api/consumer/v1/status", "{}"), t.transaction++).status != 200);
        wtp::available_memory = []() -> std::size_t { return 32768; };
        assert(read_public(t).status == 503);
        wtp::available_memory = nullptr;
    }
    {
        struct Sink final : rf::BlockSink {
            bool stop(std::uint64_t) override {
                return true;
            }
            bool submit(std::uint64_t, std::uint64_t, std::span<const std::uint32_t>,
                        std::uint64_t) override {
                std::abort();
            }
            bool arm(std::uint64_t, std::uint64_t, std::uint64_t, rf::LaunchGuard) override {
                std::abort();
            }
            rf::SinkReport poll(std::uint64_t) override {
                return {};
            }
            bool output_active() const override {
                return false;
            }
        } sink;
        rf::StreamEngine engine(sink);
        Test t(false, &engine);
        t.authority = "192.168.1.53";
        t.interface = network::ConsumerInterface::Station;
        t.login();
        const std::string session(32, '1');
        unsigned id = 2000;
        const auto command = [&](std::string op, std::string body) {
            auto result = t.call("POST", "/api/v1/jobs",
                                 "{\"session_id\":\"" + session + "\",\"request_id\":\"" +
                                     std::string(28, '0') + std::to_string(++id) +
                                     "\",\"operation\":\"" + op + "\",\"body\":" + body + "}");
            assert(result.status == 200);
            assert(result.body.find("\"status\":200") != std::string::npos);
            t.api.finish_request(t.transaction - 1, true);
            return result.body.size();
        };
        command(
            "HELLO",
            R"({"versions":["WTP/1"],"client_name":"message regression","client_version":"1"})");
        command("CLAIM", "{\"owner_id\":\"" + session + "\",\"lease_ms\":60000}");
        // Model resident request/event/reply pages as real allocations. The
        // large adjustment JSON leaves room for framing, but not another full
        // ciphertext allocation alongside the unchanged 32 KiB reserve.
        const auto allocate = wtp::allocate_input;
        const auto deallocate = wtp::deallocate_input;
        wtp::allocate_input = [](std::size_t size) -> void* {
            auto* memory = std::malloc(size);
            if (memory) {
                message_pages[memory] = size;
                message_page_bytes += size;
            }
            return memory;
        };
        wtp::deallocate_input = [](void* memory) {
            if (const auto found = message_pages.find(memory); found != message_pages.end()) {
                message_page_bytes -= found->second;
                message_pages.erase(found);
            }
            std::free(memory);
        };
        wtp::available_memory = []() -> std::size_t { return 70000 - message_page_bytes; };
        const auto bytes = command(
            "LOAD_MESSAGE",
            R"({"job_id":"33333333333333333333333333333333","mode":"fskcw","message":"CQ CQ DE AA0NT EM18 QRSS TEST 73","frequency_nhz":"10140005000000000","space_frequency_nhz":"10140000000000000","timing":{"dot_ns":"3000000000","dash_ns":"9000000000","intra_gap_ns":"3000000000","character_gap_ns":"9000000000","word_gap_ns":"21000000000"},"repeat_count":1,"repeat_gap_ns":"3000000000","allow_frequency_adjustment":true})");
        wtp::available_memory = nullptr;
        assert(bytes > wtp::OutputBuffer::page_bytes);
        assert(t.fixture.service.status().state == wtp::State::Loaded);
        assert(!t.fixture.service.status().output_active);
        command("RELEASE", "{}");
        assert(!t.fixture.service.status().owner_id);
        t.api.close();
        assert(message_pages.empty());
        wtp::allocate_input = allocate;
        wtp::deallocate_input = deallocate;
    }
    for (const auto* host : {"192.168.1.53", "wsprrypico-0a60df.local"}) {
        Test t(true);
        t.authority = host;
        t.interface = network::ConsumerInterface::Station;
        network::HttpRequest page{"GET", "/", "", {{"host", host}}};
        assert(t.api.page_admitted(page, t.interface));
        assert(!t.runtime.consumer_profile());
        assert(!t.fixture.store.config());
        const auto profile = t.media.data;
        t.login();
        auto response = t.call("GET", "/api/v1/config");
        assert(response.status == 200);
        assert(response.body.find("\"config\":null") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        response = t.call("GET", "/api/v1/capabilities");
        assert(response.body.find("\"consumer_setup_identity\":true") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        assert(t.media.data == profile);
        assert(!t.fixture.store.config());
        // A changed or corrupt profile must close the old authenticated authority.
        assert(t.store.select(provisioning::ProfileSource::Unprovisioned, ""));
        assert(!t.api.available());
        assert(t.call("GET", "/api/v1/status").status == 409);
    }
    {
        Test t;
        t.login();
        const auto cursor = t.fixture.store.watermark();
        const auto profile = t.media.data;
        const auto target =
            application::target(std::string(32, 'a'), t.fixture.service.status().boot_id);
        const auto update = [&](std::string config) {
            return "{\"schema\":\"transmitter-config-update/1\",\"target\":" + target +
                   ",\"mode\":\"merge\",\"config\":" + config + '}';
        };
        auto result =
            t.call("POST", "/api/v1/config/update",
                   update("{\"allow_unqualified_frequency\":true}"), t.fixture.api.revision());
        assert(result.body.find("\"status\":200") != std::string::npos);
        assert(t.fixture.store.config()->allow_unqualified_frequency);
        assert(t.fixture.store.watermark() == cursor && t.media.data == profile);
        t.api.finish_request(t.transaction - 1, true);
        const auto generation = t.fixture.store.config_sequence();
        result =
            t.call("POST", "/api/v1/config/update",
                   update("{\"wifi\":{\"ssid\":\"other-network\"}}"), t.fixture.api.revision());
        assert(result.body.find("consumer_setup_identity_required") != std::string::npos);
        assert(t.fixture.store.config_sequence() == generation);
        t.api.finish_request(t.transaction - 1, true);
        bool setup_busy = true;
        t.api.setup_handler(nullptr, nullptr, &setup_busy,
                            [](void* context) { return *static_cast<bool*>(context); });
        result =
            t.call("POST", "/api/v1/config/update",
                   update("{\"allow_unqualified_frequency\":false}"), t.fixture.api.revision());
        assert(result.body.find("setup_pending") != std::string::npos);
        assert(t.fixture.store.config_sequence() == generation);
        t.api.finish_request(t.transaction - 1, true);
        setup_busy = false;
        result =
            t.call("POST", "/api/v1/config/update",
                   update("{\"allow_unqualified_frequency\":false}"), t.fixture.api.revision());
        assert(result.body.find("\"status\":200") != std::string::npos);
        assert(!t.fixture.store.config()->allow_unqualified_frequency);
        assert(t.fixture.store.watermark() == cursor && t.media.data == profile);
        t.api.finish_request(t.transaction - 1, true);
    }
    {
        Test t;
        // Overlapping subnets still cannot move a session between interfaces.
        t.api.listeners(true, "192.168.4.1", "wsprrypico-0a60df.local");
        t.interface = network::ConsumerInterface::Station;
        t.login();
        t.interface = network::ConsumerInterface::AccessPoint;
        assert(t.call("GET", "/api/v1/status").status == 403);
        t.interface = network::ConsumerInterface::Station;
        t.sequence = 1;
        t.api.listeners(false, "192.168.4.1", "wsprrypico-0a60df.local");
        assert(t.call("GET", "/api/v1/status").body.find("\"status\":200") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
    }
    {
        Test t;
        bool setup_busy = true;
        t.api.setup_handler(nullptr, nullptr, &setup_busy,
                            [](void* context) { return *static_cast<bool*>(context); });
        t.login();
        assert(t.call("GET", "/api/v1/status").body.find("\"status\":200") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        const std::string hello =
            R"({"session_id":"33333333333333333333333333333333","request_id":"44444444444444444444444444444444","operation":"HELLO","body":{"versions":["WTP/1"],"client_name":"test","client_version":"1"}})";
        assert(t.call("POST", "/api/v1/jobs", hello).body.find("setup_pending") !=
               std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        assert(!t.fixture.service.activity().owned && !t.fixture.service.activity().output_active);
        assert(t.call("PUT", "/api/v1/config", "{}", t.fixture.api.revision())
                   .body.find("setup_pending") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        setup_busy = false;
        assert(t.call("POST", "/api/v1/jobs", hello).body.find("\"status\":200") !=
               std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
    }
    {
        Test t;
        struct Setup {
            unsigned requests = 0, deliveries = 0;
            bool applied = false;
        } setup;
        t.api.setup_handler(
            [](const network::HttpRequest& r, std::uint64_t, std::span<const std::uint8_t, 16>,
               void* p) {
                auto& s = *static_cast<Setup*>(p);
                ++s.requests;
                assert(r.path == "/api/bootstrap/v1/start");
                assert(r.header("host") == "192.168.4.1");
                assert(r.header("origin") == "http://192.168.4.1");
                assert(r.body_view() == "{}");
                return network::HttpResponse{200, "{\"ok\":true}", "application/json", {}};
            },
            [](std::uint64_t, bool apply, void* p) {
                auto& s = *static_cast<Setup*>(p);
                ++s.deliveries;
                s.applied = apply;
            },
            &setup);
        t.authority = "192.168.1.53";
        t.interface = network::ConsumerInterface::Station;
        t.login();
        assert(t.call("POST", "/api/v1/consumer/setup/api/bootstrap/v1/start", "{}").status == 200);
        assert(setup.requests == 1 && setup.deliveries == 0);
        t.api.finish_request(t.transaction + 9, true);
        assert(setup.deliveries == 0);
        t.api.listeners(true, {}, "wsprrypico-0a60df.local");
        assert(setup.deliveries == 1 && !setup.applied);
        t.api.finish_request(t.transaction - 1, true);
        assert(setup.deliveries == 1); // Old transaction cannot authorize a successor.
    }
    {
        Test t;
        t.authority = "192.168.1.53";
        t.interface = network::ConsumerInterface::Station;
        t.login();
        const std::string session(32, '1'), job(32, '2');
        unsigned id = 1000;
        const auto command = [&](std::string op, std::string body) {
            auto result = t.call("POST", "/api/v1/jobs",
                                 "{\"session_id\":\"" + session + "\",\"request_id\":\"" +
                                     std::string(28, '0') + std::to_string(++id) +
                                     "\",\"operation\":\"" + op + "\",\"body\":" + body + "}");
            assert(result.body.find("\"status\":200") != std::string::npos);
            t.api.finish_request(t.transaction - 1, true);
        };
        command("HELLO", R"({"versions":["WTP/1"],"client_name":"test","client_version":"1"})");
        command("CLAIM", "{\"owner_id\":\"" + session + "\",\"lease_ms\":30000}");
        command("LOAD", "{\"job_id\":\"" + job +
                            "\",\"profile\":\"rf-events/1\",\"mode\":\"tone\","
                            "\"total_duration_ns\":\"1000000000\",\"events\":[{\"offset_ns\":\"0\","
                            "\"duration_ns\":\"1000000000\","
                            "\"rf_on\":true,\"frequency_nhz\":\"3570100000000000\"}],\"allow_"
                            "frequency_adjustment\":false}");
        assert(t.call("GET", "/api/v1/status").body.find("\"state\":\"loaded\"") !=
               std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        const auto start = t.fixture.clock.snapshot().utc_now_ns + 2'000'000'000ULL;
        command("ARM", "{\"job_id\":\"" + job + "\",\"start_utc_ns\":\"" + std::to_string(start) +
                           "\",\"max_start_uncertainty_ns\":\"1000\"}");
        assert(t.call("GET", "/api/v1/status").body.find("\"state\":\"armed\"") !=
               std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        auto refused =
            t.call("PUT", "/api/v1/network", "{\"enabled\":false}", t.fixture.api.revision());
        assert(refused.body.find("\"status\":409") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        t.fixture.clock.now += 2'000'000'000ULL;
        t.fixture.service.poll();
        assert(t.call("GET", "/api/v1/status").body.find("\"state\":\"running\"") !=
               std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        t.api.close(); // Browser loss neither aborts nor releases accepted local execution.
        assert(t.fixture.service.status().state == wtp::State::Running);
        const auto public_running = read_public(t);
        assert(public_running.status == 200);
        const auto view = wtp::json::parse(public_running.body);
        assert(view->get("state")->string() == "running");
        // This fixture uses a dry-run engine: running does not assert RF output.
        assert(view->get("output_active")->raw == "false");
        assert(view->get("owned")->raw == "true");
        assert(!view->get("owner_id") && !view->get("job_id"));
        assert(t.fixture.service.status().owner_id == session);
        t.fixture.clock.now += 1'000'000'000ULL;
        t.fixture.service.poll();
        assert(t.fixture.service.status().state == wtp::State::Complete);
    }
    {
        Test t;
        const auto station = network::ConsumerInterface::Station;
        auto get = request("/api/consumer/v1/identity");
        get.method = "GET";
        for (const auto host : {"192.168.1.53", "wsprrypico-0a60df.local", "192.168.1.53:80"}) {
            get.headers["host"] = host;
            assert(t.api.handle(get, t.now, 1, station).status == 200);
            assert(t.api.handle(get, t.now, 1).status == 403);
        }
        for (const auto host : {"", "evil.local", "wsprrypico-0a60df.local.evil", "192.168.4.1",
                                "192.168.1.53:81", "192.168.1.053", "user@192.168.1.53",
                                "192.168.1.53/", "192.168.1.53:80:80", "[::1]"}) {
            get.headers["host"] = host;
            assert(t.api.handle(get, t.now, 1, station).status == 403);
        }
        t.authority = "wsprrypico-0a60df.local";
        t.interface = station;
        t.login();
        t.api.listeners(false, "192.168.1.53", t.authority); // AP loss preserves LAN session.
        assert(t.api.active(t.now));
        auto result =
            t.call("PUT", "/api/v1/network", "{\"enabled\":false}", t.fixture.api.revision());
        assert(result.body.find("\"status\":200") != std::string::npos);
        assert(t.fixture.network.pending == false);
        t.api.listeners(false, "192.168.1.54", t.authority); // DHCP cancels deferred action.
        t.api.finish_request(t.transaction - 1, true);
        assert(t.fixture.network.enabled && !t.fixture.network.pending);
        assert(!t.api.active(t.now));
        t.now += 1000;
        t.login();
        t.authority = "192.168.1.54";
        assert(t.call("GET", "/api/v1/status").status == 403); // Same IP netif, different origin.
        --t.sequence;
        t.authority = "wsprrypico-0a60df.local";
        assert(t.call("GET", "/api/v1/status").status == 200);
        t.api.finish_request(t.transaction - 1, true);
        t.api.listeners(false, "192.168.1.54", "renamed.local");
        assert(!t.api.active(t.now));
        t.authority = "renamed.local";
        t.now += 1000;
        t.login();
        t.api.listeners(false, {}, t.authority); // Link/explicit network disable.
        assert(!t.api.active(t.now));
    }
    {
        Test t;
        t.login();
        t.api.listeners(false, "192.168.1.53", "wsprrypico-0a60df.local");
        assert(!t.api.active(t.now)); // AP withdrawal cancels only the AP session.
    }
    {
        provisioning::Activity activity;
        assert(network::consumer_radio_network_idle(activity));
        activity.owned = true;
        assert(network::consumer_radio_network_idle(activity));
        assert(!provisioning::idle_for_access(activity));
        activity.output_known = false;
        assert(!network::consumer_radio_network_idle(activity));
        activity.output_known = true;
        activity.output_active = true;
        assert(!network::consumer_radio_network_idle(activity));
        activity.output_active = false;
        activity.armed = true;
        assert(!network::consumer_radio_network_idle(activity));
        activity.armed = false;
        activity.running = true;
        assert(!network::consumer_radio_network_idle(activity));
        activity.running = false;
        activity.failed = true;
        assert(!network::consumer_radio_network_idle(activity));
    }
    {
        Test t;
        auto before = t.media.data;
        t.api.admission(false);
        assert(t.start().status == 409);
        t.api.admission(true);
        assert(
            t.api.handle(request("/api/consumer/v1/request", std::string(44, 'x'), true), t.now, 1)
                .status == 401);
        auto cross = request("/api/consumer/v1/start", "{}");
        cross.headers["origin"] = "http://evil";
        assert(t.api.handle(cross, t.now, 2).status == 403);
        cross.headers["origin"] = "http://192.168.4.1";
        cross.headers["host"] = "192.168.1.53";
        assert(t.api.handle(cross, t.now, 3).status == 403);
        assert(t.start().status == 200);
        assert(t.start().status == 409);
        t.now += 30000;
        t.api.poll(t.now);
        assert(!t.api.active(t.now));
        t.login();
        auto config_reply = t.call("GET", "/api/v1/config");
        assert(config_reply.body.find("test-password") == std::string::npos);
        assert(config_reply.body.find("AA0NT") != std::string::npos);
        const auto parsed = wtp::json::parse(config_reply.body);
        const auto revision = parsed->get("etag")->string();
        t.api.finish_request(t.transaction - 1, true);
        auto result = t.call("PUT", "/api/v1/config", config, "\"stale\"");
        assert(result.body.find("revision_conflict") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        auto altered = config;
        altered.replace(altered.find("AA0NT"), 5, "K1ABC");
        result = t.call("PUT", "/api/v1/config", altered, revision);
        assert(result.body.find("consumer_setup_identity_required") != std::string::npos);
        t.api.finish_request(t.transaction - 1, true);
        auto opt = config;
        opt.insert(1, "\"allow_unqualified_frequency\":true,");
        opt.replace(opt.find("\"test-password\""), 15, "null");
        const auto cursor = t.fixture.store.watermark();
        result = t.call("PUT", "/api/v1/config", opt, revision);
        assert(result.body.find("\"status\":200") != std::string::npos);
        assert(t.fixture.store.config()->allow_unqualified_frequency);
        assert(t.fixture.store.watermark() == cursor);
        t.api.finish_request(t.transaction - 1, true);
        assert(t.media.data == before); // Authentication/config does not rewrite commissioning.
        const auto latest = t.fixture.api.revision();
        result = t.call("PUT", "/api/v1/network", "{\"enabled\":false}", latest);
        assert(t.fixture.network.pending == false && t.fixture.network.enabled);
        t.api.finish_request(t.transaction + 5, true);
        assert(t.fixture.network.enabled);
        t.api.finish_request(t.transaction - 1, false);
        assert(t.fixture.network.enabled && !t.fixture.network.pending);
        result = t.call("PUT", "/api/v1/network", "{\"enabled\":false}", t.fixture.api.revision());
        t.api.finish_request(t.transaction - 1, true);
        assert(!t.fixture.network.enabled);
        t.now += network::ConsumerRadioApi::idle_ms;
        assert(!t.api.active(t.now));
    }
    {
        Test t;
        t.login();
        const auto started = t.now;
        t.now = started + 300000;
        assert(t.api.active(t.now)); // The former idle limit no longer closes a login.
        t.now = started + 1800000 - 1;
        assert(t.api.active(t.now));
        ++t.now;
        assert(!t.api.active(t.now));
        t.login();
        const auto fresh = t.now;
        for (std::uint64_t elapsed = 1000000; elapsed < 28800000; elapsed += 1000000) {
            t.now = fresh + elapsed;
            assert(t.call("GET", "/api/v1/status").status == 200);
            t.api.finish_request(t.transaction - 1, true);
        }
        t.now = fresh + 28800000 - 1;
        assert(t.api.active(t.now));
        ++t.now;
        assert(!t.api.active(t.now)); // Authenticated traffic never renews absolute time.
    }
    {
        Test t;
        t.crypto.password_ok = false;
        auto result = t.start();
        assert(result.status == 200);
        auto root = wtp::json::parse(result.body);
        std::array<std::uint8_t, 16> id{};
        assert(network::bootstrap_unhex(root->get("session_id")->string(), id));
        const auto h = network::consumer_radio_header(id, 0);
        std::string packet(h.begin(), h.end());
        packet.resize(44);
        assert(t.api.handle(request("/api/consumer/v1/finish", packet, true), t.now, 1).status ==
               401);
        assert(!t.api.active(t.now));
        assert(t.start().status == 429);
        t.now += 1000;
        t.crypto.password_ok = true;
        t.login();
        t.crypto.tag_ok = false;
        assert(t.call("PUT", "/api/v1/network", "{\"enabled\":false}").status == 401);
        assert(!t.api.active(t.now));
        assert(t.fixture.network.enabled && !t.fixture.network.pending);
    }
    {
        Test t;
        t.login();
        t.call("GET", "/api/v1/status");
        t.api.finish_request(t.transaction - 1, true);
        --t.sequence;
        assert(t.call("GET", "/api/v1/status").status == 401);
        t.now += network::ConsumerRadioApi::absolute_ms;
        assert(!t.api.active(t.now));
        t.login();
        assert(t.store.select(provisioning::ProfileSource::Unprovisioned));
        t.api.poll(t.now);
        assert(!t.api.active(t.now));
    }
}
