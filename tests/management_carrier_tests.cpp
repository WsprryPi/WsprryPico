#include "network/management.hpp"
#include "network_support.hpp"
#include "wtp/json.hpp"

#include <cassert>
using namespace wsprrypico;
int main() {
    network_test::Fixture f;
    network::HttpRequest read{"GET", "/api/control/v1/management", "", {{"host", "127.0.0.1"}}};
    auto response = f.api.handle(network_test::control_request(read), "tls-cert:test", "127.0.0.1");
    assert(response.status == 200);
    auto unavailable = wtp::json::parse(response.body_view());
    assert(unavailable && unavailable->get("profile")->string() == "unavailable");
    const network::ManagementAvailability state{
        network::ManagementProfile::Consumer, 139, true, false, false, true, false};
    f.api.management_availability(state);
    response = f.api.handle(network_test::control_request(read), "consumer-radio:test", "127.0.0.1", 0,
                            network::ManagementCarrier::ConsumerStation);
    auto root = wtp::json::parse(response.body_view());
    assert(root && root->get("schema")->string() == "management");
    assert(root->get("limits")->get("idle_ms")->raw == "1800000");
    assert(root->get("limits")->get("absolute_ms")->raw == "28800000");
    assert(root->get("limits")->get("login_ms")->raw == "30000");
    assert(root->get("limits")->get("consumer_sessions")->raw == "3");
    assert(root->get("limits")->get("consumer_pending_logins")->raw == "1");
    assert(root->get("profile_generation")->string() == "139");
    assert(root->get("selected")->string() == "consumer_station");
    assert(root->get("preclock")->raw == "true");
    const auto rows = root->get("carriers")->elements();
    assert(rows.size() == 5 && rows[2].get("available")->raw == "true" &&
           rows[3].get("available")->raw == "false");
    assert(root->get("target")->get("boot_id")->string() == f.service.status().boot_id);
    assert(response.body_size() < 4096);
    // Carrier selection has one authority in the management document.
    read.path = "/api/control/v1/capabilities";
    const auto caps = f.api.handle(network_test::control_request(read), "tls-cert:test", "127.0.0.1");
    root = wtp::json::parse(caps.body_view());
    assert(root->get("management_carriers")->get("path")->string() == "/api/control/v1/management");
    assert(root->get("management_carriers")->get("schema")->string() == "management");
    assert(!root->get("application_resources")->get("management_carrier"));
    for (auto profile : {network::ManagementProfile::Blank, network::ManagementProfile::Recovery}) {
        f.api.management_availability({profile});
        read.path = "/api/control/v1/management";
        response = f.api.handle(network_test::control_request(read), "tls-cert:test", "127.0.0.1");
        root = wtp::json::parse(response.body_view());
        for (const auto& row : root->get("carriers")->elements())
            assert(row.get("available")->raw == (row.get("carrier")->string() == "usb_physical" ? "true" : "false"));
    }
}
