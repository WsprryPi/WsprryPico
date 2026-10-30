#include "application/resources.hpp"
#include "network/control.hpp"
#include "network_support.hpp"
#include "standalone/progress.hpp"
#include "wtp/sha256.hpp"
using namespace wsprrypico;

namespace {
network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    return {std::move(method), std::move(path), std::move(body),
            {{"host", "127.0.0.1:8443"}, {"origin", "https://127.0.0.1:8443"},
             {"content-type", "application/json"}, {"x-wsprrypico-request", "1"}}};
}
void envelope_admission() {
    for (const auto body : {R"({"contract":"Wsprry-Control/1","x":{"contract":"nested"}})",
                            R"({"x":{"contract":"nested"},"contract":"Wsprry-Control/1"})",
                            R"({"x":[1,2],"contr\u0061ct":"Wsprry-Control/1","y":false})"}) {
        const auto payload = network::control_payload(wtp::InputView(body));
        REQUIRE(payload && wtp::json::parse(*payload));
        REQUIRE(!wtp::json::parse(*payload)->get("contract"));
        REQUIRE(wtp::json::parse(*payload)->get("x"));
    }
    for (const auto body : {R"({})", R"([])", R"({"contract":1})",
                            R"({"contract":"Wsprry-Control/2"})",
                            R"({"contract":"Wsprry-Control/1","contract":"Wsprry-Control/1"})",
                            R"({"contract":"Wsprry-Control/1","x":1,"x":2})"})
        REQUIRE(!network::control_payload(wtp::InputView(body)));
    const auto empty = network::control_payload(wtp::InputView(R"({"contract":"Wsprry-Control/1"})"));
    REQUIRE(empty && *empty == "{}");
    network::HttpResponse response;
    const std::string body = "{\"value\":\"" + std::string(4200, 'x') + "\"}";
    REQUIRE(response.buffered_body.reserve(body.size()));
    REQUIRE(response.buffered_body.append(std::span(reinterpret_cast<const std::uint8_t*>(body.data()), body.size())));
    response = network::control_response(std::move(response));
    const auto parsed = wtp::json::parse(response.buffered_body.view());
    REQUIRE(parsed && parsed->get("contract")->string() == network::control_contract);
    REQUIRE(parsed->get("value")->string() == std::string(4200, 'x'));
}
void exact_progress_receipts() {
    network_test::Fixture f;
    network_test::Flash draft_flash;
    standalone::Progress progress(draft_flash);
    REQUIRE(progress.load());
    f.api.progress_settings(progress);
    const auto wire = std::string("  {\"contract\":\"Wsprry-Control/1\",\"schema\":\"progress\",\"target\":") +
        application::target(std::string(32, 'a'), f.service.status().boot_id) +
        ",\"request_id\":\"11111111111111111111111111111111\",\"fields\":{\"callsign\":\"AA0NT\"}}  ";
    const auto digest = wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(wire.data()), wire.size()));
    std::string expected;
    for (const auto byte : digest) {
        expected += "0123456789abcdef"[byte >> 4];
        expected += "0123456789abcdef"[byte & 15];
    }
    auto r = request("POST", "/api/control/v1/progress/update", wire);
    r.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(r, "test", "127.0.0.1:8443").status == 200);
    REQUIRE(progress.receipt() == wtp::json::quote(expected));
    // Commissioning uses the same synchronous save path after decrypting and
    // stripping the envelope. A copied request borrows this stack view only
    // until save_progress returns; exact original bytes remain the receipt input.
    const wtp::InputView original_wire(wire);
    r.body = *network::control_payload(original_wire);
    r.control_wire_body = &original_wire;
    r.headers["if-match"] = f.api.revision();
    const auto copied = r;
    REQUIRE(f.api.save_progress(copied, true).status == 200);
    REQUIRE(progress.receipt() == wtp::json::quote(expected));
}
void current_hardware_and_refusals() {
    network_test::Fixture f;
    const auto config = standalone::parse_config(network_test::config);
    REQUIRE(config && f.store.load() && f.store.save(*config));
    standalone::Scheduler scheduler(f.store, f.service);
    network::BrowserApi api(f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test");
    const auto call = [&](network::HttpRequest r) { return api.handle(r, "test", "127.0.0.1:8443"); };
    const auto original = *f.store.config();
    REQUIRE(call(request("GET", "/api/v1/application")).status == 404);
    REQUIRE(call(request("GET", "/api/control/v1/application/4")).status == 404);
    const auto app = call(request("GET", "/api/control/v1/application"));
    REQUIRE(app.status == 200);
    const auto document = wtp::json::parse(app.body);
    REQUIRE(document && document->get("contract")->string() == network::control_contract);
    REQUIRE(document->get("schema")->string() == "application");
    REQUIRE(document->get("hardware")->get("schema")->string() == "hardware");
    auto pins = original.pins;
    pins.amplifier = 10;
    pins.amplifier_active_high = false;
    const auto payload = std::string(R"({"contract":"Wsprry-Control/1","schema":"hardware","target":)") +
                         application::target(std::string(32, 'a'), f.service.status().boot_id) +
                         ",\"pins\":" + hardware::serialize_plan(pins, true) + "}";
    auto write = request("PUT", "/api/control/v1/hardware", payload);
    write.headers["if-match"] = "\"stale\"";
    REQUIRE(call(write).status == 412);
    REQUIRE(f.store.config()->pins == original.pins);
    write.headers["if-match"] = api.revision();
    const auto saved = call(write);
    REQUIRE(saved.status == 200);
    REQUIRE(f.store.config()->pins == pins);
    REQUIRE(f.store.config()->gpio_drive_ma == original.gpio_drive_ma);
    REQUIRE(f.store.config()->amplifier_timing == original.amplifier_timing);
    REQUIRE(scheduler.hardware_restart_required());
    auto no_contract = write;
    no_contract.body = R"({"schema":"hardware","pins":{}})";
    REQUIRE(call(no_contract).status == 400);
    REQUIRE(f.store.config()->pins == pins);
    REQUIRE(call(request("PUT", "/api/control/v1/config", "{}")).status == 405);
    auto padded = request("POST", "/api/control/v1/config/update",
        std::string(2048, ' ') + R"({"contract":"Wsprry-Control/1","schema":"config-update"})");
    REQUIRE(call(padded).status == 413);
    REQUIRE(f.store.config()->pins == pins);

}
}
int main(int argc, char**) {
    envelope_admission(); exact_progress_receipts(); current_hardware_and_refusals();
    if (argc > 1) {
        network_test::Fixture f;
        const auto config = standalone::parse_config(network_test::config);
        REQUIRE(config && f.store.load() && f.store.save(*config));
        standalone::Scheduler scheduler(f.store, f.service);
        network::BrowserApi api(f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test");
        for (const auto resource : {"capabilities", "config", "status", "management"}) {
            const auto response = api.handle(request("GET", std::string(network::control_prefix) + resource), "test", "127.0.0.1:8443");
            REQUIRE(response.status == 200);
            std::cout << response.body << '\n';
        }
    }
}
