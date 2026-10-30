#include "application/config_update.hpp"
#include "network_support.hpp"

using namespace wsprrypico;
using namespace wtp::json;
namespace {
network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    return {method,
            path,
            body,
            {{"host", "127.0.0.1:8443"},
             {"origin", "https://127.0.0.1:8443"},
             {"content-type", "application/json"},
             {"x-wsprrypico-request", "1"}}};
}
struct Member {
    network_test::Fixture f;
    standalone::Store& init() {
        REQUIRE(f.store.save(*standalone::parse_config(network_test::config)));
        return f.store;
    }
    standalone::Scheduler scheduler{init(), f.service};
    network::BrowserApi api{f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test"};
    network_test::Flash progress_flash;
    standalone::Progress progress{progress_flash};
    Member() {
        REQUIRE(progress.load());
        api.progress_settings(progress);
    }
    network::HttpResponse call(std::string method, std::string path, std::string body = {}) {
        auto r = request(method, path, body);
        r.headers["if-match"] = api.revision();
        return api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    }
    std::string envelope(std::string schema, std::string field, std::string payload) {
        return "{\"schema\":" + quote(schema) + ",\"target\":" +
               application::target(std::string(32, 'a'), f.service.status().boot_id) + "," +
               quote(field) + ":" + payload + "}";
    }
    network::HttpResponse drive(std::string value) {
        return call("PUT", "/api/control/v1/gpio-drive",
                    envelope("gpio-drive", "gpio_drive_ma", value));
    }
};
void validation() {
    auto c = *standalone::parse_config(network_test::config);
    REQUIRE(c.gpio_drive_ma == 4);
    const auto old = standalone::serialize_config(c);
    REQUIRE(old.find("gpio_drive_ma") == std::string::npos);
    for (unsigned value : {2, 4, 8, 12}) {
        c.gpio_drive_ma = value;
        const auto encoded = standalone::serialize_config(c);
        REQUIRE(standalone::parse_config(encoded)->gpio_drive_ma == value);
    }
    for (const auto bad : {"0", "-1", "3", "6", "16", "true", "false", "null", "\"4\"", "4.0",
                           "4e0", "04", "+4", "-0"}) {
        Member m;
        auto text = old;
        text.pop_back();
        text += ",\"gpio_drive_ma\":" + std::string(bad) + "}";
        REQUIRE(!standalone::parse_config(text));
        const auto seq = m.f.store.config_sequence();
        REQUIRE(m.drive(bad).status == 400);
        REQUIRE(m.f.store.config_sequence() == seq);
    }
    auto duplicate = old;
    duplicate.pop_back();
    duplicate += R"(,"gpio_drive_ma":8,"gpio_drive_ma":4})";
    REQUIRE(!standalone::parse_config(duplicate));
}
void current_persistence() {
    for (unsigned value : {2, 4, 8, 12}) {
        Member m;
        REQUIRE(m.drive(std::to_string(value)).status == 200);
        const auto r = m.call("GET", "/api/control/v1/gpio-drive");
        REQUIRE(r.status == 200);
        const auto v = parse(r.body);
        REQUIRE(v->get("saved")->integer() == int(value));
        REQUIRE(v->get("boot_active")->raw == "4");
        REQUIRE(v->get("pad_readback")->raw == "null");
        REQUIRE(m.call("GET", "/api/control/v1/config").body.find("gpio_drive_ma") != std::string::npos);
        REQUIRE(m.drive(value == 2 ? "12" : "2").status == 200);
        auto full = network_test::config;
        full.pop_back();
        full += ",\"gpio_drive_ma\":" + std::to_string(value) + "}";
        REQUIRE(m.call("POST", "/api/control/v1/config/update", network_test::configuration_update(full)).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        REQUIRE(m.drive(value == 2 ? "12" : "2").status == 200);
        auto update = m.envelope("config-update", "config",
                                 "{\"gpio_drive_ma\":" + std::to_string(value) + "}");
        update.insert(update.size() - 1, ",\"mode\":\"merge\"");
        REQUIRE(m.call("POST", "/api/control/v1/config/update", update).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        REQUIRE(m.call("GET", "/api/control/v1/application").body.find("hardware") !=
                std::string::npos);
        REQUIRE(m.call("POST", "/api/control/v1/config/update", network_test::configuration_update(network_test::config)).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        auto old_replace =
            m.envelope("config-update", "config", network_test::config);
        old_replace.insert(old_replace.size() - 1, ",\"mode\":\"replace\"");
        REQUIRE(m.call("POST", "/api/control/v1/config/update", old_replace).status == 400);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        REQUIRE(m.drive(std::to_string(value)).status == 200);
        standalone::Store rebooted(m.f.flash);
        REQUIRE(rebooted.load());
        REQUIRE(rebooted.config()->gpio_drive_ma == value);
        standalone::Scheduler boot(rebooted, m.f.service);
        REQUIRE(boot.active_gpio_drive_ma() == value);
        REQUIRE(m.drive("4").status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == 4);
        if (value != 4)
            REQUIRE(m.scheduler.hardware_restart_required()); // A/B/A sticky
        REQUIRE(m.scheduler.command("CONFIG " + network_test::config).find("\"ok\":true") !=
                std::string::npos);
        REQUIRE(m.f.store.config()->gpio_drive_ma == 4);
    }
}
void observations_and_admission() {
    // A boot selection is never presented as an SDK observation.
    network_test::Fixture blank;
    auto r = request("GET", "/api/control/v1/gpio-drive");
    auto view = blank.api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    auto v = parse(view.body);
    REQUIRE(v->get("saved")->raw == "null");
    REQUIRE(v->get("boot_active")->raw == "4");
    REQUIRE(v->get("pad_readback")->raw == "null");
    Member m;
    m.api.gpio_drive_observer(+[] { return 8; });
    view = m.call("GET", "/api/control/v1/gpio-drive");
    REQUIRE(parse(view.body)->get("pad_readback")->raw == "8");
    REQUIRE(parse(view.body)->get("boot_active")->raw == "4");
    m.api.gpio_drive_observer(+[] { return -2; });
    view = m.call("GET", "/api/control/v1/gpio-drive");
    REQUIRE(parse(view.body)->get("pad_readback")->raw == "null");
    REQUIRE(parse(view.body)->get("application_error")->string() == "pad_application_failed");
    const auto sequence = m.f.store.config_sequence();
    const auto good = m.envelope("gpio-drive", "gpio_drive_ma", "8");
    for (const auto extra : {",\"unknown\":true", ",\"gpio_drive_ma\":4"}) {
        auto body = good;
        body.insert(body.size() - 1, extra);
        REQUIRE(m.call("PUT", "/api/control/v1/gpio-drive", body).status == 400);
        REQUIRE(m.f.store.config_sequence() == sequence);
    }
    auto wrong_boot = good;
    const auto boot = m.f.service.status().boot_id;
    wrong_boot.replace(wrong_boot.find(boot), boot.size(), std::string(32, 'f'));
    REQUIRE(m.call("PUT", "/api/control/v1/gpio-drive", wrong_boot).status == 409);
    REQUIRE(m.f.store.config_sequence() == sequence);
    REQUIRE(m.drive("12").status == 200);
    const auto merge = m.envelope("config-update", "config",
                                  R"({"wifi":{"ssid":"changed-network"}})");
    auto body = merge;
    body.insert(body.size() - 1, ",\"mode\":\"merge\"");
    REQUIRE(m.call("POST", "/api/control/v1/config/update", body).status == 200);
    REQUIRE(m.f.store.config()->gpio_drive_ma == 12);
    REQUIRE(m.scheduler.hardware_restart_required());
}
void drafts_and_failures() {
    Member m;
    auto calibration = *m.f.store.config();
    calibration.manual_correction_ppb = 1234;
    calibration.ntp_rf_calibration = true;
    REQUIRE(m.f.store.save(calibration));
    REQUIRE(m.drive("12").status == 200);
    auto save = [&](std::string fields) {
        auto body=m.envelope("progress","fields",fields);
        body.insert(body.size()-1,",\"request_id\":\"11111111111111111111111111111111\"");
        return m.call("POST","/api/control/v1/progress/update",body);
    };
    const auto revision=m.progress.sequence();
    REQUIRE(save(R"({"gpio_drive_ma":null})").status==400);
    REQUIRE(m.progress.sequence()==revision);
    REQUIRE(save(R"({"gpio_drive_ma":8,"locator":"FN42"})").status==200);
    REQUIRE(m.f.store.config()->gpio_drive_ma==12);
    const auto read=m.call("GET","/api/control/v1/progress");
    REQUIRE(parse(read.body)->get("fields")->get("gpio_drive_ma")->integer()==8);
    REQUIRE(parse(read.body)->get("matches_applied")->raw=="false");
    auto apply=m.envelope("progress","application","{\"domain\":\"drive\",\"draft_revision\":"+
        quote(std::to_string(m.progress.sequence()))+"}");
    REQUIRE(m.call("POST","/api/control/v1/progress/apply",apply).status==200);
    REQUIRE(m.f.store.config()->gpio_drive_ma==8 && m.f.store.config()->manual_correction_ppb==1234);
    REQUIRE(m.f.store.config()->ntp_rf_calibration);
    m.f.flash.fail=true;
    REQUIRE(m.drive("2").status==503);
    Member n;
    auto stale = request("PUT", "/api/control/v1/gpio-drive",
                         n.envelope("gpio-drive", "gpio_drive_ma", "8"));
    stale.headers["if-match"] = n.api.revision();
    REQUIRE(n.drive("2").status == 200);
    REQUIRE(n.api.handle(network_test::control_request(stale), "test", "127.0.0.1:8443").status == 412);
    Member busy;
    auto hello = request(
        "POST", "/api/control/v1/jobs",
        R"({"session_id":"11111111111111111111111111111111","request_id":"44444444444444444444444444444444","operation":"HELLO","body":{"versions":["WTP/1"],"client_name":"drive-test","client_version":"1"}})");
    REQUIRE(busy.api.handle(network_test::control_request(hello), "test", "127.0.0.1:8443").status == 200);
    auto claim = request(
        "POST", "/api/control/v1/jobs",
        R"({"session_id":"11111111111111111111111111111111","request_id":"22222222222222222222222222222222","operation":"CLAIM","body":{"owner_id":"33333333333333333333333333333333","lease_ms":30000}})");
    REQUIRE(busy.api.handle(network_test::control_request(claim), "test", "127.0.0.1:8443").status == 200);
    REQUIRE(busy.drive("8").status == 409);
}
} // namespace
int main(int argc, char**) {
    if (argc == 2) {
        Member m;
        for (unsigned value : {2, 4, 8, 12}) {
            REQUIRE(m.drive(std::to_string(value)).status == 200);
            for (const auto path :
                 {"/api/control/v1/gpio-drive", "/api/control/v1/application", "/api/control/v1/progress"})
                std::cout << m.call("GET", path).body << '\n';
        }
        return 0;
    }

    validation();
    current_persistence();
    observations_and_admission();
    drafts_and_failures();
}
