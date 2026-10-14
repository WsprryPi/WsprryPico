#include "network/bootstrap_codec.hpp"
#include "network/consumer_radio.hpp"
#include "network_support.hpp"
#include "provisioning/consumer_profile.hpp"
#include "wtp/json.hpp"

#include <cassert>
using namespace wsprrypico;
using namespace network_test;
namespace {
constexpr auto device = "11111111111111111111111111111111";
constexpr auto boot = "22222222222222222222222222222222";
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
    std::optional<network::HttpResponse>
    seal(wtp::InputView text, const network::ConsumerRadioBinding&, std::uint64_t) override {
        return network::HttpResponse{200, std::string(text), "application/json", {}};
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
    Crypto crypto;
    network::ConsumerRadioApi api{fixture.api, store, runtime, random, crypto, device, boot};
    std::uint64_t now = 1000, sequence = 1, transaction = 100;
    Test() {
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
        assert(store.select(provisioning::ProfileSource::ConsumerProfile,
                            provisioning::serialize_consumer_profile(profile)));
        assert(runtime.load(store, device, provisioning::BuildBundleState::Absent));
        fixture.api.consumer_config(runtime);
        assert(fixture.scheduler.command("CONFIG " + config).find("true") != std::string::npos);
        api.admission(true);
        assert(fixture.store.reserve(1791970000000000000ULL));
    }
    network::HttpResponse start() {
        return api.handle(
            request(
                "/api/consumer/v1/start",
                R"({"version":1,"device_id":"11111111111111111111111111111111","boot_id":"22222222222222222222222222222222","generation":"1","public_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","nonce":"00000000000000000000000000000000"})"),
            now, transaction++);
    }
    void login() {
        auto result = start();
        assert(result.status == 200);
        const auto root = wtp::json::parse(result.body);
        std::array<std::uint8_t, 16> session{};
        assert(network::bootstrap_unhex(root->get("session_id")->string(), session));
        auto h = network::consumer_radio_header(session, 0);
        std::string packet(h.begin(), h.end());
        packet.resize(44);
        assert(api.handle(request("/api/consumer/v1/finish", packet, true), now, transaction++)
                   .status == 200);
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
        return api.handle(request("/api/consumer/v1/request", packet, true), now, transaction++);
    }
};
} // namespace
int main() {
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
        t.now += 300000;
        assert(!t.api.active(t.now));
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
