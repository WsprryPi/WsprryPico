#include "application/config_update.hpp"
#include "hardware/gpio.h"
#include "hardware/pico/amplifier_output.hpp"
#include "network_support.hpp"

using namespace wsprrypico;
using namespace wtp::json;
namespace {
std::vector<std::string> gpio_calls;
bool levels[30]{}, directions[30]{};
bool mismatch = false, wrong_function = false;
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
    network::HttpResponse save(const hardware::PinPlan& p) {
        return call("PUT", "/api/v1/hardware/3",
                    envelope("transmitter-hardware/3", "pins", hardware::serialize_plan(p, true)));
    }
};
void timing_management() {
    Member m;
    const auto path = "/api/v1/amplifier-timing";
    const auto initial = m.call("GET", path);
    auto read = parse(initial.body);
    REQUIRE(read && read->get("saved")->get("lead_ms")->raw == "200");
    REQUIRE(read->get("saved")->get("tail_ms")->raw == "200");
    const auto sequence = m.f.store.config_sequence();
    for (const auto bad :
         {"-1", "0.1", "1e2", "null", "true", "\"200\"", "1001", "4294967296", "{}", "[]"}) {
        REQUIRE(m.call("PUT", path,
                       m.envelope("transmitter-amplifier-timing/1", "timing",
                                  "{\"lead_ms\":" + std::string(bad) + ",\"tail_ms\":200}"))
                    .status == 400);
        REQUIRE(m.f.store.config_sequence() == sequence);
    }
    REQUIRE(m.call("PUT", path,
                   m.envelope("transmitter-amplifier-timing/2", "timing",
                              "{\"lead_ms\":0,\"tail_ms\":0}"))
                .status == 400);
    for (const auto payload :
         {"{}", "{\"lead_ms\":0}", "{\"lead_ms\":0,\"tail_ms\":0,\"extra\":0}"})
        REQUIRE(m.call("PUT", path, m.envelope("transmitter-amplifier-timing/1", "timing", payload))
                    .status == 400);
    const auto body =
        m.envelope("transmitter-amplifier-timing/1", "timing", "{\"lead_ms\":0,\"tail_ms\":1000}");
    auto stale = request("PUT", path, body);
    stale.headers["if-match"] = "\"stale\"";
    REQUIRE(m.api.handle(stale, "test", "127.0.0.1:8443").status == 412);
    auto wrong = body;
    wrong.replace(wrong.find(std::string(32, 'a')), 32, std::string(32, 'b'));
    REQUIRE(m.call("PUT", path, wrong).status == 409);
    REQUIRE(m.f.store.config_sequence() == sequence);
    REQUIRE(m.call("PUT", path, body).status == 200);
    REQUIRE(m.f.store.config()->amplifier_timing == (rf::AmplifierTiming{0, 1000}));
    REQUIRE(m.scheduler.hardware_restart_required() && m.f.service.output_inhibited());
    REQUIRE(m.scheduler.active_amplifier_timing() == rf::AmplifierTiming{});
    REQUIRE(m.call("GET", "/api/v1/config/4").body.find("amplifier_timing") == std::string::npos);
    auto previous = m.f.store.config();
    for (const auto mode : {application::ConfigWrite::Merge, application::ConfigWrite::Replace}) {
        const auto input =
            mode == application::ConfigWrite::Merge ? "{\"enabled\":false}" : network_test::config;
        auto candidate = application::config_candidate(*parse(input), previous, mode, true, true);
        REQUIRE(candidate && standalone::parse_config(*candidate)->amplifier_timing ==
                                 previous->amplifier_timing);
    }
    standalone::Store rebooted(m.f.flash);
    REQUIRE(rebooted.load() && rebooted.config()->amplifier_timing == previous->amplifier_timing);
    REQUIRE(m.call("PUT", path,
                   m.envelope("transmitter-amplifier-timing/1", "timing",
                              "{\"lead_ms\":200,\"tail_ms\":200}"))
                .status == 200);
    REQUIRE(m.scheduler.hardware_restart_required()); // A/B/A cannot clear the latch.
}
void pins_and_adapter() {
    hardware::PinPlan p;
    const auto canonical = hardware::serialize_plan(p);
    REQUIRE(canonical.find("amplifier_active_high") == std::string::npos);
    gpio_calls.clear();
    hardware::PicoAmplifierOutput disabled(p);
    REQUIRE(disabled.initialize_inactive() && disabled.write(true) && disabled.write(false));
    REQUIRE(gpio_calls.empty());
    for (const bool high : {true, false}) {
        p.amplifier = 18;
        p.amplifier_active_high = high;
        REQUIRE(hardware::operational(p));
        REQUIRE(hardware::parse_plan(hardware::serialize_plan(p)) == p);
        gpio_calls.clear();
        hardware::PicoAmplifierOutput output(p);
        REQUIRE(!output.write(true) && gpio_calls.empty());
        REQUIRE(output.initialize_inactive());
        REQUIRE(gpio_calls ==
                std::vector<std::string>({"input 18", "put 18 0", "sio 18",
                                          std::string("put 18 ") + (high ? "0" : "1"), "out 18",
                                          std::string("put 18 ") + (high ? "0" : "1")}));
        REQUIRE(levels[18] == !high);
        REQUIRE(output.write(true) && levels[18] == high);
        const auto writes = gpio_calls;
        REQUIRE(output.verify_active() && gpio_calls == writes);
        wrong_function = true;
        REQUIRE(!output.verify_active() && gpio_calls == writes);
        wrong_function = false;

        mismatch = true;
        REQUIRE(!output.write(false));
        mismatch = false;
        wrong_function = true;
        REQUIRE(!output.write(true));
        wrong_function = false;
        REQUIRE(output.write(false) && levels[18] == !high);
    }
    for (const auto gp : {2u, 14u, 23u, 24u, 25u, 29u, 30u, 999u}) {
        p.amplifier = gp;
        gpio_calls.clear();
        hardware::PicoAmplifierOutput invalid(p);
        REQUIRE(!invalid.initialize_inactive() && !invalid.write(true) && gpio_calls.empty());
    }
    for (const auto bad : {"null", "0", "1", "\"false\"", "{}", "[]"}) {
        auto text = canonical;
        text.pop_back();
        text += ",\"amplifier_active_high\":" + std::string(bad) + "}";
        REQUIRE(!hardware::parse_plan(text));
    }
}
void management() {
    for (const bool high : {true, false}) {
        Member m;
        const auto boot = m.scheduler.active_pins();
        auto p = boot;
        p.amplifier = 18;
        p.amplifier_active_high = high;
        gpio_calls.clear();
        REQUIRE(m.save(p).status == 200);
        REQUIRE(gpio_calls.empty()); // Saving/drafting never activates GPIO.
        REQUIRE(m.scheduler.active_pins() == boot && m.scheduler.hardware_restart_required());
        REQUIRE(m.f.store.config()->pins == p);
        const auto read = m.call("GET", "/api/v1/hardware/3");
        const auto value = parse(read.body);
        REQUIRE(value->get("schema")->string() == "transmitter-hardware/3");
        REQUIRE(value->get("saved")->get("amplifier_active_high")->boolean() == high);
        REQUIRE(value->get("active")->get("amplifier_gp")->raw == "null");
        const auto legacy = m.call("GET", "/api/v1/hardware");
        REQUIRE(legacy.status == 409);
        REQUIRE(legacy.body.find("amplifier_view_required") != std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/config").body.find("amplifier_active_high") ==
                std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/application/4").body.find("transmitter-hardware/3") !=
                std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/capabilities").body.find("inhibited_inactive_only") !=
                std::string::npos);
        REQUIRE(m.call("GET", "/api/v1/pins/2").body.find("\"amplifier\":true") !=
                std::string::npos);
        REQUIRE(m.call("POST", "/api/v1/pins/validate", hardware::serialize_plan(p)).status == 400);
        // Ordinary legacy full writes and legacy pin editors preserve the new resource.
        REQUIRE(m.call("PUT", "/api/v1/config", network_test::config).status == 200);
        REQUIRE(m.f.store.config()->pins == p);
        auto old = *standalone::parse_config(network_test::config);
        old.pins.rf = 3;
        REQUIRE(m.call("PUT", "/api/v1/config", standalone::serialize_config(old)).status == 200);
        REQUIRE(m.f.store.config()->pins.amplifier == 18);
        REQUIRE(m.f.store.config()->pins.amplifier_active_high == high);
        auto update = m.envelope("transmitter-config-update/3", "config", "{\"enabled\":false}");
        update.insert(update.size() - 1, ",\"mode\":\"merge\"");
        REQUIRE(m.call("POST", "/api/v1/config/update/4", update).status == 200);
        REQUIRE(m.f.store.config()->pins.amplifier == 18);
        auto omitted = p;
        omitted.rf = 4;
        auto text = hardware::serialize_plan(omitted);
        if (!high) { // Deliberate omission on ordinary save must preserve false.
            const auto pos = text.find(",\"amplifier_active_high\":false");
            text.erase(pos, std::string(",\"amplifier_active_high\":false").size());
        }
        REQUIRE(
            m.call("PUT", "/api/v1/hardware/3", m.envelope("transmitter-hardware/3", "pins", text))
                .status == 200);
        REQUIRE(m.f.store.config()->pins.amplifier_active_high == high);
        standalone::Store reloaded(m.f.flash);
        REQUIRE(reloaded.load() && reloaded.config()->pins == m.f.store.config()->pins);
        standalone::Scheduler next_boot(reloaded, m.f.service);
        REQUIRE(next_boot.active_pins() == reloaded.config()->pins);
        REQUIRE(m.save(boot).status == 200); // A/B/A cannot clear restart inhibition.
        REQUIRE(m.scheduler.hardware_restart_required() && m.f.service.output_inhibited());
        REQUIRE(gpio_calls.empty());
        update = m.envelope("transmitter-config-update/3", "config", network_test::config);
        update.insert(update.size() - 1, ",\"mode\":\"replace\"");
        REQUIRE(m.call("POST", "/api/v1/config/update/4", update).status == 200);
        REQUIRE(m.f.store.config()->pins == hardware::PinPlan{});
    }
}
void atomic_failures_and_progress() {
    Member m;
    auto type3 = m.envelope("transmitter-config-update/3", "config",
                            R"({"station":{"callsign":"<K1ABC>","locator":"FN42AB"}})");
    type3.insert(type3.size() - 1, ",\"mode\":\"merge\"");
    REQUIRE(m.call("POST", "/api/v1/config/update/4", type3).status == 200);
    REQUIRE(m.f.store.config()->callsign == "<K1ABC>");
    auto p = m.scheduler.active_pins();
    p.amplifier = 18;
    p.amplifier_active_high = false;
    const auto invalid_batch = [&](std::string pins) {
        auto batch = m.envelope("transmitter-progress/3", "fields",
                                "{\"locator\":\"FN42\",\"pins\":" + pins + "}");
        batch.insert(batch.size() - 1, ",\"request_id\":\"" + std::string(32, 'b') + "\"");
        const auto before = m.progress_flash.bytes;
        const auto rev = m.api.revision();
        REQUIRE(m.call("POST", "/api/v1/progress/update/3", batch).status == 400);
        REQUIRE(m.progress_flash.bytes == before && m.api.revision() == rev);
    };
    auto bad = hardware::serialize_plan(p, true);
    bad.replace(bad.find("\"amplifier_active_high\":false"),
                std::string("\"amplifier_active_high\":false").size(),
                "\"amplifier_active_high\":null");
    REQUIRE(parse(bad));
    invalid_batch(bad);
    for (const unsigned gp : {2u, 14u, 23u, 29u}) {
        auto conflict = p;
        conflict.amplifier = gp;
        invalid_batch(hardware::serialize_plan(conflict, true));
        const auto before = m.f.flash.bytes;
        REQUIRE(m.save(conflict).status == 400 && m.f.flash.bytes == before);
    }
    auto calibration = *m.f.store.config();
    calibration.manual_correction_ppb = -4321;
    calibration.ntp_rf_calibration = true;
    REQUIRE(m.f.store.save(calibration));
    auto fields = "{\"pins\":" + hardware::serialize_plan(p, true) + "}";
    auto batch = m.envelope("transmitter-progress/3", "fields", fields);
    batch.insert(batch.size() - 1, ",\"request_id\":\"" + std::string(32, 'c') + "\"");
    REQUIRE(m.call("POST", "/api/v1/progress/update/3", batch).status == 200);
    REQUIRE(!m.f.store.config()->pins.amplifier && !m.scheduler.hardware_restart_required());
    REQUIRE(m.call("GET", "/api/v1/progress").status == 409);
    const auto draft_before = m.progress_flash.bytes;
    const auto revision_before = m.api.revision();
    auto legacy_batch = m.envelope("transmitter-progress/1", "fields", "{\"locator\":\"FN42\"}");
    legacy_batch.insert(legacy_batch.size() - 1,
                        ",\"request_id\":\"" + std::string(32, 'f') + "\"");
    REQUIRE(m.call("POST", "/api/v1/progress/update", legacy_batch).status == 409);
    REQUIRE(m.progress_flash.bytes == draft_before && m.api.revision() == revision_before);
    standalone::Progress reloaded(m.progress_flash);
    REQUIRE(reloaded.load() && reloaded.amplifier_view_required());
    auto apply = m.envelope("transmitter-progress/3", "application",
                            "{\"draft_revision\":" + quote(std::to_string(m.progress.sequence())) +
                                ",\"domain\":\"radio\"}");
    REQUIRE(m.call("POST", "/api/v1/progress/apply/3", apply).status == 200);
    REQUIRE(m.f.store.config()->manual_correction_ppb == -4321);
    REQUIRE(m.f.store.config()->ntp_rf_calibration);
    REQUIRE(m.f.store.config()->pins == p && m.scheduler.hardware_restart_required());
    // Ordinary progress pin writes preserve omitted polarity, first from the
    // saved draft, then from applied configuration after draft clearing.
    auto omitted = hardware::serialize_plan(p);
    const auto polarity = std::string(",\"amplifier_active_high\":false");
    omitted.erase(omitted.find(polarity), polarity.size());
    batch = m.envelope("transmitter-progress/3", "fields", "{\"pins\":" + omitted + "}");
    batch.insert(batch.size() - 1, ",\"request_id\":\"" + std::string(32, 'd') + "\"");
    REQUIRE(m.call("POST", "/api/v1/progress/update/3", batch).status == 200);
    REQUIRE(!parse(m.progress.fields())->get("pins")->get("amplifier_active_high")->boolean());
    // A deliberate true value must survive canonical storage omission and
    // explicit application over the currently active-low saved settings.
    p.amplifier_active_high = true;
    batch = m.envelope("transmitter-progress/3", "fields",
                       "{\"pins\":" + hardware::serialize_plan(p, true) + "}");
    batch.insert(batch.size() - 1, ",\"request_id\":\"" + std::string(32, 'e') + "\"");
    auto saved = m.call("POST", "/api/v1/progress/update/3", batch);
    REQUIRE(saved.status == 200);
    REQUIRE(parse(saved.body)->get("fields")->get("pins")->get("amplifier_active_high")->boolean());
    apply = m.envelope("transmitter-progress/3", "application",
                       "{\"draft_revision\":" + quote(std::to_string(m.progress.sequence())) +
                           ",\"domain\":\"radio\"}");
    REQUIRE(m.call("POST", "/api/v1/progress/apply/3", apply).status == 200);
    REQUIRE(m.f.store.config()->pins.amplifier_active_high);
    const auto seq = m.f.store.config_sequence();
    m.f.flash.fail = true;
    p.amplifier = 17;
    REQUIRE(m.save(p).status == 503 && m.f.store.config_sequence() == seq);
}
void legacy_progress_preserves_other_pin_edits() {
    Member m;
    auto p = m.scheduler.active_pins();
    p.amplifier = 18;
    p.amplifier_active_high = false;
    REQUIRE(m.save(p).status == 200);
    auto legacy = hardware::PinPlan{};
    legacy.rf = 19;
    auto batch = m.envelope("transmitter-progress/1", "fields",
                            "{\"pins\":" + hardware::serialize_plan(legacy) + "}");
    batch.insert(batch.size() - 1, ",\"request_id\":\"" + std::string(32, 'f') + "\"");
    REQUIRE(m.call("POST", "/api/v1/progress/update", batch).status == 200);
    auto apply = m.envelope("transmitter-progress/1", "application",
                            "{\"draft_revision\":" + quote(std::to_string(m.progress.sequence())) +
                                ",\"domain\":\"radio\"}");
    REQUIRE(m.call("POST", "/api/v1/progress/apply", apply).status == 200);
    REQUIRE(m.f.store.config()->pins.rf == 19);
    REQUIRE(m.f.store.config()->pins.amplifier == 18);
    REQUIRE(!m.f.store.config()->pins.amplifier_active_high);
}
} // namespace
// Host stand-in for pinned SDK gpio_init's input/latch/function ordering.
void gpio_init(unsigned gp) {
    directions[gp] = false;
    gpio_calls.push_back("input " + std::to_string(gp));
    gpio_put(gp, false);
    gpio_calls.push_back("sio " + std::to_string(gp));
}
void gpio_put(unsigned gp, bool value) {
    levels[gp] = value;
    gpio_calls.push_back("put " + std::to_string(gp) + (value ? " 1" : " 0"));
}
void gpio_set_dir(unsigned gp, bool value) {
    directions[gp] = value;
    gpio_calls.push_back(std::string(value ? "out " : "input ") + std::to_string(gp));
}
bool gpio_get(unsigned gp) {
    return mismatch ? !levels[gp] : levels[gp];
}
unsigned gpio_get_function(unsigned) {
    return wrong_function ? 0 : GPIO_FUNC_SIO;
}
bool gpio_is_dir_out(unsigned gp) {
    return directions[gp];
}
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--timing-samples") {
        Member m;
        std::cout << application::amplifier_timing_capabilities() << '\n';
        std::cout << m.call("GET", "/api/v1/amplifier-timing").body << '\n';
        std::cout << m.envelope("transmitter-amplifier-timing/1", "timing",
                                "{\"lead_ms\":200,\"tail_ms\":200}")
                  << '\n';
        std::cout << application::amplifier_observation(rf::AmplifierObservation{}) << '\n';
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--samples") {
        Member m;
        auto p = m.scheduler.active_pins();
        p.amplifier = 18;
        p.amplifier_active_high = false;
        REQUIRE(m.save(p).status == 200);
        for (const auto route :
             {"/api/v1/application/4", "/api/v1/hardware/3", "/api/v1/progress/3"}) {
            auto result = m.call("GET", route);
            REQUIRE(result.status == 200);
            std::cout << result.body << '\n';
        }
        auto usb = request("GET", "/api/v1/application/4");
        const auto usb_result =
            m.api.handle(usb, "usb-physical", "", 0, network::ManagementCarrier::UsbPhysical);
        REQUIRE(usb_result.status == 200);
        std::cout << usb_result.body << '\n';
        const auto capability = m.call("GET", "/api/v1/capabilities");
        std::cout << std::string(parse(capability.body)->get("amplifier_enable")->raw) << '\n';
        return 0;
    }
    timing_management();
    pins_and_adapter();
    management();
    atomic_failures_and_progress();
    legacy_progress_preserves_other_pin_edits();
    std::cout << "Amplifier polarity, inactive initialization, compatibility, persistence and "
                 "atomic failure checks passed\n";
}
