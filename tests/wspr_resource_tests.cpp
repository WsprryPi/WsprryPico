#include "application/resources.hpp"
#include "network_support.hpp"
#include "wtp/json.hpp"
using namespace wsprrypico;
network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    return {std::move(method),
            std::move(path),
            std::move(body),
            {{"host", "127.0.0.1:8443"},
             {"origin", "https://127.0.0.1:8443"},
             {"content-type", "application/json"},
             {"x-wsprrypico-request", "1"}}};
}
int main(int argc, char**) {
    std::string samples = "{";
    network_test::Fixture f;
    auto original = *standalone::parse_config(network_test::config);
    original.allow_unqualified_frequency = original.allow_non_amateur_frequency = true;
    REQUIRE(f.store.save(original) && f.store.reserve(100));
    const auto call = [&](network::HttpRequest r) {
        return f.api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    };
    REQUIRE(call(request("GET", "/api/control/v1/capabilities")).body.find("application_resources") !=
            std::string::npos);
    for (const auto callsign :
         {"AA0NT", "AA0NT/12", "<AA0NT>", "<AA0NT/12>", "PJ4/AA0NT", "W1A/AA0NT", "<W1A/AA0NT>"}) {
        const std::string station = "{\"callsign\":" + wtp::json::quote(callsign) +
                                    ",\"locator\":\"EM18IG\",\"power_dbm\":37}";
        const auto before = f.api.revision();
        const auto sequence = f.store.config_sequence();
        auto preview = call(request("POST", "/api/control/v1/wspr-plan", station));
        REQUIRE(preview.status == 200 &&
                wtp::json::parse(preview.body)->get("supported")->boolean());
        REQUIRE(f.api.revision() == before && f.store.config_sequence() == sequence);
        auto r = request("PUT", "/api/control/v1/station",
                         "{\"schema\":\"station\",\"target\":" +
                             application::target(std::string(32, 'a'), f.service.status().boot_id) +
                             ",\"station\":" + station + '}');
        r.headers["if-match"] = before;
        const auto saved = call(r);
        REQUIRE(saved.status == 200 &&
                saved.body.find("station") != std::string::npos);
        REQUIRE(saved.body.find(callsign) != std::string::npos);
        auto extended = call(request("GET", "/api/control/v1/application"));
        const auto body = wtp::json::parse(extended.body);
        REQUIRE(extended.status == 200 && body && extended.body.size() <= 4096);
        REQUIRE(body->get("capabilities")->get("station_encoding")->string() ==
                "wspr_type123_auto");
        REQUIRE(body->get("wspr_plan")->get("supported")->boolean());
        if (samples.size() > 1)
            samples += ',';
        samples += wtp::json::quote(callsign) + ':' + extended.body;
        REQUIRE(call(request("GET", "/api/control/v1/application")).status ==
                200U);
        standalone::Store reboot(f.flash);
        REQUIRE(reboot.load() && reboot.config()->callsign == callsign &&
                reboot.config()->locator == "EM18IG");
        REQUIRE(reboot.config()->pins == original.pins &&
                reboot.config()->password == original.password);
        REQUIRE(reboot.config()->allow_unqualified_frequency &&
                reboot.config()->allow_non_amateur_frequency);
        REQUIRE(reboot.watermark() == 100);
    }
    for (const auto station : {R"({"callsign":"<AA0NT>","locator":"EM18","power_dbm":37})",
                               R"({"callsign":"AA0NT/ABC","locator":"EM18IG","power_dbm":37})",
                               R"({"callsign":"AA0NT","locator":"EM18IG","power_dbm":"37"})",
                               R"({"callsign":"AA0NT","locator":"EM18IG","power_dbm":3.7})"}) {
        const auto before = *f.store.config();
        const auto revision = f.api.revision();
        const auto preview = call(request("POST", "/api/control/v1/wspr-plan", station));
        REQUIRE(preview.status == 400 ||
                preview.body.find("\"supported\":false") != std::string::npos);
        auto invalid =
            request("PUT", "/api/control/v1/station",
                    "{\"schema\":\"station\",\"target\":" +
                        application::target(std::string(32, 'a'), f.service.status().boot_id) +
                        ",\"station\":" + station + '}');
        invalid.headers["if-match"] = revision;
        REQUIRE(call(invalid).status == 400);
        REQUIRE(*f.store.config() == before && f.api.revision() == revision &&
                f.store.watermark() == 100);
    }
    if (argc > 1) {
        std::cout << samples << "}\n";
        return 0;
    }
    std::cout
        << "Versioned WSPR resources, preview, strict refusal and durable preservation passed\n";
}
