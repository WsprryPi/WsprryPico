#include "network/bootstrap_http.hpp"

#include <cassert>
#include <cstdint>
#include <span>
#include <string_view>

using wsprrypico::network::bootstrap_http_wire;
using wsprrypico::network::HttpParser;

static std::string_view send(std::string_view request, HttpParser& parser) {
    const auto bytes =
        std::span(reinterpret_cast<const std::uint8_t*>(request.data()), request.size());
    assert(parser.receive(bytes) == bytes.size());
    assert(parser.ready() && !parser.failed());
    return parser.request().header("host");
}

int main() {
    HttpParser probe;
    assert(send("GET /hotspot-detect.html HTTP/1.1\r\nHost: captive.apple.com\r\n\r\n", probe) ==
           "captive.apple.com");
    const auto redirected = bootstrap_http_wire(probe.request(), "device-id", "firmware");
    assert(redirected.starts_with("HTTP/1.1 302 Found\r\n"));
    assert(redirected.find("Location: http://192.168.4.1/\r\n") != std::string::npos);
    assert(redirected.find("Cache-Control: no-store\r\n") != std::string::npos);
    assert(redirected.find("device-id") == std::string::npos);

    HttpParser local;
    assert(send("GET /local/v1/identity HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", local) ==
           "192.168.4.1");
    const auto identity = bootstrap_http_wire(local.request(), "device-id", "firmware");
    assert(identity.starts_with("HTTP/1.1 200 Response\r\n"));
    assert(identity.find("\"surface\":\"blank_read_only\"") != std::string::npos);

    HttpParser page_request;
    assert(send("GET / HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", page_request) == "192.168.4.1");
    const auto page = bootstrap_http_wire(page_request.request(), "device-id", "firmware");
    assert(page.find("Wi-Fi setup is not available here.") != std::string::npos);
    assert(page.find("<form") == std::string::npos);
    assert(page.find("password") == std::string::npos);

    HttpParser foreign_post;
    assert(send("POST /local/v1/identity HTTP/1.1\r\nHost: captive.apple.com\r\n"
                "Content-Length: 0\r\n\r\n",
                foreign_post) == "captive.apple.com");
    const auto rejected = bootstrap_http_wire(foreign_post.request(), "device-id", "firmware");
    assert(rejected.starts_with("HTTP/1.1 405 Response\r\n"));
    assert(rejected.find("Location:") == std::string::npos);
    return 0;
}
