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
        return api.handle(r, "test", "127.0.0.1:8443");
    }
    std::string envelope(std::string schema, std::string field, std::string payload) {
        return "{\"schema\":" + quote(schema) + ",\"target\":" +
               application::target(std::string(32, 'a'), f.service.status().boot_id) + "," +
               quote(field) + ":" + payload + "}";
    }
    network::HttpResponse drive(std::string value) {
        return call("PUT", "/api/v1/gpio-drive",
                    envelope("transmitter-gpio-drive/1", "gpio_drive_ma", value));
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
void persistence_and_legacy() {
    for (unsigned value : {2, 4, 8, 12}) {
        Member m;
        REQUIRE(m.drive(std::to_string(value)).status == 200);
        const auto r = m.call("GET", "/api/v1/gpio-drive");
        REQUIRE(r.status == 200);
        const auto v = parse(r.body);
        REQUIRE(v->get("saved")->integer() == int(value));
        REQUIRE(v->get("boot_active")->raw == "4");
        REQUIRE(v->get("pad_readback")->raw == "null");
        REQUIRE(m.call("GET", "/api/v1/config").body.find("gpio_drive_ma") == std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/config/3").body.find("gpio_drive_ma") != std::string::npos);
        REQUIRE(m.drive(value == 2 ? "12" : "2").status == 200);
        auto full = network_test::config;
        full.pop_back();
        full += ",\"gpio_drive_ma\":" + std::to_string(value) + "}";
        REQUIRE(m.call("PUT", "/api/v1/config/3", full).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        REQUIRE(m.drive(value == 2 ? "12" : "2").status == 200);
        auto update = m.envelope("transmitter-config-update/2", "config",
                                 "{\"gpio_drive_ma\":" + std::to_string(value) + "}");
        update.insert(update.size() - 1, ",\"mode\":\"merge\"");
        REQUIRE(m.call("POST", "/api/v1/config/update/3", update).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        REQUIRE(m.call("GET", "/api/v1/hardware").body.find("gpio_drive") == std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/application/3").body.find("transmitter-hardware/2") !=
                std::string::npos);
        REQUIRE(m.call("PUT", "/api/v1/config", network_test::config).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == value);
        auto old_replace =
            m.envelope("transmitter-config-update/1", "config", network_test::config);
        old_replace.insert(old_replace.size() - 1, ",\"mode\":\"replace\"");
        REQUIRE(m.call("POST", "/api/v1/config/update", old_replace).status == 200);
        REQUIRE(m.f.store.config()->gpio_drive_ma == 4);
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
    auto r = request("GET", "/api/v1/gpio-drive");
    auto view = blank.api.handle(r, "test", "127.0.0.1:8443");
    auto v = parse(view.body);
    REQUIRE(v->get("saved")->raw == "null");
    REQUIRE(v->get("boot_active")->raw == "4");
    REQUIRE(v->get("pad_readback")->raw == "null");
    Member m;
    m.api.gpio_drive_observer(+[] { return 8; });
    view = m.call("GET", "/api/v1/gpio-drive");
    REQUIRE(parse(view.body)->get("pad_readback")->raw == "8");
    REQUIRE(parse(view.body)->get("boot_active")->raw == "4");
    m.api.gpio_drive_observer(+[] { return -2; });
    view = m.call("GET", "/api/v1/gpio-drive");
    REQUIRE(parse(view.body)->get("pad_readback")->raw == "null");
    REQUIRE(parse(view.body)->get("application_error")->string() == "pad_application_failed");
    const auto sequence = m.f.store.config_sequence();
    const auto good = m.envelope("transmitter-gpio-drive/1", "gpio_drive_ma", "8");
    for (const auto extra : {",\"unknown\":true", ",\"gpio_drive_ma\":4"}) {
        auto body = good;
        body.insert(body.size() - 1, extra);
        REQUIRE(m.call("PUT", "/api/v1/gpio-drive", body).status == 400);
        REQUIRE(m.f.store.config_sequence() == sequence);
    }
    auto wrong_boot = good;
    const auto boot = m.f.service.status().boot_id;
    wrong_boot.replace(wrong_boot.find(boot), boot.size(), std::string(32, 'f'));
    REQUIRE(m.call("PUT", "/api/v1/gpio-drive", wrong_boot).status == 409);
    REQUIRE(m.f.store.config_sequence() == sequence);
    REQUIRE(m.drive("12").status == 200);
    const auto merge = m.envelope("transmitter-config-update/2", "config",
                                  R"({"wifi":{"ssid":"changed-network"}})");
    auto body = merge;
    body.insert(body.size() - 1, ",\"mode\":\"merge\"");
    REQUIRE(m.call("POST", "/api/v1/config/update/3", body).status == 200);
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
    auto save = [&](std::string fields, bool modern) {
        auto body = m.envelope(modern ? "transmitter-progress/2" : "transmitter-progress/1",
                               "fields", fields);
        body.insert(body.size() - 1, ",\"request_id\":\"11111111111111111111111111111111\"");
        return m.call("POST", modern ? "/api/v1/progress/update/2" : "/api/v1/progress/update",
                      body);
    };
    const auto revision = m.progress.sequence();
    REQUIRE(save(R"({"gpio_drive_ma":8,"locator":"FN42"})", false).status == 400);
    REQUIRE(save(R"({"gpio_drive_ma":null,"locator":"FN42"})", true).status == 400);
    REQUIRE(m.progress.sequence() == revision);
    REQUIRE(save(R"({"gpio_drive_ma":8})", true).status == 200);
    REQUIRE(m.f.store.config()->gpio_drive_ma == 12);
    REQUIRE(parse(m.call("GET", "/api/v1/progress/2").body)->get("matches_applied")->raw ==
            "false");
    REQUIRE(parse(m.call("GET", "/api/v1/progress").body)->get("matches_applied")->raw == "true");
    REQUIRE(m.call("GET", "/api/v1/progress").body.find("gpio_drive_ma") == std::string::npos);
    REQUIRE(m.progress.candidate(m.f.store.config())->gpio_drive_ma == 12);
    REQUIRE(m.progress.candidate(m.f.store.config(), "drive", true)->gpio_drive_ma == 8);
    standalone::Progress loaded(m.progress_flash);
    REQUIRE(loaded.load());
    REQUIRE(loaded.candidate(m.f.store.config(), "drive", true)->gpio_drive_ma == 8);
    auto apply = [&](bool modern, std::string domain) {
        return m.call("POST", modern ? "/api/v1/progress/apply/2" : "/api/v1/progress/apply",
                      m.envelope(modern ? "transmitter-progress/2" : "transmitter-progress/1",
                                 "application",
                                 "{\"domain\":" + quote(domain) + ",\"draft_revision\":" +
                                     quote(std::to_string(m.progress.sequence())) + "}"));
    };
    const auto legacy_apply = apply(false, "all");
    REQUIRE(legacy_apply.status == 200);
    REQUIRE(legacy_apply.body.find("manual_correction_ppb") == std::string::npos);
    REQUIRE(m.f.store.config()->manual_correction_ppb == 1234);
    REQUIRE(m.f.store.config()->ntp_rf_calibration);
    REQUIRE(legacy_apply.body.find("gpio_drive_ma") == std::string::npos);
    REQUIRE(m.f.store.config()->gpio_drive_ma == 12);
    REQUIRE(apply(true, "drive").status == 200);
    REQUIRE(m.f.store.config()->manual_correction_ppb == 1234);
    REQUIRE(m.f.store.config()->ntp_rf_calibration);
    REQUIRE(m.f.store.config()->gpio_drive_ma == 8);
    REQUIRE(parse(m.call("GET", "/api/v1/progress/2").body)->get("matches_applied")->raw == "true");
    m.f.flash.fail = true;
    REQUIRE(m.drive("2").status == 503);
    Member n;
    auto stale = request("PUT", "/api/v1/gpio-drive",
                         n.envelope("transmitter-gpio-drive/1", "gpio_drive_ma", "8"));
    stale.headers["if-match"] = n.api.revision();
    REQUIRE(n.drive("2").status == 200);
    REQUIRE(n.api.handle(stale, "test", "127.0.0.1:8443").status == 412);
    Member busy;
    auto hello = request(
        "POST", "/api/v1/jobs",
        R"({"session_id":"11111111111111111111111111111111","request_id":"44444444444444444444444444444444","operation":"HELLO","body":{"versions":["WTP/1"],"client_name":"drive-test","client_version":"1"}})");
    REQUIRE(busy.api.handle(hello, "test", "127.0.0.1:8443").status == 200);
    auto claim = request(
        "POST", "/api/v1/jobs",
        R"({"session_id":"11111111111111111111111111111111","request_id":"22222222222222222222222222222222","operation":"CLAIM","body":{"owner_id":"33333333333333333333333333333333","lease_ms":30000}})");
    REQUIRE(busy.api.handle(claim, "test", "127.0.0.1:8443").status == 200);
    REQUIRE(busy.drive("8").status == 409);
}
} // namespace
int main(int argc, char**) {
    if (argc == 2) {
        Member m;
        for (unsigned value : {2, 4, 8, 12}) {
            REQUIRE(m.drive(std::to_string(value)).status == 200);
            for (const auto path :
                 {"/api/v1/gpio-drive", "/api/v1/application/3", "/api/v1/progress/2"})
                std::cout << m.call("GET", path).body << '\n';
        }
        return 0;
    }

    validation();
    persistence_and_legacy();
    observations_and_admission();
    drafts_and_failures();
}
