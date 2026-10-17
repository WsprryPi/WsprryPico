#pragma once
#include "network/api.hpp"

namespace wsprrypico::network {
// This adapter is instantiated only by the physically selected USB endpoint.
// Its caller enforces access-journal/reset admission and boot/session/target
// binding. Network transports never select this carrier or principal.
class LocalUsbApi {
  public:
    explicit LocalUsbApi(BrowserApi& api) : api_(api) {}
    HttpResponse handle(const HttpRequest& request, std::uint64_t transaction = 0) {
        if (!request.path.starts_with("/api/v1/") && !request.path.starts_with("/api/usb/v1/"))
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
