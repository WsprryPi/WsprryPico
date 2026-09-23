#include "provisioning/softap_http.hpp"

#include "network/identity.hpp"
#include "wtp/json.hpp"

#include <algorithm>

namespace wsprrypico::provisioning {
namespace {
void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}

bool hex_token(std::string_view value) {
    return value.size() == 32 &&
           std::all_of(value.begin(), value.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}

network::HttpResponse http_error_for(AccessCode code) {
    switch (code) {
    case AccessCode::AuthenticationRequired:
    case AccessCode::Expired:
        return network::http_error(401, "authentication_required");
    case AccessCode::WrongDevice:
    case AccessCode::ConfirmationRequired:
        return network::http_error(403, "forbidden");
    case AccessCode::Busy:
    case AccessCode::Capacity:
    case AccessCode::Conflict:
        return network::http_error(409, "busy");
    case AccessCode::StorageFault:
    case AccessCode::BondEraseFault:
        return network::http_error(503, "access_unavailable");
    case AccessCode::Invalid:
        return network::http_error(400, "invalid_request");
    case AccessCode::Ok:
        break;
    }
    return network::http_error(400, "invalid_request");
}
} // namespace

std::string SoftApHttpResponse::wire_headers() const {
    auto headers = response.wire_headers();
    if (set_cookie.empty() || set_cookie.find_first_of("\r\n") != std::string::npos)
        return headers;
    const auto end = headers.rfind("\r\n");
    if (end == std::string::npos)
        return headers;
    headers.insert(end, "Set-Cookie: " + set_cookie + "\r\n");
    return headers;
}

SoftApHttpResponse SoftApHttpAdmission::error(AccessCode code) {
    return {http_error_for(code), {}};
}

bool SoftApHttpAdmission::same_origin(const network::HttpRequest& request, bool mutation) const {
    const auto expected = network::canonical_authority(authority_);
    const auto host = network::canonical_authority(request.header("host"));
    if (!expected || !host || *host != *expected)
        return false;
    if (!request.header("sec-fetch-site").empty() &&
        request.header("sec-fetch-site") != "same-origin" &&
        request.header("sec-fetch-site") != "none")
        return false;
    if (!mutation)
        return !request.headers.contains("origin") ||
               (request.header("origin").starts_with("https://") &&
                network::canonical_authority(request.header("origin").substr(8)) == host);
    if (!request.header("origin").starts_with("https://") ||
        network::canonical_authority(request.header("origin").substr(8)) != host)
        return false;
    return request.header("x-wsprrypico-request") == "1" &&
           request.header("content-type") == "application/json";
}

std::string_view SoftApHttpAdmission::cookie_token(const network::HttpRequest& request) {
    constexpr std::string_view prefix = "__Host-wsprrypico=";
    const auto cookie = request.header("cookie");
    if (!cookie.starts_with(prefix) || cookie.size() != prefix.size() + 32)
        return {};
    const auto token = cookie.substr(prefix.size());
    return hex_token(token) ? token : std::string_view{};
}

SoftApHttpResponse SoftApHttpAdmission::login(const network::HttpRequest& request,
                                              SoftApSurface surface,
                                              std::string_view protected_wtp_session,
                                              std::uint64_t now_ms) {
    if (surface == SoftApSurface::BlankReadOnly)
        return error(AccessCode::AuthenticationRequired);
    if (request.method != "POST" || request.path != "/local/v1/login" ||
        !same_origin(request, true))
        return error(AccessCode::Invalid);
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !wtp::json::fields(*root, {"version", "device_id", "password"}))
        return error(AccessCode::Invalid);
    const auto version = root->get("version");
    const auto device = root->get("device_id");
    const auto password_value = root->get("password");
    if (!version || version->type() != '1' || version->integer() != 1 || !device ||
        !wtp::json::identifier(*device) || !password_value || password_value->type() != '"')
        return error(AccessCode::Invalid);
    if (device->string() != device_id_)
        return error(AccessCode::WrongDevice);
    auto password = password_value->string();
    const auto admitted = valid_local_password(password)
                              ? access_.softap_login(password, now_ms, protected_wtp_session)
                              : SoftApLogin{AccessCode::AuthenticationRequired};
    clear(password);
    if (admitted.code != AccessCode::Ok)
        return error(admitted.code);
    SoftApHttpResponse response{
        network::HttpResponse{
            200, "{\"ok\":true,\"principal\":" + wtp::json::quote(admitted.principal) + "}",
            "application/json", {}},
        LocalAccessController::cookie_header(admitted.token)};
    if (response.set_cookie.empty())
        return error(AccessCode::StorageFault);
    return response;
}

SoftApHttpAuthority SoftApHttpAdmission::authorize(const network::HttpRequest& request,
                                                   SoftApSurface surface, SoftApOperation operation,
                                                   std::string_view wtp_session,
                                                   const Activity& activity, std::uint64_t now_ms,
                                                   std::string_view active_owner_session,
                                                   bool establish_session) {
    if (surface == SoftApSurface::BlankReadOnly ||
        (surface == SoftApSurface::ProvisionedPreClock &&
         operation != SoftApOperation::Hello && operation != SoftApOperation::Status &&
         operation != SoftApOperation::Time) ||
        !same_origin(request, request.method != "GET"))
        return {AccessCode::AuthenticationRequired, {}, false, {}};
    const auto token = cookie_token(request);
    if (token.empty())
        return {AccessCode::AuthenticationRequired, {}, false, {}};
    if (establish_session && !wtp_session.empty()) {
        const auto bound = access_.bind_softap_session(token, wtp_session, now_ms);
        if (bound != AccessCode::Ok)
            return {bound, {}, false, {}};
    }
    const auto admitted = access_.softap_authorize(token, operation, wtp_session,
                                                   active_owner_session, activity, now_ms);
    if (admitted.code != AccessCode::Ok)
        return {admitted.code, {}, false, {}};
    return {AccessCode::Ok,
            {true, true, true, admitted.principal},
            admitted.owner_only_grace,
            admitted.wtp_session};
}

AccessCode SoftApHttpAdmission::logout(const network::HttpRequest& request, SoftApSurface surface,
                                       std::string_view wtp_session,
                                       std::string_view active_owner_session,
                                       const Activity& activity, std::uint64_t now_ms) {
    if (surface == SoftApSurface::BlankReadOnly || request.method != "POST" ||
        request.path != "/local/v1/logout" || !same_origin(request, true))
        return AccessCode::AuthenticationRequired;
    const auto token = cookie_token(request);
    if (token.empty())
        return AccessCode::AuthenticationRequired;
    return access_.softap_logout(token, wtp_session, active_owner_session, activity, now_ms);
}

} // namespace wsprrypico::provisioning
