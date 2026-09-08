#pragma once
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace wsprrypico::network {
inline constexpr std::size_t max_http_headers = 2048, max_http_body = 32768;
struct HttpRequest {
    std::string method, path, body;
    std::map<std::string, std::string> headers;
    std::string_view header(std::string_view name) const;
};
struct HttpResponse {
    unsigned status = 200;
    std::string body;
    std::string type = "application/json";
    std::string etag;
    std::string wire() const;
};
// One request per TLS connection. The owner enforces a total connection deadline.
class HttpParser {
  public:
    std::size_t receive(std::span<const std::uint8_t> bytes);
    bool ready() const {
        return ready_;
    }
    bool failed() const {
        return failed_;
    }
    const HttpRequest& request() const {
        return request_;
    }

  private:
    void parse_headers();
    HttpRequest request_;
    std::string headers_;
    std::size_t content_length_ = 0;
    bool headers_done_ = false, ready_ = false, failed_ = false;
};
HttpResponse http_error(unsigned status, std::string_view code);
} // namespace wsprrypico::network
