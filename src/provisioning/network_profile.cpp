#include "provisioning/network_profile.hpp"

#include "network/identity.hpp"
#include "wtp/json.hpp"

#include <algorithm>

namespace wsprrypico::provisioning {
namespace {
bool printable(std::string_view text, std::size_t minimum, std::size_t maximum) {
    return text.size() >= minimum && text.size() <= maximum &&
           std::all_of(text.begin(), text.end(),
                       [](unsigned char c) { return c >= 32 && c < 127; });
}
void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
} // namespace

bool valid_network_profile(const NetworkProfile& profile) {
    return network::valid_device_id(profile.device_id) && printable(profile.ssid, 1, 32) &&
           printable(profile.password, 8, 63) && standalone::valid_time_server(profile.time_server);
}

std::optional<NetworkProfile> parse_network_profile(std::string_view text) {
    if (text.empty() || text.size() > 640)
        return {};
    auto root = wtp::json::parse(text);
    if (!root || !root->get("version"))
        return {};
    const bool old = root->get("version")->raw == "1";
    if ((!old && root->get("version")->raw != "2") ||
        !wtp::json::fields(
            *root, old ? std::initializer_list<std::string_view>{"version", "device_id", "ssid",
                                                                 "password"}
                       : std::initializer_list<std::string_view>{"version", "device_id", "ssid",
                                                                 "password", "time_server"}) ||
        root->get("device_id")->type() != '"' || root->get("ssid")->type() != '"' ||
        root->get("password")->type() != '"')
        return {};
    NetworkProfile profile{root->get("device_id")->string(), root->get("ssid")->string(),
                           root->get("password")->string()};
    if (!old) {
        if (root->get("time_server")->type() != '"')
            return {};
        profile.time_server = root->get("time_server")->string();
    }
    if (!valid_network_profile(profile)) {
        scrub(profile);
        return {};
    }
    return profile;
}

std::string serialize_network_profile(const NetworkProfile& profile) {
    if (!valid_network_profile(profile))
        return {};
    return "{\"version\":2,\"device_id\":" + wtp::json::quote(profile.device_id) +
           ",\"ssid\":" + wtp::json::quote(profile.ssid) +
           ",\"password\":" + wtp::json::quote(profile.password) +
           ",\"time_server\":" + wtp::json::quote(profile.time_server) + "}";
}

void scrub(NetworkProfile& profile) {
    clear(profile.device_id);
    clear(profile.ssid);
    clear(profile.password);
    clear(profile.time_server);
}
} // namespace wsprrypico::provisioning
