#pragma once

#include "network/api.hpp"
#include "provisioning/softap_http.hpp"
#include "time/controller_time.hpp"

#include <array>

namespace wsprrypico::network {

// Interface-confined adapter for Safari on the device SoftAP. It reuses the
// browser API and JobService after cookie admission; it is not another job API.
class SoftApApi {
  public:
    SoftApApi(BrowserApi& browser, provisioning::SoftApHttpAdmission& admission,
              provisioning::LocalAccessController& access, time::ControllerTimeArbiter& time,
              wtp::JobService& service, std::string device, std::string firmware)
        : browser_(browser), admission_(admission), access_(access), time_(time), service_(service),
          device_(std::move(device)), firmware_(std::move(firmware)) {}

    HttpResponse handle(const HttpRequest& request, provisioning::SoftApSurface surface,
                        std::string_view authority, std::uint64_t now_ms,
                        std::uint64_t transaction);
    void finish_request(std::uint64_t transaction, bool apply);

  private:
    struct PendingTime {
        std::uint64_t transaction = 0;
        std::string principal;
        std::string session;
        bool live = false;
    };

    provisioning::Activity activity() const;
    HttpResponse identity(provisioning::SoftApSurface surface) const;
    HttpResponse local_status(std::string_view principal, std::string_view wtp_session,
                              provisioning::SoftApSurface surface) const;
    HttpResponse challenge(const HttpRequest& request, std::string_view principal,
                           std::string_view session, std::uint64_t transaction);
    HttpResponse submit_time(const HttpRequest& request, std::string_view principal,
                             std::string_view session);
    static HttpResponse access_error(provisioning::AccessCode code);
    static provisioning::SoftApOperation operation(const HttpRequest& request, std::string& session,
                                                   bool& valid);
    static std::string_view surface_name(provisioning::SoftApSurface surface);

    BrowserApi& browser_;
    provisioning::SoftApHttpAdmission& admission_;
    provisioning::LocalAccessController& access_;
    time::ControllerTimeArbiter& time_;
    wtp::JobService& service_;
    std::string device_;
    std::string firmware_;
    std::array<PendingTime, 2> pending_time_{};
};

} // namespace wsprrypico::network
