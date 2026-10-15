#include "network/management.hpp"
#include "network_support.hpp"
#include "wtp/json.hpp"

#include <cassert>
using namespace wsprrypico;
int main() {
    network_test::Fixture f;
    network::HttpRequest read{"GET", "/api/v1/management", "", {{"host", "127.0.0.1"}}};
    auto response = f.api.handle(read, "tls-cert:test", "127.0.0.1");
    assert(response.status == 200);
    auto unavailable = wtp::json::parse(response.body);
    assert(unavailable && unavailable->get("profile")->string() == "unavailable");
    const network::ManagementAvailability state{
        network::ManagementProfile::Consumer, 139, true, false, false, true, false};
    f.api.management_availability(state);
    response = f.api.handle(read, "consumer-radio:test", "127.0.0.1", 0,
                            network::ManagementCarrier::ConsumerStation);
    auto root = wtp::json::parse(response.body);
    assert(root && root->get("schema")->string() == "transmitter-management/2");
    assert(root->get("limits")->get("consumer_sessions")->raw == "3");
    assert(root->get("limits")->get("consumer_pending_logins")->raw == "1");
    assert(root->get("profile_generation")->string() == "139");
    assert(root->get("selected")->string() == "consumer_station");
    assert(root->get("preclock")->raw == "true");
    const auto rows = root->get("carriers")->elements();
    assert(rows.size() == 4 && rows[2].get("available")->raw == "true" &&
           rows[3].get("available")->raw == "false");
    assert(root->get("target")->get("boot_id")->string() == f.service.status().boot_id);
    assert(response.body.size() < 4096);
    // The extension sits outside closed application objects used by P15.2.
    read.path = "/api/v1/capabilities";
    const auto caps = f.api.handle(read, "tls-cert:test", "127.0.0.1");
    root = wtp::json::parse(caps.body);
    assert(root->get("management_carriers")->get("path")->string() == "/api/v1/management");
    assert(root->get("application_resources")->get("management_carrier")->string() ==
           "authenticated_https");
    for (auto profile : {network::ManagementProfile::Blank, network::ManagementProfile::Recovery}) {
        f.api.management_availability({profile});
        read.path = "/api/v1/management";
        response = f.api.handle(read, "tls-cert:test", "127.0.0.1");
        root = wtp::json::parse(response.body);
        for (const auto& row : root->get("carriers")->elements())
            assert(row.get("available")->raw == "false");
    }
}
