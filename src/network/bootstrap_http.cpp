#include "network/bootstrap_http.hpp"

#include "network/assets.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::network {
HttpResponse bootstrap_http_response(const HttpRequest& request, std::string_view device,
                                     std::string_view firmware, bool setup_enabled) {
    if (request.method != "GET")
        return http_error(405, "read_only");
    if (request.header("host") != "192.168.4.1") {
        // Captive probes retain their original Host. Redirect safe GETs only.
        HttpResponse response{302, "", "text/plain; charset=utf-8", {}};
        response.location = "http://192.168.4.1/";
        response.content_security_policy = bootstrap_csp();
        return response;
    }
    if (request.path == "/local/v1/identity")
        return HttpResponse{200,
                            "{\"version\":1,\"device_id\":" + wtp::json::quote(device) +
                                ",\"firmware\":" + wtp::json::quote(firmware) +
                                ",\"surface\":\"blank_read_only\",\"authenticated\":false}",
                            "application/json",
                            {}};
    if ((setup_enabled && (request.path == "/" || request.path == "/index.html")) ||
        request.path == "/style.css" || request.path == "/bundle.js") {
        const auto asset = bootstrap_asset(request.path == "/" ? "/index.html" : request.path);
        if (!asset)
            return http_error(404, "not_found");
        HttpResponse response{200, "", std::string(asset->type), {}};
        response.static_body = asset->body;
        response.content_security_policy = bootstrap_csp();
        return response;
    }
    if (request.path == "/")
        return HttpResponse{200,
                            "<!doctype html><meta charset=utf-8><meta name=viewport "
                            "content=\"width=device-width,initial-scale=1\"><title>WsprryPico "
                            "recovery</title><h1>WsprryPico recovery</h1><p>Connected to "
                            "WsprryPico. This page shows device identity only. Wi-Fi setup is "
                            "not available here.</p><p>"
                            "Device: <code>" +
                                std::string(device) + "</code></p><p>Firmware: <code>" +
                                std::string(firmware) + "</code></p>",
                            "text/html; charset=utf-8",
                            {}};
    return http_error(404, "not_found");
}

std::string bootstrap_http_wire(const HttpRequest& request, std::string_view device,
                                std::string_view firmware) {
    return bootstrap_http_response(request, device, firmware).wire();
}
} // namespace wsprrypico::network
