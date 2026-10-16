// SPDX-License-Identifier: MIT
// External test harness; unchanged release product and source guards remain intact.
#include "unchanged_fixture.hpp"
int main() {
    for (bool ap : {false, true})
        for (const auto& call :
             {"AA0NT", "AA0NT/P", "<AA0NT>", "PJ4/AA0NT", "W1A/AA0NT", "AA0NT/09"}) {
            Test t;
            auto profile = *t.runtime.consumer_profile();
            profile.callsign = call;
            profile.locator = "EM18IG";
            profile.request_sha256 = std::string(64, 'b');
            assert(t.profiles.select(pico::provisioning::ProfileSource::ConsumerProfile,
                                     pico::provisioning::serialize_consumer_profile(profile)));
            assert(
                t.runtime.load(t.profiles, device, pico::provisioning::BuildBundleState::Absent));
            t.f.api.management_availability({pico::network::ManagementProfile::Consumer,
                                             t.profiles.sequence(), true, false, false, true,
                                             true});
            if (ap) {
                t.authority = "192.168.4.1";
                t.origin = "http://192.168.4.1";
                t.interface = pico::network::ConsumerInterface::AccessPoint;
            }
            const auto carrier = ap ? "consumer_ap" : "consumer_station";
            auto c = t.client();
            assert(c->login(device, carrier, "test-password").status == 200);
            const auto bytes = t.f.flash.bytes;
            const auto generation = t.profiles.sequence();
            const auto config = t.coordinated(*c);
            pi::PicoHttpResponse resources;
            assert(t.app->idle_management(
                [&] {
                    resources = pi::pico_resource_request(
                        [&](auto p, auto m, auto b, auto e) { return c->request(p, m, b, e); },
                        c->device(), c->boot(), "application", "GET", {}, {}, carrier,
                        c->generation());
                },
                true));
            if (std::string(call) == "AA0NT") {
                assert(config.status == 200 && resources.status == 200);
                const auto result = Json::parse(config.body);
                assert(result["config"]["station"]["locator"] == "EM18IG");
                const Json edit = {{"schema", "wsprrypi-pico-settings/1"},
                                   {"target", result["target"]},
                                   {"operation", "save"},
                                   {"config", {{"allow_non_amateur_frequency", true}}}};
                const auto saved = t.coordinated(*c, "POST", edit.dump(), config.etag);
                assert(saved.status == 200 && t.mutations == 1 &&
                       t.f.store.config()->allow_non_amateur_frequency);
                assert(t.f.store.watermark() == 1791970000000000000ULL);
            } else {
                assert(config.status == 409 && resources.status == 409);
                assert(Json::parse(config.body)["error"]["code"] == "unsupported_station_encoding");
                assert(Json::parse(resources.body)["error"]["code"] ==
                       "unsupported_station_encoding");
                assert(t.f.flash.bytes == bytes && t.profiles.sequence() == generation &&
                       t.mutations == 0);
            }
            assert(t.runtime.consumer_profile()->callsign == call &&
                   t.runtime.consumer_profile()->locator == "EM18IG" && t.wtp.io == 0);
            std::cout << carrier << " " << call << " "
                      << (std::string(call) == "AA0NT" ? "Type1 read/write WORK"
                                                       : "new format explicit REFUSE")
                      << std::endl;
        }
}
