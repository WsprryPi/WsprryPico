#include "hardware/pins.hpp"
#include "network_support.hpp"
#include "standalone/config.hpp"

#include <cstdlib>
#include <iostream>
using namespace wsprrypico;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " #x "\n";                                                 \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
int main() {
    hardware::PinPlan p;
    CHECK(hardware::validate(p).valid());
    CHECK(hardware::operational(p));
    for (unsigned gp = 0; gp < 48; ++gp) {
        p.button.reset();
        p.rf = gp;
        CHECK(hardware::validate(p).valid() == hardware::eligible(gp));
    }
    p = {};
    p.button.reset();
    p.rf.reset();
    p.engine = hardware::PinPlan::Engine::I2c;
    for (unsigned i = 0; i < hardware::i2c_pairs.size(); ++i) {
        p.i2c_pair = i;
        CHECK(hardware::validate(p).valid());
        CHECK(!hardware::operational(p));
        p.amplifier = hardware::i2c_pairs[i].sda;
        CHECK(!hardware::validate(p).valid());
        p.amplifier = hardware::i2c_pairs[i].scl;
        CHECK(!hardware::validate(p).valid());
        p.amplifier.reset();
    }
    p.i2c_pair = 12;
    CHECK(!hardware::validate(p).valid());
    p = {};
    p.i2c_pair = 0;
    CHECK(!hardware::validate(p).valid());
    p.i2c_pair.reset();
    p.rf.reset();
    CHECK(!hardware::validate(p).valid());
    for (unsigned a = 0; a < 5; ++a)
        for (unsigned b = a + 1; b < 5; ++b) {
            p = {};
            p.button.reset();
            p.rf = 0;
            std::array<std::optional<unsigned>*, 4> roles{&p.rf, &p.button, &p.amplifier,
                                                          &p.indicator_gp};
            if (a < 4)
                *roles[a] = 10;
            else
                p.lpf.push_back(10);
            if (b < 4)
                *roles[b] = 10;
            else
                p.lpf.push_back(10);
            if (p.indicator_gp)
                p.indicator = hardware::PinPlan::Indicator::External;
            CHECK(hardware::validate(p).error == "pin_conflict");
        }
    p = {};
    p.lpf = {3, 3};
    CHECK(!hardware::validate(p).valid());
    p = {};
    p.indicator_gp = 3;
    CHECK(!hardware::validate(p).valid());
    p.indicator = hardware::PinPlan::Indicator::External;
    CHECK(hardware::validate(p).valid());
    const auto text = hardware::serialize_plan(p);
    CHECK(hardware::parse_plan(text) == p);
    for (const auto bad : {"-1", "1.0", "true", "\"2\"", "4294967296", "1e0"}) {
        auto s = text;
        auto at = s.find("\"rf_gp\":2");
        s.replace(at + 8, 1, bad);
        CHECK(!hardware::parse_plan(s));
    }
    CHECK(!hardware::parse_plan(text.substr(0, text.size() - 1) + ",\"rf_gp\":2}"));
    CHECK(!hardware::parse_plan(text.substr(0, text.size() - 1) + ",\"unknown\":2}"));
    p = {};
    auto too_many = hardware::serialize_plan(p);
    auto at = too_many.find("\"lpf_gps\":[]");
    std::string array = "[";
    for (unsigned i = 0; i < 28; ++i)
        array += (i ? ",0" : "0");
    array += ']';
    too_many.replace(at + 10, 2, array);
    CHECK(!hardware::parse_plan(too_many));
    const std::string legacy =
        R"({"version":1,"enabled":false,"station":{"callsign":"K1ABC","locator":"FN42","power_dbm":10},"wifi":{"ssid":"","password":""},"schedules":[]})";
    auto c = standalone::parse_config(legacy);
    CHECK(c);
    CHECK(c->pins == hardware::PinPlan{});
    c->pins.rf = 28;
    c->pins.button = 22;
    c->pins.indicator = hardware::PinPlan::Indicator::External;
    c->pins.indicator_gp = 4;
    CHECK(standalone::parse_config(standalone::serialize_config(*c)) == c);
    c->pins.amplifier = 5;
    CHECK(!standalone::parse_config(standalone::serialize_config(*c)));
    c->pins.amplifier.reset();
    c->pins.rf = 22;
    CHECK(!standalone::parse_config(standalone::serialize_config(*c)));
    network_test::Fixture f;
    auto initial = standalone::parse_config(network_test::config);
    CHECK(initial && f.store.save(*initial));
    standalone::Scheduler scheduler(f.store, f.service);
    network::BrowserApi api(f.service, f.store, scheduler, f.network,
                            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "test");
    auto request = [](std::string method, std::string path, std::string body) {
        return network::HttpRequest{std::move(method),
                                    std::move(path),
                                    std::move(body),
                                    {{"host", "127.0.0.1:8443"},
                                     {"origin", "https://127.0.0.1:8443"},
                                     {"content-type", "application/json"},
                                     {"x-wsprrypico-request", "1"}}};
    };
    auto validate =
        request("POST", "/api/v1/pins/validate", hardware::serialize_plan(hardware::PinPlan{}));
    CHECK(api.handle(validate, "", "127.0.0.1:8443").status == 401);
    const auto flash_before = f.flash.bytes;
    const auto revision_before = api.revision();
    CHECK(api.handle(validate, "test", "127.0.0.1:8443").status == 200);
    CHECK(f.flash.bytes == flash_before && api.revision() == revision_before);
    auto invalid = *initial;
    invalid.pins.rf = 14;
    auto save = request("PUT", "/api/v1/config", standalone::serialize_config(invalid));
    save.headers["if-match"] = api.revision();
    CHECK(api.handle(save, "test", "127.0.0.1:8443").status == 400);
    CHECK(f.flash.bytes == flash_before && f.store.config() == initial);
    auto changed = *initial;
    changed.pins.rf = 28;
    save.body = standalone::serialize_config(changed);
    save.headers["if-match"] = "wrong";
    CHECK(api.handle(save, "test", "127.0.0.1:8443").status == 412);
    save.headers["if-match"] = api.revision();
    CHECK(api.handle(save, "test", "127.0.0.1:8443").status == 200);
    CHECK(scheduler.reboot_required() && scheduler.active_pins().rf == 2);
    CHECK(f.store.config()->pins.rf == 28);
    standalone::Store reloaded(f.flash);
    CHECK(reloaded.load());
    CHECK(reloaded.config()->pins.rf == 28);
    // A later ordinary save cannot conceal the pending pin restart.
    changed.locator = "EM19";
    save.body = standalone::serialize_config(changed);
    save.headers["if-match"] = api.revision();
    CHECK(api.handle(save, "test", "127.0.0.1:8443").status == 200);
    CHECK(scheduler.reboot_required());
    wtp::Request hello;
    hello.operation = "HELLO";
    hello.principal = "test";
    hello.session_id = std::string(32, 'a');
    hello.request_id = std::string(32, 'd');
    hello.payload_digest[0] = 1;
    hello.body = wtp::HelloBody{{"WTP/1"}};
    CHECK(f.service.handle(hello).ok);
    wtp::Request claim;
    claim.operation = "CLAIM";
    claim.principal = "test";
    claim.session_id = std::string(32, 'a');
    claim.request_id = std::string(32, 'b');
    claim.payload_digest[0] = 2;
    claim.body = wtp::ClaimBody{std::string(32, 'c'), 1000};
    const auto inhibited_claim = f.service.handle(claim);
    CHECK(!inhibited_claim.ok &&
          inhibited_claim.error ==
              wtp::ErrorCode::Busy); // Old physical assignment cannot transmit before restart.
    // Unsupported persisted assignment is rejected even when its CRC is valid.
    network_test::Flash media;
    standalone::Journal journal(media, 0, 2048);
    CHECK(journal.load());
    auto unsupported = *initial;
    unsupported.pins.amplifier = 3;
    CHECK(journal.append(standalone::serialize_config(unsupported)));
    standalone::Store bad_store(media);
    CHECK(!bad_store.load());
    CHECK(!bad_store.healthy());
    CHECK(!bad_store.config());
    std::cout << "pin allocation checks passed\n";
}
