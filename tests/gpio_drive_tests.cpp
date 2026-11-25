#include "application/config_update.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"

using namespace wsprrypico;
using namespace execution::json;
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
void station_independent() {
    for (unsigned value : {2, 4, 8, 12}) {
        for (int route = 0; route < 3; ++route)
            for (bool physical_usb : {false, true}) {
                network_test::Fixture f;
                network::LocalUsbApi usb(f.api);
                network_test::Flash draft_flash;
                standalone::Progress progress(draft_flash);
                REQUIRE(progress.load());
                f.api.progress_settings(progress);
                auto call = [&](std::string method, std::string path, std::string body = {}) {
                    auto r = request(method, path, body);
                    r.headers["if-match"] = f.api.revision();
                    return physical_usb ? usb.handle(network_test::control_request(r))
                                        : f.api.handle(network_test::control_request(r), "test",
                                                       "127.0.0.1:8443");
                };
                auto envelope = [&](std::string schema, std::string key, std::string v) {
                    return "{\"schema\":" + quote(schema) + ",\"target\":" +
                           application::target(std::string(32, 'a'), f.service.status().boot_id) +
                           "," + quote(key) + ":" + v + "}";
                };
                auto unrelated = envelope("progress", "fields", R"({"locator":"EM18"})");
                unrelated.insert(unrelated.size() - 1,
                                 ",\"request_id\":\"99999999999999999999999999999999\"");
                REQUIRE(call("POST", "/api/control/v1/progress/update", unrelated).status == 200);
                REQUIRE(call("POST", "/api/control/v1/progress/apply",
                             envelope("progress", "application",
                                      "{\"domain\":\"drive\",\"draft_revision\":" +
                                          quote(std::to_string(progress.sequence())) + "}"))
                            .status == 409);
                REQUIRE(!f.store.config() && !f.store.config_sequence());
                const auto pins = f.scheduler.active_pins();
                network::HttpResponse response;
                if (route == 0)
                    response = call("PUT", "/api/control/v1/gpio-drive",
                                    envelope("gpio-drive", "gpio_drive_ma", std::to_string(value)));
                if (route == 1) {
                    auto body = envelope("config-update", "config",
                                         "{\"gpio_drive_ma\":" + std::to_string(value) + "}");
                    body.insert(body.size() - 1, ",\"mode\":\"merge\"");
                    response = call("POST", "/api/control/v1/config/update", body);
                }
                if (route == 2) {
                    auto body = envelope("progress", "fields",
                                         "{\"gpio_drive_ma\":" + std::to_string(value) +
                                             ",\"locator\":\"FN42\"}");
                    body.insert(body.size() - 1,
                                ",\"request_id\":\"11111111111111111111111111111111\"");
                    REQUIRE(call("POST", "/api/control/v1/progress/update", body).status == 200);
                    REQUIRE(!f.store.config());
                    response = call("POST", "/api/control/v1/progress/apply",
                                    envelope("progress", "application",
                                             "{\"domain\":\"drive\",\"draft_revision\":" +
                                                 quote(std::to_string(progress.sequence())) + "}"));
                }
                if (response.status != 200)
                    std::cerr << response.body_text() << "\n";
                REQUIRE(response.status == 200);
                if (!f.store.config() || f.store.config()->gpio_drive_ma != value)
                    std::cerr << "route=" << route << " value=" << value
                              << " body=" << response.body_text() << "\n";
                REQUIRE(f.store.config() && f.store.config()->gpio_drive_ma == value);
                REQUIRE(f.store.config()->callsign.empty() && f.store.config()->locator.empty());
                REQUIRE(!f.store.config()->enabled && !f.store.message_schedule());
                REQUIRE(f.store.config()->pins == pins);
                REQUIRE(f.scheduler.active_gpio_drive_ma() == 12);
                REQUIRE(f.scheduler.hardware_restart_required() == (value != 12));
                REQUIRE(f.scheduler.reboot_required() == (value != 12));
                auto station = call("GET", "/api/control/v1/station");
                REQUIRE(parse(station.body_view())->get("station")->raw == "null");
                auto read = call("GET", "/api/control/v1/progress");
                REQUIRE(parse(read.body_view())->get("station_complete")->raw == "false");
                REQUIRE(parse(read.body_view())->get("applied_station")->raw == "null");
                const auto before = f.store.config_sequence();
                auto bad = *f.store.config();
                bad.enabled = true;
                REQUIRE(!standalone::parse_config(standalone::serialize_config(bad)));
                bad.enabled = false;
                bad.callsign = "AA0NT";
                REQUIRE(!standalone::parse_config(standalone::serialize_config(bad)));
                REQUIRE(
                    f.scheduler.command("CONFIG " + standalone::serialize_config(*f.store.config()))
                        .find("invalid_station") != std::string::npos);
                REQUIRE(f.store.config_sequence() == before);
                standalone::Store reboot(f.flash);
                REQUIRE(reboot.load());
                standalone::Scheduler boot(reboot, f.service);
                REQUIRE(boot.active_gpio_drive_ma() == value && boot.active_pins() == pins);
                REQUIRE(!boot.hardware_restart_required());
                // Applying a real station later preserves the previously saved RF settings.
                auto station_draft = envelope(
                    "progress", "fields", R"({"callsign":"AA0NT","locator":"EM18","power_dbm":0})");
                station_draft.insert(station_draft.size() - 1,
                                     ",\"request_id\":\"22222222222222222222222222222222\"");
                REQUIRE(call("POST", "/api/control/v1/progress/update", station_draft).status ==
                        200);
                REQUIRE(call("POST", "/api/control/v1/progress/apply",
                             envelope("progress", "application",
                                      "{\"domain\":\"station\",\"draft_revision\":" +
                                          quote(std::to_string(progress.sequence())) + "}"))
                            .status == 200);
                REQUIRE(f.store.config()->callsign == "AA0NT" &&
                        f.store.config()->locator == "EM18");
                REQUIRE(f.store.config()->gpio_drive_ma == value && f.store.config()->pins == pins);
                REQUIRE(!f.store.config()->enabled);
            }
    }
}
void no_wspr_frequency_prerequisite() {
    auto policy = network_test::Fixture::physical_policy();
    policy.maximum_frequency_nhz = 10'000'000'000'000'000ULL;
    network_test::Fixture f(0, std::string(32, 'a'), nullptr, policy);
    auto r = request("PUT", "/api/control/v1/gpio-drive",
                     "{\"schema\":\"gpio-drive\",\"target\":" +
                         application::target(std::string(32, 'a'), f.service.status().boot_id) +
                         ",\"gpio_drive_ma\":8}");
    r.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(r), "test", "127.0.0.1:8443").status == 200);
    REQUIRE(f.store.config()->gpio_drive_ma == 8 && !f.store.config()->enabled);
}
void first_write_failure() {
    network_test::Fixture f;
    auto put = request("PUT", "/api/control/v1/gpio-drive",
                       "{\"schema\":\"gpio-drive\",\"target\":" +
                           application::target(std::string(32, 'a'), f.service.status().boot_id) +
                           ",\"gpio_drive_ma\":8}");
    put.headers["if-match"] = f.api.revision();
    f.flash.fail = true;
    REQUIRE(f.api.handle(network_test::control_request(put), "test", "127.0.0.1:8443").status ==
            503);
    REQUIRE(!f.store.config() && !f.store.healthy());
    put.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(put), "test", "127.0.0.1:8443").status ==
            503);
    REQUIRE(!f.store.config() && !f.store.config_sequence());
}
void validation() {
    REQUIRE(standalone::factory_config().gpio_drive_ma == 12);
    auto c = *standalone::parse_config(network_test::config);
    REQUIRE(c.gpio_drive_ma == 4);
    const auto old = standalone::serialize_config(c);
    REQUIRE(old.find("gpio_drive_ma") == std::string::npos);
    for (unsigned value : {2, 4, 8, 12}) {
        c.gpio_drive_ma = value;
        const auto encoded = standalone::serialize_config(c);
        REQUIRE(standalone::parse_config(encoded)->gpio_drive_ma == value);
    }
    for (const auto bad :
         {"0",    "1",     "-1",   "3",     "5",   "6",          "7",
          "9",    "10",    "11",   "13",    "16",  "4294967296", "18446744073709551616",
          "true", "false", "null", "\"4\"", "4.0", "4.5",        "4e0",
          "04",   "+4",    "-0"}) {
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
        const auto v = parse(r.body_view());
        REQUIRE(v->get("saved")->integer() == int(value));
        REQUIRE(v->get("boot_active")->raw == "4");
        REQUIRE(v->get("pad_readback")->raw == "null");
        REQUIRE(m.call("GET", "/api/control/v1/config").body_text().find("gpio_drive_ma") != std::string::npos);
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
        REQUIRE(m.call("GET", "/api/control/v1/application").body_text().find("hardware") !=
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
    auto v = parse(view.body_view());
    REQUIRE(v->get("saved")->raw == "null");
    REQUIRE(v->get("boot_active")->raw == "12");
    REQUIRE(v->get("pad_readback")->raw == "null");
    Member m;
    m.api.gpio_drive_observer(+[] { return 8; });
    view = m.call("GET", "/api/control/v1/gpio-drive");
    REQUIRE(parse(view.body_view())->get("pad_readback")->raw == "8");
    REQUIRE(parse(view.body_view())->get("boot_active")->raw == "4");
    m.api.gpio_drive_observer(+[] { return -2; });
    view = m.call("GET", "/api/control/v1/gpio-drive");
    REQUIRE(parse(view.body_view())->get("pad_readback")->raw == "null");
    REQUIRE(parse(view.body_view())->get("application_error")->string() == "pad_application_failed");
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
    REQUIRE(parse(read.body_view())->get("fields")->get("gpio_drive_ma")->integer()==8);
    REQUIRE(parse(read.body_view())->get("matches_applied")->raw=="false");
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
    REQUIRE(network_test::internal_command(busy.f.service,"HELLO",execution::HelloBody{{"native-execution/1"}}).ok);
    REQUIRE(network_test::internal_command(busy.f.service,"CLAIM",execution::ClaimBody{std::string(32,'3'),30000}).ok);
    REQUIRE(busy.drive("8").status == 409);
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--station-free-samples") {
        for (unsigned drive : {2, 4, 8, 12}) {
            network_test::Fixture f;
            auto put =
                request("PUT", "/api/control/v1/gpio-drive",
                        "{\"schema\":\"gpio-drive\",\"target\":" +
                            application::target(std::string(32, 'a'), f.service.status().boot_id) +
                            ",\"gpio_drive_ma\":" + std::to_string(drive) + "}");
            put.headers["if-match"] = f.api.revision();
            REQUIRE(
                f.api.handle(network_test::control_request(put), "test", "127.0.0.1:8443").status ==
                200);
            std::cout << f.api
                             .handle(network_test::control_request(
                                         request("GET", "/api/control/v1/config")),
                                     "test", "127.0.0.1:8443")
                             .body_text()
                      << '\n';
        }
        return 0;
    }
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

    no_wspr_frequency_prerequisite();
    first_write_failure();
    station_independent();
    validation();
    current_persistence();
    observations_and_admission();
    drafts_and_failures();
}
