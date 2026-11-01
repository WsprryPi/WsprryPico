#include "network/management.hpp"
#include "network/control_contract.hpp"

#include "application/resources.hpp"
#include "network/consumer_radio.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::network {
static_assert(ConsumerRadioApi::session_capacity == 3 && ConsumerRadioApi::pending_capacity == 1);
std::string management_contract(const ManagementAvailability& state, ManagementCarrier selected,
                                std::string_view device, std::string_view boot) {
    const char* names[] = {"engineering_mtls", "engineering_field", "consumer_station",
                           "consumer_ap", "usb_physical"};
    const bool available[] = {state.engineering_station, state.engineering_field,
                              state.consumer_station, state.consumer_ap, true};
    const char* profiles[] = {"unavailable", "blank", "recovery", "engineering", "consumer"};
    std::string rows;
    for (unsigned i = 0; i < 5U; ++i) {
        if (i)
            rows += ',';
        rows += "{\"carrier\":" + wtp::json::quote(names[i]) +
                ",\"built_in\":true,\"available\":" + (available[i] ? "true}" : "false}");
    }
    return std::string("{\"schema\":") + wtp::json::quote(management_schema(selected)) +
           ",\"target\":" + application::target(device, boot) +
           ",\"profile\":" + wtp::json::quote(profiles[static_cast<unsigned>(state.profile)]) +
           ",\"preclock\":" + (state.preclock ? "true" : "false") + ",\"profile_generation\":" +
           (state.generation ? wtp::json::quote(std::to_string(state.generation)) : "null") +
           ",\"selected\":" + wtp::json::quote(names[static_cast<unsigned>(selected)]) +
           ",\"carriers\":[" + rows +
           "],\"unsupported\":[\"plain_wtp_json\",\"tls_wtp_json\",\"ble_json\"]," +
           "\"operations\":" + std::string(control_operations) +
           ",\"limits\":{\"http_body\":32768,"
           "\"consumer_plaintext\":32724,\"config\":1800,\"update\":2048,\"login_ms\":" +
           std::to_string(ConsumerRadioApi::login_ms) +
           ",\"idle_ms\":" + std::to_string(ConsumerRadioApi::idle_ms) +
           ",\"absolute_ms\":" + std::to_string(ConsumerRadioApi::absolute_ms) +
           ",\"consumer_sessions\":3,\"consumer_pending_"
           "logins\":1}}";
}
} // namespace wsprrypico::network
