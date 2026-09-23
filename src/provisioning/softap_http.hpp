#pragma once

#include "network/http.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/local_access.hpp"

#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::provisioning {

struct SoftApHttpAuthority {
    AccessCode code = AccessCode::Invalid;
    Authorization authorization;
    bool owner_only_grace = false;
    std::string wtp_session;
};

struct SoftApHttpResponse {
    network::HttpResponse response;
    std::string set_cookie;
    std::string wire_headers() const;
};

class SoftApHttpAdmission {
  public:
    SoftApHttpAdmission(LocalAccessController& access, std::string device_id,
                        std::string authority)
        : access_(access), device_id_(std::move(device_id)),
          authority_(std::move(authority)) {}

    SoftApHttpResponse login(const network::HttpRequest& request, SoftApSurface surface,
                             std::string_view protected_wtp_session, std::uint64_t now_ms);
    SoftApHttpAuthority authorize(const network::HttpRequest& request, SoftApSurface surface,
                                  SoftApOperation operation, std::string_view wtp_session,
                                  const Activity& activity, std::uint64_t now_ms,
                                  std::string_view active_owner_session = {},
                                  bool establish_session = false);
    AccessCode logout(const network::HttpRequest& request, SoftApSurface surface,
                      std::string_view wtp_session, std::string_view active_owner_session,
                      const Activity& activity, std::uint64_t now_ms);

  private:
    bool same_origin(const network::HttpRequest& request, bool mutation) const;
    static std::string_view cookie_token(const network::HttpRequest& request);
    static SoftApHttpResponse error(AccessCode code);

    LocalAccessController& access_;
    std::string device_id_;
    std::string authority_;
};

} // namespace wsprrypico::provisioning
