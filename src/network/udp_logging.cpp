// SPDX-License-Identifier: MIT
#include "application/resources.hpp"
#include "network/api.hpp"
namespace wsprrypico::network {
HttpResponse BrowserApi::udp_logging_resource(const HttpRequest& r) {
    if (!udp_store_ || !udp_sender_)
        return http_error(404, "unsupported_udp_logging");
    const auto target = application::target(device_, service_.status().boot_id);
    const auto revision = [&] {
        return "\"udp-" + service_.status().boot_id + "-" + std::to_string(udp_store_->sequence()) +
               "\"";
    };
    if (r.path == "/api/control/v1/udp-logging/test/capabilities") {
        if (r.method != "GET")
            return http_error(405, "method_not_allowed");
        HttpResponse out;
        out.body =
            "{\"schema\":\"udp-logging-test-capabilities\",\"target\":" + target +
            ",\"resource\":\"/api/control/v1/udp-logging/test\",\"request_schema\":\"udp-logging-test\",\"event_code\":\"UDP_TEST\",\"maximum_rate\":2}";
        return out;
    }
    if (r.path == "/api/control/v1/udp-logging/test") {
        if (r.body_view().size() > 2048)
            return http_error(413, "body_too_large");
        if (r.method != "POST")
            return http_error(405, "method_not_allowed");
        if (!udp_store_->healthy() || !logger_)
            return http_error(503, "udp_logging_unavailable");
        if (r.header("if-match").empty())
            return http_error(428, "revision_required");
        if (r.header("if-match") != revision())
            return http_error(412, "revision_conflict");
        if (!scheduler_.idle() || pending_transaction_)
            return http_error(409, "busy");
        const auto root = wtp::json::parse(r.body_view(), 8);
        if (!root || !wtp::json::fields(*root, {"schema", "target"}) ||
            root->get("schema")->type() != '"' ||
            root->get("schema")->string() != "udp-logging-test")
            return http_error(400, "invalid_udp_test");
        const auto t = *root->get("target");
        if (!wtp::json::fields(t, {"scope", "device_id", "boot_id"}) ||
            t.get("scope")->type() != '"' || t.get("device_id")->type() != '"' ||
            t.get("boot_id")->type() != '"' || t.get("scope")->string() != "member" ||
            t.get("device_id")->string() != device_ ||
            t.get("boot_id")->string() != service_.status().boot_id)
            return http_error(409, "udp_test_target_changed");
        const auto& settings = udp_sender_->settings();
        bool selected = settings.event_count == 0;
        for (std::size_t i = 0; i < settings.event_count; ++i)
            selected |= settings.event_codes[i].view() == "UDP_TEST";
        if (!settings.enabled || settings.maximum_severity < 5 || !selected)
            return http_error(409, "udp_test_filtered_or_disabled");
        const auto clock = service_.clock_snapshot();
        if (udp_test_at_ && (clock.monotonic_now_ns < *udp_test_at_ ||
                             clock.monotonic_now_ns - *udp_test_at_ < 500'000'000ULL))
            return http_error(429, "udp_test_rate_limited");
        udp_test_at_ = clock.monotonic_now_ns;
        const auto before = udp_sender_->queued();
        logger_->event(5, "UDP_TEST", "UDP logging test event", clock.monotonic_now_ns,
                       clock.state == wtp::ClockState::Unsynchronized ? 0 : clock.utc_now_ns);
        HttpResponse out;
        out.body = "{\"schema\":\"udp-logging-test\",\"target\":" + target +
                   ",\"accepted\":" + (udp_sender_->queued() > before ? "true" : "false") +
                   ",\"receipt\":\"unknown\"}";
        return out;
    }
    if (r.path.ends_with("/capabilities")) {
        if (r.method != "GET")
            return http_error(405, "method_not_allowed");
        HttpResponse result;
        result.body =
            "{\"schema\":\"udp-logging-capabilities\",\"target\":" + target +
            ",\"resource\":\"/api/control/v1/"
            "udp-logging\",\"settings_schema\":\"udp-logging\",\"wire_schema\":\"wsprry-udp/1\","
            "\"limits\":{\"payload_bytes\":480,\"queue_records\":16,\"maximum_sources\":0,"
            "\"maximum_peers\":0,\"maximum_rate\":8,\"maximum_burst\":16,\"address_"
            "family\":\"ipv4\"}}";
        return result;
    }
    if (!udp_store_->healthy())
        return http_error(503, "udp_logging_storage_fault");
    const auto tag = [&] {
        return "\"udp-" + service_.status().boot_id + "-" + std::to_string(udp_store_->sequence()) +
               "\"";
    };
    if (r.method == "PUT") {
        if (r.body_view().size() > 2048)
            return http_error(413, "body_too_large");
        if (r.header("if-match").empty())
            return http_error(428, "revision_required");
        if (r.header("if-match") != tag())
            return http_error(412, "revision_conflict");
        if (!scheduler_.idle() || pending_transaction_)
            return http_error(409, "busy");
        const auto root = wtp::json::parse(r.body_view(), 8);
        if (!root || application::validate_envelope(*root, "udp-logging", "settings",
                                                    device_, service_.status().boot_id) !=
                         application::Envelope::Valid)
            return http_error(400, "invalid_udp_logging_target_or_resource");
        const auto settings = logging::parse_udp_settings(*root->get("settings"));
        if (!settings)
            return http_error(400, "invalid_udp_logging_settings");
        if (settings->destination_ipv4.size &&
            (settings->enabled ||
             settings->destination_ipv4.view() != udp_store_->settings().destination_ipv4.view()) &&
            !network_.udp_destination_allowed(settings->destination_ipv4.view()))
            return http_error(400, "invalid_udp_logging_destination");
        if (!udp_store_->save(*settings)) {
            (void)udp_sender_->configure(logging::UdpSettings{});
            return http_error(503, "udp_logging_save_unconfirmed");
        }
        (void)udp_sender_->configure(*settings);
    } else if (r.method != "GET")
        return http_error(405, "method_not_allowed");
    HttpResponse result;
    result.status = 200;
    result.type = "application/json";
    result.etag = tag();
    result.body = "{\"schema\":\"udp-logging\",\"target\":" + target +
                  ",\"saved\":" + logging::udp_settings_json(udp_store_->settings()) +
                  ",\"active\":" + logging::udp_active_json(*udp_sender_, tag()) + "}";
    return result;
}
} // namespace wsprrypico::network
