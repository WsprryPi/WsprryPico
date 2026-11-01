#include "network_support.hpp"
#include "application/resources.hpp"
#include "standalone/progress.hpp"

using namespace wsprrypico;
using namespace network_test;
namespace { unsigned progress_checks=0; }
#undef REQUIRE
#define REQUIRE(x) do { ++progress_checks; if (!(x)) { std::cerr << __LINE__ << ": " #x "\n"; std::exit(1); } } while(false)
namespace {
network::HttpRequest request(std::string path, std::string body = {}) {
    return {body.empty() ? "GET" : "POST", std::move(path), std::move(body),
        {{"host", "127.0.0.1:8443"}, {"origin", "https://127.0.0.1:8443"},
         {"x-wsprrypico-request", "1"}, {"content-type", "application/json"}}};
}
struct ProgressFixture : Fixture {
    Flash draft_flash;
    standalone::Progress progress{draft_flash};
    ProgressFixture() { REQUIRE(progress.load()); api.progress_settings(progress); }
    network::HttpResponse read() {
        return api.handle(network_test::control_request(request("/api/control/v1/progress")), "test", "127.0.0.1:8443");
    }
    network::HttpResponse save(std::string fields, std::string revision = {}) {
        auto r = request("/api/control/v1/progress/update", "{\"schema\":\"progress\",\"target\":" +
            application::target("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", service.status().boot_id) +
            ",\"request_id\":\"11111111111111111111111111111111\",\"fields\":" + fields + '}');
        r.headers["if-match"] = revision.empty() ? api.revision() : revision;
        return api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    }
    network::HttpResponse apply(std::string domain = "all") {
        auto r = request("/api/control/v1/progress/apply", "{\"schema\":\"progress\",\"target\":" +
            application::target("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", service.status().boot_id) +
            ",\"application\":{\"draft_revision\":" + wtp::json::quote(std::to_string(progress.sequence())) + ",\"domain\":" + wtp::json::quote(domain) + "}}");
        r.headers["if-match"] = api.revision();
        return api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    }
};
void independent() {
    ProgressFixture f;
    const auto service = f.service.status();
    REQUIRE(f.save(R"({"callsign":"AA0NT"})").status == 200);
    REQUIRE(!f.store.config());
    REQUIRE(f.progress.fields() == R"({"callsign":"AA0NT"})");
    REQUIRE(f.apply().status == 409);
    REQUIRE(f.save(R"({"locator":"EM18IG","power_dbm":0})").status == 200);
    REQUIRE(f.progress.candidate({}));
    REQUIRE(f.progress.candidate({})->power_dbm == 0);
    REQUIRE(!f.store.config());
    REQUIRE(f.store.config_sequence() == 0 && f.store.watermark() == 0);
    REQUIRE(f.service.status().owner_id == service.owner_id);
    REQUIRE(f.service.status().job_id == service.job_id);
    REQUIRE(f.service.status().output_active == service.output_active);
    standalone::Progress reboot(f.draft_flash);
    REQUIRE(reboot.load());
    REQUIRE(reboot.fields() == f.progress.fields());
    REQUIRE(reboot.candidate({})->callsign == "AA0NT");
    REQUIRE(f.apply().status == 200);
    REQUIRE(f.store.config()->power_dbm == 0);
    REQUIRE(!f.store.config()->enabled);
}
void mixed_and_revisions() {
    ProgressFixture f;
    const auto before = f.api.revision();
    const auto value=wtp::json::parse(R"({"callsign":"AA0NT"})");
    REQUIRE(!f.progress.save(*value,std::string(64,'g')));
    REQUIRE(f.progress.sequence()==0);
    const auto r = f.save(R"({"callsign":"AA0NT/09","locator":"bad","power_dbm":""})");
    REQUIRE(r.status == 200);
    REQUIRE(r.body.find("\"locator\":\"invalid\"") != std::string::npos);
    REQUIRE(f.progress.fields() == R"({"callsign":"AA0NT/09"})");
    REQUIRE(f.save(R"({"locator":"EM18"})", before).status == 412);
    auto revision = f.api.revision();
    REQUIRE(f.save(R"({"callsign":"AA0NT/09"})").status == 200);
    REQUIRE(revision != f.api.revision());
    REQUIRE(f.save(R"({"callsign":"BB1BB"})").status == 200);
    REQUIRE(f.save(R"({"callsign":"AA0NT/09"})").status == 200);
    REQUIRE(f.save(R"({"locator":"EM18"})", revision).status == 412);
    auto sequence = f.progress.sequence();
    REQUIRE(f.save(R"({"callsign":"AA0NT","unexpected":true})").status == 400);
    REQUIRE(f.save(R"({"callsign":"AA0NT","callsign":"BB1BB"})").status == 400);
    REQUIRE(f.progress.sequence() == sequence);
    REQUIRE(f.save(R"({"locator":null})").status == 200);
    REQUIRE(!f.progress.candidate(standalone::parse_config(config)));
}
void legacy_authority() {
    ProgressFixture f;
    REQUIRE(f.save(R"({"callsign":"BB1BB","locator":null})").status==200);
    const auto before=f.progress.fields();
    REQUIRE(f.scheduler.command("CONFIG "+config).find("true")!=std::string::npos);
    REQUIRE(f.store.config()->callsign=="AA0NT");
    REQUIRE(f.progress.fields()==before);
    auto preview=request("/api/control/v1/wspr-plan",R"({"callsign":"CC2CC","locator":"EM18","power_dbm":0})");
    const auto seq=f.store.config_sequence();
    REQUIRE(f.api.handle(network_test::control_request(preview),"test","127.0.0.1:8443").status==200);
    REQUIRE(f.store.config_sequence()==seq && f.progress.fields()==before);
    standalone::Store reload(f.flash);REQUIRE(reload.load());
    REQUIRE(reload.config()->callsign=="AA0NT");
    standalone::Progress draft(f.draft_flash);REQUIRE(draft.load());
    REQUIRE(draft.fields()==before && !draft.candidate(reload.config()));
}
void coupled_and_preservation() {
    ProgressFixture f;
    REQUIRE(f.store.save(*standalone::parse_config(config)));
    REQUIRE(f.store.reserve(100));
    REQUIRE(f.scheduler.command("STOP").find("true") != std::string::npos);
    const auto applied = *f.store.config();
    const auto sequence = f.store.config_sequence();
    const auto result = f.save(R"({"callsign":"AA0NT/09","schedules":[{"period_s":120,"phase_s":0},{"period_s":240,"phase_s":0}],"wifi":{"ssid":"other","password":"short"},"frequency_policy":{"allow_unqualified_frequency":false,"allow_non_amateur_frequency":true}})");
    REQUIRE(result.status == 200);
    REQUIRE(f.progress.fields() == R"({"callsign":"AA0NT/09"})");
    REQUIRE(*f.store.config() == applied && f.store.config_sequence() == sequence);
    REQUIRE(f.store.watermark() == 100);
    REQUIRE(f.scheduler.status().find("\"suspended\":true") != std::string::npos);
    REQUIRE(f.apply().status == 200);
    REQUIRE(f.store.config()->callsign == "AA0NT/09");
    REQUIRE(f.store.config()->password == applied.password && f.store.config()->locator == applied.locator);
    REQUIRE(f.scheduler.status().find("\"suspended\":true") != std::string::npos);
    REQUIRE(f.store.watermark() == 100);
    auto legacy = request("/api/control/v1/config", R"({"version":1,"enabled":false,"station":{"callsign":"BB1BB","locator":"bad","power_dbm":0},"wifi":{"ssid":"","password":""},"schedules":[]})");
    legacy.method = "PUT"; legacy.headers["if-match"] = f.api.revision();
    const auto stored = *f.store.config();
    REQUIRE(f.api.handle(network_test::control_request(legacy), "test", "127.0.0.1:8443").status == 405);
    REQUIRE(*f.store.config() == stored);
}
void faults_and_secrets() {
    ProgressFixture f;
    REQUIRE(f.store.save(*standalone::parse_config(config)));
    REQUIRE(f.save(R"({"wifi":{"ssid":"draft-net","password":"private-draft"}})").status == 200);
    REQUIRE(f.read().body.find("private-draft") == std::string::npos);
    REQUIRE(f.progress.candidate(f.store.config())->password == "private-draft");
    REQUIRE(f.save(R"({"wifi":{"ssid":"renamed-draft","password":null}})").status == 200);
    REQUIRE(f.progress.candidate(f.store.config())->password == "private-draft");
    REQUIRE(f.progress.candidate(f.store.config())->ssid == "renamed-draft");
    const auto applied = *f.store.config();
    f.draft_flash.fail = true;
    REQUIRE(f.save(R"({"locator":"EM18IG"})").status == 503);
    REQUIRE(!f.store.healthy() && *f.store.config() == applied);
    f.draft_flash.fail = false;
    REQUIRE(f.store.erase_progress());
    REQUIRE(f.store.healthy() && f.progress.sequence() == 0);
    REQUIRE(f.save(R"({"callsign":"AA0NT"})").status == 200);
    f.draft_flash.bytes[40] ^= 1;
    standalone::Progress corrupted(f.draft_flash);
    REQUIRE(!corrupted.load());
    REQUIRE(corrupted.erase() && corrupted.fields() == "{}");
}
void domains_and_admission() {
    ProgressFixture f;
    auto selected = *standalone::parse_config(config);
    selected.wspr_dial_frequency_hz = 14'095'600;
    REQUIRE(f.store.save(selected));
    const auto applied = *f.store.config();
    REQUIRE(f.save(R"({"locator":null,"enabled":true,"ntp_ipv4":"pool.ntp.org"})").status == 200);
    REQUIRE(!f.progress.candidate(applied));
    REQUIRE(f.apply("radio").status == 200);
    REQUIRE(f.store.config()->enabled && f.store.config()->locator == applied.locator);
    REQUIRE(f.store.config()->wspr_dial_frequency_hz == selected.wspr_dial_frequency_hz);
    REQUIRE(f.apply("network").status == 200);
    REQUIRE(f.store.config()->ntp_ipv4 == "pool.ntp.org");
    REQUIRE(f.apply("station").status == 409);
    REQUIRE(f.progress.station_fields(f.store.config()).find("\"locator\":null") != std::string::npos);
    const auto seq=f.progress.sequence();
    auto r=request("/api/control/v1/progress/update", "{}");
    r.headers["origin"]="https://wrong.example";
    REQUIRE(f.api.handle(network_test::control_request(r),"test","127.0.0.1:8443").status == 403);
    r.headers["origin"]="https://127.0.0.1:8443";r.headers.erase("x-wsprrypico-request");
    REQUIRE(f.api.handle(network_test::control_request(r),"test","127.0.0.1:8443").status == 403);
    REQUIRE(f.progress.sequence() == seq);
    const auto public_read=f.api.progress_readback(true);
    REQUIRE(public_read.body.find("pool.ntp.org") == std::string::npos);
    REQUIRE(public_read.body.find("\"last_receipt\":null") != std::string::npos);
    REQUIRE(public_read.body.find("\"last_outcomes\":{\"locator\":\"cleared\"}") != std::string::npos);
}
struct TornFlash : Flash {
    int pages=-1;
    bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
        if (pages==0) {std::copy_n(data.begin(),17,bytes.begin()+offset);return false;}
        if (pages>0) --pages;
        return Flash::program(offset,data);
    }
};
void torn_progress() {
    // Every interrupted page of both an append and a bank rollover is fail-closed.
    for (int initial : {1,2}) for (int cut=0;cut<8;++cut) {
        TornFlash flash; standalone::Progress p(flash); REQUIRE(p.load());
        const std::string receipt(64,'a');
        const auto value=wtp::json::parse(R"({"callsign":"AA0NT"})");
        for (int i=0;i<initial;++i) REQUIRE(p.save(*value,receipt));
        flash.pages=cut;
        const auto changed=wtp::json::parse(R"({"callsign":"BB1BB"})");
        REQUIRE(!p.save(*changed,receipt)); REQUIRE(!p.healthy());
        standalone::Progress reboot(flash);REQUIRE(!reboot.load());
        flash.pages=-1; REQUIRE(reboot.erase()); REQUIRE(reboot.sequence()==0);
        REQUIRE(reboot.fields()=="{}"); REQUIRE(!reboot.candidate({}));
    }
}
} // namespace
int main() {
    independent(); legacy_authority(); mixed_and_revisions(); coupled_and_preservation(); faults_and_secrets(); domains_and_admission(); torn_progress();
    std::cout << "progress persistence/API tests passed: " << progress_checks << " explicit assertions\n";
}
