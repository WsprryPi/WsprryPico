#pragma once
#include "wtp/frame_buffer.hpp"
#include "wtp/output_buffer.hpp"

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace wsprrypico::network {
inline constexpr std::size_t max_http_headers = 2048, max_http_body = 32768;
struct HttpRequest {
    std::string method, path, body;
    std::map<std::string, std::string> headers;
    // Parsed bodies retain paged storage when requests are copied. Direct host
    // API callers may still supply body; a parsed body takes precedence.
    std::shared_ptr<wtp::FrameBuffer> buffered_body{};
    wtp::InputView body_view() const {
        return buffered_body ? buffered_body->view() : wtp::InputView(body);
    }
    std::string_view header(std::string_view name) const;
};
struct HttpResponse {
    unsigned status = 200;
    std::string body;
    std::string type = "application/json";
    std::string etag;
    wtp::OutputBuffer buffered_body{};
    // Generated browser assets have static storage duration. Borrowing those
    // bytes lets the target stream them from flash without a same-size heap
    // copy while another authenticated connection remains active.
    std::string_view static_body{};
    // Optional response cookie owned by trusted application code. The wire
    // encoder rejects control characters before emitting it.
    std::string set_cookie{};
    std::size_t body_size() const {
        if (!static_body.empty())
            return static_body.size();
        return buffered_body.empty() ? body.size() : buffered_body.size();
    }
    std::span<const std::uint8_t> body_at(std::size_t offset) const {
        if (!static_body.empty())
            return std::span(reinterpret_cast<const std::uint8_t*>(static_body.data()),
                             static_body.size())
                .subspan(offset);
        if (!buffered_body.empty())
            return buffered_body.at(offset);
        return std::span(reinterpret_cast<const std::uint8_t*>(body.data()), body.size())
            .subspan(offset);
    }
    // Convenience for host consumers. Target transport streams body_at pages.
    std::string body_text() const;
    std::string wire_headers() const;
    std::string wire() const;
};
// One request per TLS connection. The owner enforces a total connection deadline.
class HttpParser {
  public:
    std::size_t receive(std::span<const std::uint8_t> bytes);
    void reset_secure();
    bool ready() const {
        return ready_;
    }
    bool exhausted() const {
        return exhausted_;
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
    bool exhausted_ = false;
    bool headers_done_ = false, ready_ = false, failed_ = false;
};
HttpResponse http_error(unsigned status, std::string_view code);
} // namespace wsprrypico::network
