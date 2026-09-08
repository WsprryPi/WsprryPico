#include "network/http.hpp"

#include "network/assets.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <charconv>

namespace wsprrypico::network {
std::string_view HttpRequest::header(std::string_view name) const {
    auto it = headers.find(std::string(name));
    return it == headers.end() ? std::string_view{} : it->second;
}
HttpResponse http_error(unsigned status, std::string_view code) {
    return {
        status, "{\"error\":{\"code\":" + wtp::json::quote(code) + "}}", "application/json", {}};
}
std::string HttpResponse::wire() const {
    return "HTTP/1.1 " + std::to_string(status) + " Response\r\nContent-Type: " + type +
           "\r\nContent-Length: " + std::to_string(body.size()) +
           "\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n"
           "Content-Security-Policy: " +
           std::string(web_csp()) + "\r\nReferrer-Policy: no-referrer\r\n" +
           (etag.empty() ? "" : "ETag: " + etag + "\r\n") + "\r\n" + body;
}
void HttpParser::parse_headers() {
    const auto end = headers_.find("\r\n");
    const auto line = std::string_view(headers_).substr(0, end);
    const auto first = line.find(' '), last = line.rfind(' ');
    if (first == line.npos || first == last || line.substr(last) != " HTTP/1.1") {
        failed_ = true;
        return;
    }
    request_.method = line.substr(0, first);
    request_.path = line.substr(first + 1, last - first - 1);
    if ((request_.method != "GET" && request_.method != "PUT" && request_.method != "POST") ||
        request_.path.empty() || request_.path.front() != '/' ||
        request_.path.find_first_of(" %?#\\") != request_.path.npos) {
        failed_ = true;
        return;
    }
    std::size_t pos = end + 2;
    while (pos < headers_.size() - 2) {
        const auto next = headers_.find("\r\n", pos);
        const auto field = std::string_view(headers_).substr(pos, next - pos);
        const auto colon = field.find(':');
        if (colon == field.npos || colon == 0) {
            failed_ = true;
            return;
        }
        std::string name(field.substr(0, colon));
        for (auto& c : name) {
            if (c >= 'A' && c <= 'Z')
                c += 'a' - 'A';
            if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
                failed_ = true;
                return;
            }
        }
        auto value = field.substr(colon + 1);
        while (!value.empty() && value.front() == ' ')
            value.remove_prefix(1);
        while (!value.empty() && value.back() == ' ')
            value.remove_suffix(1);
        if (!request_.headers.emplace(name, value).second) {
            failed_ = true;
            return;
        }
        pos = next + 2;
    }
    if (request_.header("host").empty() || request_.headers.contains("transfer-encoding") ||
        request_.headers.contains("expect") || request_.headers.contains("upgrade")) {
        failed_ = true;
        return;
    }
    auto length = request_.header("content-length");
    if (!length.empty()) {
        const auto result =
            std::from_chars(length.data(), length.data() + length.size(), content_length_);
        if (result.ec != std::errc{} || result.ptr != length.data() + length.size() ||
            content_length_ > max_http_body) {
            failed_ = true;
            return;
        }
    } else if (request_.method != "GET" || request_.headers.contains("content-length")) {
        failed_ = true;
        return;
    }
    if (request_.method == "GET" && content_length_) {
        failed_ = true;
        return;
    }
    if (!wtp::memory_admitted(content_length_)) {
        exhausted_ = failed_ = true;
        return;
    }
    request_.body.reserve(content_length_);
    headers_done_ = true;
    ready_ = content_length_ == 0;
}
std::size_t HttpParser::receive(std::span<const std::uint8_t> bytes) {
    std::size_t used = 0;
    for (auto c : bytes) {
        if (ready_ || failed_) {
            failed_ = true;
            break;
        }
        ++used;
        if (!headers_done_) {
            if (headers_.size() >= max_http_headers || c > 126 ||
                (c < 32 && c != '\r' && c != '\n')) {
                failed_ = true;
                break;
            }
            headers_ += static_cast<char>(c);
            // Reject bare LF and CR followed by anything except LF.
            const auto n = headers_.size();
            if ((c == '\n' && (n < 2 || headers_[n - 2] != '\r')) ||
                (n > 1 && headers_[n - 2] == '\r' && c != '\n')) {
                failed_ = true;
                break;
            }
            if (headers_.ends_with("\r\n\r\n"))
                parse_headers();
        } else {
            request_.body += static_cast<char>(c);
            ready_ = request_.body.size() == content_length_;
        }
    }
    return used;
}
} // namespace wsprrypico::network
