#pragma once
#include "network/api.hpp"
#include "network/control.hpp"
#include <optional>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::network {
// Shared by the physical endpoint and software production-path driver. The
// owner defers its existing AP action until this transaction's delivery ACK.
// This validates an AP request; acceptance never asserts that AP is active.
inline HttpResponse local_usb_ap_request(const HttpRequest& request, std::string_view device,
                                        std::string_view boot, const std::string& revision,
                                        bool available) {
    auto payload = control_payload(request.body_view());
    std::string bytes = payload ? std::move(*payload) : std::string{};
    ControlStringWiper wipe(bytes);
    const auto root = payload ? execution::json::parse(bytes) : std::nullopt;
    if (request.path != "/api/usb/v1/ap" || request.method != "POST" || !root ||
        !execution::json::fields(*root, {"schema", "target"}) ||
        root->get("schema")->type() != '"' || root->get("schema")->string() != "ap-request" ||
        !execution::json::fields(*root->get("target"), {"scope", "device_id", "boot_id"}) ||
        root->get("target")->get("scope")->type() != '"' ||
        root->get("target")->get("device_id")->type() != '"' ||
        root->get("target")->get("boot_id")->type() != '"' ||
        root->get("target")->get("scope")->string() != "member" ||
        root->get("target")->get("device_id")->string() != device ||
        root->get("target")->get("boot_id")->string() != boot)
        return http_error(400, "invalid_ap_request");
    if (request.header("if-match") != revision)
        return http_error(412, "revision_conflict");
    if (!available)
        return http_error(409, "ap_unavailable");
    return control_response(HttpResponse{202, "{\"requested\":true}", "application/json", revision});
}
// This adapter is instantiated only by the physically selected USB endpoint.
// Its caller enforces access-journal/reset admission and boot/session/target
// binding. Network transports never select this carrier or principal.
class LocalUsbApi {
  public:
    explicit LocalUsbApi(BrowserApi& api) : api_(api) {}
    HttpResponse handle(const HttpRequest& request, std::uint64_t transaction = 0) {
        if (!request.path.starts_with("/api/control/v1/") && !request.path.starts_with("/api/usb/v1/"))
            return http_error(404, "not_found");
        return api_.handle(request, "usb-physical", "", transaction,
                           ManagementCarrier::UsbPhysical);
    }
    void finish(std::uint64_t transaction, bool delivered) {
        api_.finish_request(transaction, delivered);
    }

  private:
    BrowserApi& api_;
};
} // namespace wsprrypico::network
