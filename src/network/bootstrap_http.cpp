#include "network/bootstrap_http.hpp"

#include "wtp/json.hpp"

namespace wsprrypico::network {
std::string bootstrap_http_wire(const HttpRequest& request, std::string_view device,
                                std::string_view firmware) {
    if (request.method != "GET")
        return http_error(405, "read_only").wire();
    if (request.header("host") != "192.168.4.1") {
        // Captive probes retain their original Host. Redirect safe GETs only.
        return "HTTP/1.1 302 Found\r\nLocation: http://192.168.4.1/\r\n"
               "Content-Length: 0\r\nConnection: close\r\nCache-Control: no-store\r\n"
               "Referrer-Policy: no-referrer\r\n\r\n";
    }
    if (request.path == "/local/v1/identity")
        return HttpResponse{200,
                            "{\"version\":1,\"device_id\":" + wtp::json::quote(device) +
                                ",\"firmware\":" + wtp::json::quote(firmware) +
                                ",\"surface\":\"blank_read_only\",\"authenticated\":false}",
                            "application/json",
                            {}}
            .wire();
    if (request.path == "/")
        return HttpResponse{200,
                            "<!doctype html><meta charset=utf-8><meta name=viewport "
                            "content=\"width=device-width,initial-scale=1\"><title>WsprryPico "
                            "recovery</title><h1>WsprryPico recovery</h1><p>This device has no "
                            "authenticated server identity. This page is read-only. Provision it "
                            "over encrypted BLE or USB before entering any credential.</p><p>"
                            "Device: <code>" +
                                std::string(device) + "</code></p><p>Firmware: <code>" +
                                std::string(firmware) + "</code></p>",
                            "text/html; charset=utf-8",
                            {}}
            .wire();
    return http_error(404, "not_found").wire();
}
} // namespace wsprrypico::network
