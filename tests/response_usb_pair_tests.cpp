#include "application/resources.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"
#include "rf/stream_engine.hpp"
#include "usb/management_endpoint.hpp"

#include <cassert>
using namespace wsprrypico;
namespace {
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
};
std::string frame(std::string_view payload) {
    std::string result = "UMP1";
    for (int shift : {24, 16, 8, 0})
        result.push_back(static_cast<char>(payload.size() >> shift));
    result += payload;
    return result;
}
} // namespace
int main() {
    Sink sink;
    rf::StreamEngine engine(sink);
    network_test::Fixture f(0, std::string(32, 'a'), &engine);
    network::LocalUsbApi api(f.api);
    bool generated = false;
    unsigned finishes = 0;
    usb::ManagementEndpoint endpoint(
        std::string(32, 'a'), f.service.status().boot_id, "test",
        [&](const network::HttpRequest& r, std::uint64_t transaction) {
            auto response = api.handle(r, transaction);
            generated = bool(response.generated_body);
            return response;
        },
        [&](std::uint64_t transaction, bool delivered) {
            assert(delivered);
            ++finishes;
            api.finish(transaction, delivered);
        });
    const std::string usb_session(32, 'c'), job_session(32, '1');
    const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
    endpoint.connect(usb_session);
    const auto send = [&](std::string text) {
        const auto bytes = frame(text);
        for (const auto byte : bytes) {
            const auto b = static_cast<std::uint8_t>(byte);
            assert(endpoint.receive({&b, 1}, 1) == 1);
        }
    };
    const auto drain = [&]() {
        for (unsigned i = 0; endpoint.output().empty() && i < 65; ++i)
            endpoint.poll(1);
        assert(!endpoint.output().empty() && !endpoint.closed());
        std::string wire;
        while (!endpoint.output().empty()) {
            const auto part = endpoint.output();
            const auto count = std::min<std::size_t>(13, part.size());
            wire.append(reinterpret_cast<const char*>(part.data()), count);
            endpoint.consume_output(count);
        }
        assert(wire.starts_with("UMP1"));
        std::size_t length = 0;
        for (unsigned i = 4; i < 8; ++i)
            length = (length << 8) | static_cast<unsigned char>(wire[i]);
        assert(length == wire.size() - 8 && length <= 65536);
        return wire.substr(8);
    };
    send("{\"schema\":\"usb-management/1\",\"id\":1,\"operation\":\"hello\"}");
    (void)drain();
    unsigned id = 1, job_id = 2000;
    const auto common = [&](std::string_view op) {
        return "{\"schema\":\"usb-management/1\",\"id\":" + std::to_string(id) +
               ",\"operation\":" + wtp::json::quote(op) +
               ",\"session\":" + wtp::json::quote(usb_session) + ",\"target\":" + target;
    };
    const auto command = [&](std::string_view operation, std::string_view body) {
        ++id;
        const auto request =
            "{\"contract\":\"Wsprry-Control/1\",\"session_id\":" + wtp::json::quote(job_session) +
            ",\"request_id\":" + wtp::json::quote(std::string(28, '0') + std::to_string(++job_id)) +
            ",\"operation\":" + wtp::json::quote(operation) + ",\"body\":" + std::string(body) +
            "}";
        send(common("request") +
             ",\"method\":\"POST\",\"path\":\"/api/control/v1/jobs\",\"body\":" +
             wtp::json::quote(request) + ",\"if_match\":\"\"}");
        const auto response = drain();
        const auto root = wtp::json::parse(response);
        assert(root && root->get("status")->integer() == 200);
        const auto logical = root->get("body")->string();
        assert(wtp::json::parse(logical)->get("ok")->boolean());
        const auto before = finishes;
        send(common("ack") + "}");
        (void)drain();
        assert(finishes == before + 1);
        return logical.size();
    };
    command(
        "HELLO",
        R"({"versions":["WTP/1"],"client_name":"USB response regression","client_version":"1"})");
    command("CLAIM", "{\"owner_id\":" + wtp::json::quote(job_session) + ",\"lease_ms\":60000}");
    const auto bytes = command(
        "LOAD_MESSAGE",
        R"({"job_id":"33333333333333333333333333333333","mode":"fskcw","message":"CQ CQ DE AA0NT EM18 QRSS TEST 73","frequency_nhz":"10140005000000000","space_frequency_nhz":"10140000000000000","timing":{"dot_ns":"3000000000","dash_ns":"9000000000","intra_gap_ns":"3000000000","character_gap_ns":"9000000000","word_gap_ns":"21000000000"},"repeat_count":1,"repeat_gap_ns":"3000000000","allow_frequency_adjustment":true})");
    assert(generated && bytes > 4096);
    assert(f.service.status().state == wtp::State::Loaded && !f.service.status().output_active);
    command("ABORT", R"({"job_id":"33333333333333333333333333333333"})");
    command("RELEASE", "{}");
    assert(!f.service.status().owner_id && !f.service.status().output_active);
}
