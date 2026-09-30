#include "network/assets.hpp"
#include "network/bootstrap_http.hpp"

#include <algorithm>
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

    const auto setup = wsprrypico::network::bootstrap_http_response(page_request.request(),
                                                                    "device-id", "firmware", true);
    assert(setup.status == 200 && setup.static_body.find("wifi-form") != std::string_view::npos);
    assert(setup.static_body.find("<style>") != std::string_view::npos);
    assert(setup.static_body.find("rel=\"stylesheet\"") == std::string_view::npos);
    assert(setup.wire_headers().find("Cache-Control: no-store") != std::string::npos);
    assert(setup.wire_headers().find("style-src 'self' 'sha256-") != std::string::npos);
    const auto owner_root = wsprrypico::network::bootstrap_http_response(
        page_request.request(), "device-id", "firmware", false, true);
    assert(owner_root.status == 200 &&
           owner_root.static_body.find("owner-form") != std::string_view::npos);
    assert(owner_root.static_parts.size() == 6);
    assert(owner_root.body_text().find("<script src=") == std::string::npos);
    const auto captive_setup = wsprrypico::network::bootstrap_http_response(
        page_request.request(), "device-id", "firmware", true, true);
    assert(captive_setup.status == 200 &&
           captive_setup.static_body.find("wifi-form") != std::string_view::npos);
    assert(captive_setup.static_body.find("owner-callsign") == std::string_view::npos);
    assert(captive_setup.static_body.find("BOOTSEL") == std::string_view::npos);

    HttpParser station_request;
    send("GET /owner.html HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", station_request);
    const auto station_page = wsprrypico::network::bootstrap_http_response(
        station_request.request(), "device-id", "firmware", true, true);
    assert(station_page.status == 200 &&
           station_page.static_body.find("owner-callsign") != std::string_view::npos);
    assert(station_page.static_body.find("owner-password") == std::string_view::npos);
    assert(station_page.static_body.find("rel=\"stylesheet\"") == std::string_view::npos);
    const auto style_start = station_page.static_body.find("<style>");
    const auto style_end = station_page.static_body.find("</style>", style_start);
    assert(style_start != std::string_view::npos && style_end != std::string_view::npos);
    assert(station_page.static_body.substr(style_start + 7, style_end - style_start - 7) ==
           wsprrypico::network::bootstrap_asset("/style.css")->body);
    assert(station_page.content_security_policy == setup.content_security_policy);
    assert(setup.static_parts.size() == 4 && setup.body.empty() && setup.buffered_body.empty());
    assert(setup.body_text().find("<script src=") == std::string::npos);
    assert(setup.static_body.find("href=\"/owner.html\"") != std::string_view::npos);
    assert(station_page.body.empty() && station_page.buffered_body.empty());
    std::string station_delivered;
    for (std::size_t offset = 0; offset < station_page.body_size();) {
        const auto bytes = station_page.body_at(offset);
        assert(!bytes.empty());
        const auto count = std::min<std::size_t>(1024, bytes.size());
        station_delivered.append(reinterpret_cast<const char*>(bytes.data()), count);
        offset += count;
    }
    assert(station_delivered == station_page.body_text());
    assert(station_page.body_at(station_page.body_size()).empty());
    assert(station_delivered.ends_with("</script></body>\n</html>\n"));
    assert(station_page.wire_headers().find(
               "Content-Length: " + std::to_string(station_delivered.size())) != std::string::npos);
    const auto key_script = wsprrypico::network::bootstrap_asset("/owner-key-bundle.js")->body;
    const auto app_script = wsprrypico::network::bootstrap_asset("/owner-bundle.js")->body;
    assert(station_delivered.find(key_script) < station_delivered.find(app_script));

    HttpParser owner_script_request;
    send("GET /owner-key-bundle.js HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", owner_script_request);
    const auto owner_script = wsprrypico::network::bootstrap_http_response(
        owner_script_request.request(), "device-id", "firmware", false, true);
    assert(owner_script.status == 200 && owner_script.static_body.size() > 30000);
    assert(wsprrypico::network::bootstrap_http_response(owner_script_request.request(), "device-id",
                                                        "firmware")
               .status == 404);

    HttpParser bundle_request;
    assert(send("GET /bundle.js HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", bundle_request) ==
           "192.168.4.1");
    const auto bundle = wsprrypico::network::bootstrap_http_response(bundle_request.request(),
                                                                     "device-id", "firmware");
    const auto asset = wsprrypico::network::bootstrap_asset("/bundle.js");
    assert(asset && asset->body.size() > 50000);
    assert(bundle.status == 200 && bundle.static_body.data() == asset->body.data());
    assert(bundle.body.empty() && bundle.buffered_body.empty());
    assert(bundle.body_size() == asset->body.size());
    assert(bundle.wire_headers().find("Content-Length: " + std::to_string(asset->body.size())) !=
           std::string::npos);
    assert(bundle.wire_headers().find("script-src 'self'") != std::string::npos);
    std::string delivered;
    for (std::size_t offset = 0; offset < bundle.body_size();) {
        const auto chunk = bundle.body_at(offset).first(
            std::min<std::size_t>(1024, bundle.body_at(offset).size()));
        delivered.append(reinterpret_cast<const char*>(chunk.data()), chunk.size());
        offset += chunk.size();
    }
    assert(delivered == asset->body);

    HttpParser hidden_form;
    send("GET /index.html HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n", hidden_form);
    const auto owner_alias = wsprrypico::network::bootstrap_http_response(
        hidden_form.request(), "device-id", "firmware", false, true);
    assert(owner_alias.status == 200 &&
           owner_alias.static_body.find("owner-form") != std::string_view::npos);
    assert(
        wsprrypico::network::bootstrap_http_response(hidden_form.request(), "device-id", "firmware")
            .status == 404);

    HttpParser foreign_post;
    assert(send("POST /local/v1/identity HTTP/1.1\r\nHost: captive.apple.com\r\n"
                "Content-Length: 0\r\n\r\n",
                foreign_post) == "captive.apple.com");
    const auto rejected = bootstrap_http_wire(foreign_post.request(), "device-id", "firmware");
    assert(rejected.starts_with("HTTP/1.1 405 Response\r\n"));
    assert(rejected.find("Location:") == std::string::npos);
    return 0;
}
