// SPDX-License-Identifier: MIT
#include "logging/udp_settings.hpp"
namespace wsprrypico::logging {
std::optional<UdpSettings> parse_udp_settings(wtp::json::Value value) {
    using namespace wtp::json;
    if (!fields(value, {"enabled", "destination_ipv4", "destination_port", "maximum_severity",
                        "event_codes", "rate", "burst"}))
        return {};
    UdpSettings s;
    const auto enabled = value.get("enabled");
    if (enabled->raw != "true" && enabled->raw != "false")
        return {};
    s.enabled = enabled->raw == "true";
    const auto destination = value.get("destination_ipv4");
    if (destination->raw != "null" &&
        (destination->type() != '"' || !s.destination_ipv4.assign(destination->string()) ||
         s.destination_ipv4.view().empty()))
        return {};
    const auto integer = [&](const char* key, unsigned& out) {
        const auto v = value.get(key);
        std::uint64_t n{};
        if (!v || !wsprry::logging::decimal(std::string(v->raw), n) || n > 65535)
            return false;
        out = static_cast<unsigned>(n);
        return true;
    };
    if (!integer("destination_port", s.destination_port) ||
        !integer("maximum_severity", s.maximum_severity) || !integer("rate", s.rate) ||
        !integer("burst", s.burst))
        return {};
    const auto codes = value.get("event_codes");
    if (codes->type() != '[')
        return {};
    std::size_t cursor = 0;
    while (const auto code = codes->next_element(cursor)) {
        if (s.event_count == 16 || code->type() != '"' ||
            !s.event_codes[s.event_count].assign(code->string()))
            return {};
        ++s.event_count;
    }
    return valid_udp_settings(s) ? std::optional<UdpSettings>{s} : std::nullopt;
}
std::string udp_settings_json(const UdpSettings& s) {
    using wtp::json::quote;
    std::string codes = "[";
    for (std::size_t i = 0; i < s.event_count; ++i) {
        if (i)
            codes += ',';
        codes += quote(s.event_codes[i].view());
    }
    return "{\"enabled\":" + std::string(s.enabled ? "true" : "false") + ",\"destination_ipv4\":" +
           (s.destination_ipv4.view().empty() ? "null" : quote(s.destination_ipv4.view())) +
           ",\"destination_port\":" + std::to_string(s.destination_port) +
           ",\"maximum_severity\":" + std::to_string(s.maximum_severity) +
           ",\"event_codes\":" + codes + "],\"rate\":" + std::to_string(s.rate) +
           ",\"burst\":" + std::to_string(s.burst) + "}";
}
std::string udp_active_json(const UdpSender& sender, std::string_view revision) {
    constexpr std::array states = {"disabled", "awaiting_network",  "invalid_destination",
                                   "ready",    "submission_failed", "unavailable"};
    const auto& c = sender.counters();
    std::string counters = "{";
    const auto field = [&](std::string_view key, std::uint64_t n) {
        if (counters.size() > 1)
            counters += ',';
        counters += wtp::json::quote(key) + ":" + wtp::json::quote(std::to_string(n));
    };
    field("generated", c.generated);
    field("filtered", c.filtered);
    field("redacted_rejected", c.redacted_rejected);
    field("queued", c.queued);
    field("overflow", c.overflow);
    field("expired", c.expired);
    field("reconfigured_drops", c.reconfigured_drops);
    field("truncated", c.truncated);
    field("attempted", c.attempted);
    field("locally_submitted", c.locally_submitted);
    field("locally_failed", c.locally_failed);
    return "{\"state\":" + wtp::json::quote(states[static_cast<unsigned>(sender.state())]) +
           ",\"applied_revision\":" + wtp::json::quote(revision) +
           ",\"receipt\":\"unknown\",\"queued\":" + std::to_string(sender.queued()) +
           ",\"counters\":" + counters + "}}";
}
bool UdpStore::load() {
    healthy_ = false;
    settings_ = {};
    if (!journal_.load())
        return false;
    if (!journal_.data().empty()) {
        const auto root = wtp::json::parse(journal_.data(), 8);
        if (!root || !wtp::json::fields(*root, {"schema", "settings"}) ||
            root->get("schema")->type() != '"' ||
            root->get("schema")->string() != "udp-logging-state/1")
            return false;
        const auto settings = parse_udp_settings(*root->get("settings"));
        if (!settings)
            return false;
        settings_ = *settings;
    }
    healthy_ = true;
    return true;
}
bool UdpStore::save(const UdpSettings& value) {
    if (!healthy() || !valid_udp_settings(value))
        return false;
    const auto text =
        "{\"schema\":\"udp-logging-state/1\",\"settings\":" + udp_settings_json(value) + "}";
    if (text.size() > 1984 || !journal_.append(text)) {
        healthy_ = false;
        return false;
    }
    settings_ = value;
    return true;
}
bool UdpStore::clear() {
    // Durable factory-reset intent is held by the independent access journal.
    // Erasure must recover a corrupt UDP journal rather than requiring it healthy.
    healthy_ = false;
    settings_ = {};
    return flash_.erase(0) && flash_.erase(4096) && load();
}
} // namespace wsprrypico::logging
