#include "provisioning/local_settings.hpp"

#include "application/resources.hpp"
#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "wtp/sha256.hpp"

namespace wsprrypico::provisioning {
namespace {
std::string digest(std::string_view text) {
    return network::bootstrap_hex(
        wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size())));
}
struct ConsumerProposal {
    ConsumerProfile value;
    ~ConsumerProposal() {
        scrub(value);
    }
};
struct EngineeringProposal {
    Profile value;
    ~EngineeringProposal() {
        scrub(value);
    }
};
} // namespace
bool LocalSettings::healthy() const {
    return profiles_.healthy() && store_.healthy() && progress_.healthy() &&
           runtime_.control_healthy(profiles_);
}
std::string LocalSettings::revision_context() const {
    return ":usb-profile:" + std::to_string(profiles_.sequence()) + (healthy() ? ":ok" : ":fault");
}
std::optional<ConsumerProfile> LocalSettings::consumer_candidate() const {
    if (!healthy())
        return {};
    if (const auto* existing = runtime_.consumer_profile())
        return *existing;
    if (runtime_.profile() || runtime_.source() == RuntimeSource::Factory)
        return {};
    ConsumerProfile result;
    result.usb_managed = true;
    result.device_id = device_;
    result.time_server = standalone::default_time_server;
    result.tls_pending = true;
    result.tls.hostname = default_;
    result.request_sha256 = digest(device_ + ":usb-initial");
    if (const auto* net = runtime_.network_profile()) {
        result.ssid = net->ssid;
        result.password = net->password;
        result.time_server = net->time_server;
    }
    return result;
}
std::string LocalSettings::commit(ProfileSource source, std::string_view payload) {
    if (!healthy() || payload.empty())
        return "storage_fault";
    if (profiles_.source() == source && profiles_.data() == payload)
        return {};
    const auto result = commit_setup_profile(profiles_, source, payload);
    const bool loaded = runtime_.load(
        profiles_, device_, factory_ ? BuildBundleState::Matching : BuildBundleState::Absent);
    if (!loaded || result == SetupCommitResult::Reconcile)
        return "reconcile_required";
    if (result != SetupCommitResult::Committed)
        return "storage_fault";
    return {};
}
std::string LocalSettings::ensure_local_profile() {
    if (!healthy())
        return "storage_fault";
    if (runtime_.consumer_profile())
        return {};
    auto parsed = consumer_candidate();
    if (!parsed)
        return "credential_bound_deployment";
    ConsumerProposal proposal{std::move(*parsed)};
    scrub(*parsed);
    return commit(ProfileSource::ConsumerProfile, serialize_consumer_profile(proposal.value));
}
std::string LocalSettings::wifi_readback(std::string_view boot) const {
    std::string ssid, server = standalone::default_time_server;
    if (const auto* p = runtime_.consumer_profile()) {
        ssid = p->ssid;
        server = p->time_server;
    } else if (const auto* p = runtime_.profile()) {
        ssid = p->ssid;
        server = p->time_server;
    } else if (const auto* p = runtime_.network_profile()) {
        ssid = p->ssid;
        server = p->time_server;
    } else if (factory_) {
        ssid = factory_->ssid;
        server = factory_->time_server;
    }
    return "{\"schema\":\"wifi\",\"target\":" + application::target(device_, boot) +
           ",\"wifi\":" +
           (ssid.empty()
                ? std::string("null")
                : "{\"ssid\":" + wtp::json::quote(ssid) +
                      ",\"password\":null,\"time_server\":" + wtp::json::quote(server) + "}") +
           ",\"generation\":" + wtp::json::quote(std::to_string(profiles_.sequence())) +
           ",\"pending_restart\":" + (pending_restart_ ? "true" : "false") +
           ",\"storage_healthy\":" + (healthy() ? "true}" : "false}");
}
std::string LocalSettings::wifi_save(wtp::json::Value wifi) {
    using namespace wtp::json;
    if (!healthy())
        return "storage_fault";
    const bool remove = wifi.raw == "null";
    std::string ssid, password, server = standalone::default_time_server;
    const auto current = wifi_readback("");
    const auto readback = parse(current);
    const auto saved = readback->get("wifi");
    if (!remove) {
        if (!fields(wifi, {"ssid", "password", "time_server"}) || wifi.get("ssid")->type() != '"' ||
            wifi.get("time_server")->type() != '"' ||
            (wifi.get("password")->type() != '"' && wifi.get("password")->raw != "null"))
            return "invalid_wifi";
        ssid = wifi.get("ssid")->string();
        server = wifi.get("time_server")->string();
        if (wifi.get("password")->raw == "null") {
            if (saved->raw == "null" || saved->get("ssid")->string() != ssid)
                return "password_required";
            if (const auto* p = runtime_.consumer_profile())
                password = p->password;
            else if (const auto* p = runtime_.profile())
                password = p->password;
            else if (const auto* p = runtime_.network_profile())
                password = p->password;
            else if (factory_)
                password = factory_->password;
        } else
            password = wifi.get("password")->string();
        if (!standalone::valid_wifi_credentials(ssid, password, server))
            return "invalid_wifi";
    }
    if (runtime_.source() == RuntimeSource::Factory && !factory_)
        return "factory_profile_unavailable";
    // Remove stale network drafts before the authoritative profile commits.
    // Power failure before the final boundary leaves the previous profile;
    // after it, neither standalone nor progress can reintroduce old credentials.
    const auto draft = "{\"wifi\":{\"ssid\":" + quote(ssid) + ",\"password\":" + quote(password) +
                       "},\"ntp_ipv4\":" + quote(server) + "}";
    const auto parsed_draft = parse(draft);
    if (!progress_.save(*parsed_draft, digest(draft)))
        return "storage_fault";
    const auto* previous_consumer = runtime_.consumer_profile();
    if (store_.config() || (remove && previous_consumer && !previous_consumer->usb_managed)) {
        const auto previous = (store_.config() ? *store_.config() : standalone::factory_config());
        auto config = previous_consumer ? runtime_.overlay(previous).value_or(previous) : previous;
        config.ssid = ssid;
        config.password = password;
        config.ntp_ipv4 = server;
        if (!store_.save(config))
            return "storage_fault";
    }
    std::string result;
    if (runtime_.profile() || runtime_.source() == RuntimeSource::Factory) {
        if (!runtime_.profile() && !factory_)
            return "factory_profile_unavailable";
        EngineeringProposal proposal{runtime_.profile() ? *runtime_.profile() : *factory_};
        proposal.value.usb_managed = proposal.value.usb_managed || remove;
        proposal.value.ssid = ssid;
        proposal.value.password = password;
        proposal.value.time_server = server;
        result = commit(ProfileSource::RuntimeProfile, serialize_profile(proposal.value));
    } else {
        auto parsed = consumer_candidate();
        if (!parsed)
            return "profile_unavailable";
        ConsumerProposal proposal{std::move(*parsed)};
        scrub(*parsed);
        proposal.value.usb_managed = proposal.value.usb_managed || remove;
        if (proposal.value.usb_managed) {
            proposal.value.callsign.clear();
            proposal.value.locator.clear();
            proposal.value.power_dbm = 0;
        }
        proposal.value.ssid = ssid;
        proposal.value.password = password;
        proposal.value.time_server = server;
        proposal.value.request_sha256 =
            digest(profiles_.data() + ":usb-wifi:" + std::to_string(profiles_.sequence()) + draft);
        result = commit(ProfileSource::ConsumerProfile, serialize_consumer_profile(proposal.value));
    }
    if (result.empty())
        pending_restart_ = true;
    volatile char* secret = password.data();
    for (std::size_t i = 0; i < password.size(); ++i)
        secret[i] = 0;
    return result;
}
std::string LocalSettings::station_save(const standalone::Config&) {
    if (!healthy())
        return "storage_fault";
    if (!runtime_.consumer_profile() || runtime_.consumer_profile()->usb_managed)
        return {};
    // Transfer station authority without changing the effective configuration.
    // The caller's requested complete Config is committed afterwards through
    // the one standalone journal, so a torn save cannot mix station and radio.
    const auto effective = runtime_.overlay((store_.config() ? *store_.config() : standalone::factory_config()));
    if (!effective || !store_.save(*effective))
        return "storage_fault";
    ConsumerProposal proposal{*runtime_.consumer_profile()};
    proposal.value.usb_managed = true;
    proposal.value.callsign.clear();
    proposal.value.locator.clear();
    proposal.value.power_dbm = 0;
    proposal.value.request_sha256 =
        digest(profiles_.data() + ":usb-station-authority:" + std::to_string(profiles_.sequence()));
    return commit(ProfileSource::ConsumerProfile, serialize_consumer_profile(proposal.value));
}
} // namespace wsprrypico::provisioning
