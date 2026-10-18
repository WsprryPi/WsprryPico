#pragma once

#include "network/http.hpp"
#include "wtp/job_service.hpp"
#include "wtp/json.hpp"

#include <functional>

namespace wsprrypico::usb {
// USB-local adapter only. Its transaction is owned by ManagementEndpoint;
// failed delivery, connection closure, reclamation and timeout cancel the hold.
class Maintenance {
  public:
    Maintenance(wtp::JobService& service, std::string device, std::string boot,
                std::function<bool()> ready, std::function<bool()> idle,
                std::function<std::string()> revision, std::function<std::string()> watermark,
                std::function<bool()> enter)
        : service_(service), device_(std::move(device)), boot_(std::move(boot)),
          ready_(std::move(ready)), idle_(std::move(idle)), revision_(std::move(revision)),
          watermark_(std::move(watermark)), enter_(std::move(enter)) {}

    network::HttpResponse handle(const network::HttpRequest& request, std::uint64_t transaction) {
        using namespace wtp;
        if (request.method == "GET" && request.path == "/api/usb/v1/maintenance")
            return {200, std::string("{\"schema\":\"transmitter-usb-maintenance/1\",\"phase\":\"") +
                         (service_.update_verification() ? "verification" : service_.maintenance() ? "pending" : "idle") +
                         "\"}", "application/json", revision_()};
        const auto body = json::parse(request.body_view());
        if (request.method != "POST" || !transaction || !body ||
            !json::fields(*body, {"schema", "target", "confirmed", "watermark_utc_ns"}) ||
            body->get("schema")->string() != "transmitter-usb-maintenance/1" ||
            body->get("confirmed")->raw != "true" ||
            !json::fields(*body->get("target"), {"scope", "device_id", "boot_id"}) ||
            body->get("target")->get("scope")->string() != "member" ||
            body->get("target")->get("device_id")->string() != device_ ||
            body->get("target")->get("boot_id")->string() != boot_ ||
            body->get("watermark_utc_ns")->type() != '"')
            return network::http_error(400, "invalid_usb_maintenance_request");
        if (request.header("if-match").empty())
            return network::http_error(428, "revision_required");
        if (request.header("if-match") != revision_() ||
            body->get("watermark_utc_ns")->string() != watermark_())
            return network::http_error(412, "revision_conflict");
        const bool finishing = request.path == "/api/usb/v1/maintenance/finish";
        if (pending_ || !ready_() || (finishing ? (!service_.update_verification() || !service_.verification_safe()) :
                                    (!idle_() || !service_.begin_maintenance())))
            return network::http_error(409, "usb_maintenance_unavailable");
        finishing_ = finishing;
        pending_ = transaction;
        revision_at_request_ = revision_();
        watermark_at_request_ = watermark_();
        return {202, "{\"requested\":true}", "application/json", revision_at_request_};
    }

    void finish(std::uint64_t transaction, bool delivered) {
        if (!pending_ || transaction != pending_)
            return;
        pending_ = 0;
        if (delivered && service_.maintenance() && service_.verification_safe() && ready_() &&
            revision_() == revision_at_request_ && watermark_() == watermark_at_request_) {
            if (finishing_)
                service_.finish_update_verification();
            else if (enter_())
                return; // Keep the bounded hold while the target drains ACK and resets.
        }
        service_.end_maintenance(); // Also runs if target callback refuses to reset.
        revision_at_request_.clear();
        watermark_at_request_.clear();
    }

  private:
    wtp::JobService& service_;
    std::string device_, boot_;
    std::function<bool()> ready_, idle_;
    std::function<std::string()> revision_, watermark_;
    std::function<bool()> enter_;
    std::uint64_t pending_ = 0;
    bool finishing_ = false;
    std::string revision_at_request_, watermark_at_request_;
};
} // namespace wsprrypico::usb
