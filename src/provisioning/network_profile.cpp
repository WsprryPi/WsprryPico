#include "provisioning/network_profile.hpp"

#include "network/identity.hpp"
#include "provisioning/consumer_profile.hpp"
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
           printable(profile.password, 8, 63) &&
           standalone::valid_time_server(profile.time_server) &&
           (profile.request_sha256.empty() ||
            (profile.request_sha256.size() == 64 &&
             std::all_of(profile.request_sha256.begin(), profile.request_sha256.end(),
                         [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); })));
}

std::optional<NetworkProfile> parse_network_profile(std::string_view text) {
    if (text.empty() || text.size() > 768)
        return {};
    auto root = wtp::json::parse(text);
    if (!root || !root->get("version"))
        return {};
    const bool old = root->get("version")->raw == "1";
    const bool durable = root->get("version")->raw == "3";
    if ((!old && !durable && root->get("version")->raw != "2") ||
        !wtp::json::fields(
            *root, old ? std::initializer_list<std::string_view>{"version", "device_id", "ssid",
                                                                 "password"}
                   : durable
                       ? std::initializer_list<std::string_view>{"version", "device_id", "ssid",
                                                                 "password", "time_server",
                                                                 "request_sha256"}
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
    if (durable) {
        if (root->get("request_sha256")->type() != '"' ||
            root->get("request_sha256")->string().empty()) {
            scrub(profile);
            return {};
        }
        profile.request_sha256 = root->get("request_sha256")->string();
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
    return "{\"version\":" + std::string(profile.request_sha256.empty() ? "2" : "3") +
           ",\"device_id\":" + wtp::json::quote(profile.device_id) +
           ",\"ssid\":" + wtp::json::quote(profile.ssid) +
           ",\"password\":" + wtp::json::quote(profile.password) +
           ",\"time_server\":" + wtp::json::quote(profile.time_server) +
           (profile.request_sha256.empty()
                ? std::string{}
                : ",\"request_sha256\":" + wtp::json::quote(profile.request_sha256)) +
           "}";
}

SetupCommitResult commit_setup_profile(ProfileStore& store, ProfileSource source,
                                       std::string_view payload) {
    if (!store.healthy() || payload.empty() || store.sequence() == UINT64_MAX)
        return SetupCommitResult::Reconcile;
    const auto previous_generation = store.sequence();
    const auto previous_source = store.source();
    std::string previous = store.data();
    const bool selected = store.select(source, payload);
    if (!selected)
        (void)store.load();
    const bool committed = store.healthy() && store.sequence() == previous_generation + 1 &&
                           store.source() == source && store.data() == payload;
    const bool unchanged = store.healthy() && store.sequence() == previous_generation &&
                           store.source() == previous_source && store.data() == previous;
    clear(previous);
    return committed   ? SetupCommitResult::Committed
           : unchanged ? SetupCommitResult::NotCommitted
                       : SetupCommitResult::Reconcile;
}

std::string setup_request_digest(const ProfileStore& store, std::string_view device_id) {
    if (!store.healthy())
        return {};
    if (store.source() == ProfileSource::NetworkOnly) {
        auto profile = parse_network_profile(store.data());
        const auto digest =
            profile && profile->device_id == device_id ? profile->request_sha256 : std::string{};
        if (profile)
            scrub(*profile);
        return digest;
    }
    if (store.source() == ProfileSource::ConsumerProfile) {
        auto profile = parse_consumer_profile(store.data());
        const auto digest =
            profile && profile->device_id == device_id ? profile->request_sha256 : std::string{};
        if (profile)
            scrub(*profile);
        return digest;
    }
    return {};
}

void scrub(NetworkProfile& profile) {
    clear(profile.device_id);
    clear(profile.ssid);
    clear(profile.password);
    clear(profile.time_server);
    clear(profile.request_sha256);
}
} // namespace wsprrypico::provisioning
