// SPDX-License-Identifier: MIT
// Unchanged Pi product sources and original interoperability suite, plus rename preservation.
#include "provisioning/hostname.hpp"
#include "standalone/progress.hpp"
#include "unchanged_fixture.hpp"
struct HostnamePlatform : pico::provisioning::ConsumerClaimCommitPlatform {
    bool safe_to_commit() override {
        return true;
    }
    std::uint64_t monotonic_now_ms() override {
        return 1000;
    }
    bool station_ready(std::string_view) override {
        return true;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return {};
    }
    std::string_view local_hostname() override {
        return "wsprrypico-0a60df.local";
    }
    bool valid_owner_point(std::string_view) override {
        return false;
    }
    bool generate_tls(std::string_view, std::string_view, std::uint64_t,
                      pico::provisioning::ConsumerTls&) override {
        return false;
    }
    bool valid_tls(const pico::provisioning::ConsumerTls&, std::string_view,
                   std::uint64_t) override {
        return false;
    }
};
int main(int argc, char** argv) {
    assert(unchanged_pair_main(argc, argv) == 0);
    for (const bool ap : {false, true}) {
        Test t;
        network_test::Flash draft_flash;
        pico::standalone::Progress progress(draft_flash);
        assert(progress.load());t.f.api.progress_settings(progress);
        const auto fields=pico::wtp::json::parse(R"({"callsign":"BB1BB","locator":null})");
        assert(progress.save(*fields,std::string(64,'a')));
        const auto saved_draft=progress.fields();
        HostnamePlatform platform;
        const auto active = t.runtime.consumer_profile()->tls.hostname;
        pico::provisioning::HostnameSettings settings(t.profiles, t.runtime, platform, device,
                                                      active, active);
        t.f.api.hostname_settings(settings);
        if (ap) {
            t.authority = "192.168.4.1";
            t.origin = "http://192.168.4.1";
            t.interface = pico::network::ConsumerInterface::AccessPoint;
        }
        auto c = t.client();
        const auto carrier = ap ? "consumer_ap" : "consumer_station";
        assert(c->login(device, carrier, "test-password").status == 200);
        const auto exchanges_before = t.exchanges;
        const auto unsupported = pi::pico_resource_request(
            [&](auto p, auto m, auto b, auto e) { return c->request(p, m, b, e); }, c->device(),
            c->boot(), "hostname", "PUT", "{}", "", carrier, c->generation());
        assert(unsupported.status == 404 && t.exchanges == exchanges_before);
        assert(c->request("hostname", "GET", {}, {}).status == 404);
        assert(c->request("hostname", "PUT", "{}", {}).status == 404);
        assert(t.exchanges == exchanges_before);
        // The unchanged native Pi client deliberately cannot rename. Establish
        // that Pico-owned precondition through its production coordinator;
        // authenticated AP/station PUTs are covered by hostname_sessions.
        assert(settings.save(std::string{"pico-a.local"}).empty());
        assert(Json::parse(settings.readback(c->boot()))["pending_restart"] == true);
        assert(t.runtime.consumer_profile()->tls.hostname == "pico-a.local");
        t.f.api.management_availability({pico::network::ManagementProfile::Consumer,
                                         t.profiles.sequence(), true, false, false, true, true});
        assert(t.coordinated(*c).status != 200); // Old generation cannot keep its session.
        t.host.now += 1000;
        c = t.client();
        assert(c->login(device, carrier, "test-password").status == 200);
        auto config = t.coordinated(*c);
        assert(config.status == 200);
        // Existing complete PUT/merge saves omit hostname and must preserve its profile authority.
        const auto value = Json::parse(config.body);
        const Json edit = {{"schema", "wsprrypi-pico-settings/1"},
                           {"target", value["target"]},
                           {"operation", "save"},
                           {"config", {{"allow_non_amateur_frequency", true}}}};
        assert(t.coordinated(*c, "POST", edit.dump(), config.etag).status == 200);
        assert(t.runtime.consumer_profile()->tls.hostname == "pico-a.local");
        assert(t.f.store.watermark() == 1791970000000000000ULL && t.wtp.io == 0);
        assert(progress.fields()==saved_draft);
        assert(t.f.store.config()->callsign!="BB1BB");
        assert(c->request("progress", "GET", {}, {}).status==404); // Unchanged Pi client does not invent new support.
        std::cout << carrier << " unchanged Pi relogin/read/save retains Pico-owned hostname and incomplete saved progress"
                  << std::endl;
    }
}
