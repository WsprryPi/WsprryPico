#include "usb/management_endpoint.hpp"

#include "application/resources.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::usb {
namespace {
constexpr std::string_view schema = "usb-management/1";
std::string_view quoted_byte(unsigned char c, std::array<char, 6>& scratch) {
    if (c == '"')
        return "\\\"";
    if (c == '\\')
        return "\\\\";
    if (c < 32) {
        constexpr char hex[] = "0123456789abcdef";
        scratch = {'\\', 'u', '0', '0', hex[c >> 4], hex[c & 15]};
        return {scratch.data(), scratch.size()};
    }
    scratch[0] = static_cast<char>(c);
    return {scratch.data(), 1};
}
} // namespace

std::string ManagementEndpoint::target() const {
    return application::target(device_, boot_);
}
void ManagementEndpoint::clear_input() {
    input_ = {};
    expected_ = header_size_ = 0;
}
void ManagementEndpoint::disconnect() {
    if (pending_)
        finish_(transaction_, false);
    pending_ = false;
    clear_input();
    output_ = {};
    output_offset_ = 0;
    timing_ = negotiated_ = false;
    closed_ = true;
    session_.clear();
}
void ManagementEndpoint::connect(std::string session) {
    disconnect();
    if (session.size() != 32 ||
        !std::all_of(session.begin(), session.end(),
                     [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }) ||
        generation_ == 0x3fffffffULL)
        return;
    ++generation_;
    last_id_ = 0;
    session_ = std::move(session);
    closed_ = false;
}
void ManagementEndpoint::poll(std::uint64_t now_ms) {
    if (timing_ && (now_ms < started_ms_ || now_ms - started_ms_ >= transaction_timeout_ms))
        disconnect();
}
bool ManagementEndpoint::binding(wtp::json::Value value) const {
    const auto session = value.get("session"), destination = value.get("target");
    if (!session || session->type() != '"' || session->string() != session_ || !destination ||
        !wtp::json::fields(*destination, {"scope", "device_id", "boot_id"}))
        return false;
    for (const auto name : {"scope", "device_id", "boot_id"})
        if (destination->get(name)->type() != '"')
            return false;
    return destination->get("scope")->string() == "member" &&
           destination->get("device_id")->string() == device_ &&
           destination->get("boot_id")->string() == boot_;
}
bool ManagementEndpoint::respond(unsigned status, network::HttpResponse response, bool delivery) {
    const auto prefix = "{\"schema\":\"usb-management/1\",\"id\":" + std::to_string(last_id_) +
                        ",\"status\":" + std::to_string(status) +
                        ",\"session\":" + wtp::json::quote(session_) + ",\"target\":" + target() +
                        ",\"body\":\"";
    const auto suffix = "\",\"etag\":" + wtp::json::quote(response.etag) +
                        ",\"delivery_required\":" + (delivery ? "true}" : "false}");
    std::size_t length = prefix.size() + suffix.size();
    std::array<char, 6> escaped{};
    for (std::size_t offset = 0; offset < response.body_size();) {
        const auto part = response.body_at(offset);
        for (auto c : part)
            length += quoted_byte(c, escaped).size();
        offset += part.size();
    }
    if (length > maximum_response || !wtp::memory_admitted(length, memory_reserve) ||
        !output_.reserve(length))
        return false;
    const auto append = [&](std::string_view text) {
        return output_.append({reinterpret_cast<const std::uint8_t*>(text.data()), text.size()});
    };
    if (!append(prefix))
        return false;
    for (std::size_t offset = 0; offset < response.body_size();) {
        const auto part = response.body_at(offset);
        for (auto c : part)
            if (!append(quoted_byte(c, escaped)))
                return false;
        offset += part.size();
    }
    if (!append(suffix))
        return false;
    output_header_ = {'U',
                      'M',
                      'P',
                      '1',
                      static_cast<std::uint8_t>(length >> 24),
                      static_cast<std::uint8_t>(length >> 16),
                      static_cast<std::uint8_t>(length >> 8),
                      static_cast<std::uint8_t>(length)};
    output_offset_ = 0;
    return true;
}
bool ManagementEndpoint::dispatch() {
    using namespace wtp::json;
    auto root = parse(input_.view());
    if (!root || root->type() != '{')
        return false;
    const auto version = root->get("schema"), id = root->get("id"), op = root->get("operation");
    if (!version || version->type() != '"' || version->string() != schema || !id ||
        id->type() < '0' || id->type() > '9' || id->integer() <= 0 || !op || op->type() != '"')
        return false;
    const auto sequence = id->integer();
    const auto operation = op->string();
    if (operation == "ack") {
        if (!fields(*root, {"schema", "id", "operation", "session", "target"}) || !negotiated_ ||
            !pending_ || sequence != last_id_ || !binding(*root))
            return false;
        const auto covered = transaction_;
        // The ACK response is allocated before any deferred restart can run.
        if (!respond(200, {200, "{\"acknowledged\":true}", "application/json", {}}, false))
            return false;
        pending_ = false;
        finish_(covered, true);
        return true;
    }
    if (sequence <= last_id_ || pending_)
        return false;
    last_id_ = sequence;
    if (operation == "hello") {
        if (negotiated_ || !fields(*root, {"schema", "id", "operation"}))
            return false;
        negotiated_ = true;
        return respond(200,
                       {200,
                        "{\"schema\":\"usb-management-discovery/1\",\"product\":\"WsprryPico\","
                        "\"firmware\":" +
                            quote(firmware_) +
                            ",\"max_request_bytes\":32768,"
                            "\"max_response_bytes\":65536}",
                        "application/json",
                        {}},
                       false);
    }
    if (operation != "request" || !negotiated_ || !binding(*root) ||
        !fields(*root, {"schema", "id", "operation", "session", "target", "method", "path", "body",
                        "if_match"}))
        return false;
    for (const auto name : {"method", "path", "body", "if_match"})
        if (root->get(name)->type() != '"')
            return false;
    network::HttpRequest request;
    request.method = root->get("method")->string();
    request.path = root->get("path")->string();
    request.body = root->get("body")->string();
    request.headers["if-match"] = root->get("if_match")->string();
    if (request.path.size() > 128 || request.method.size() > 8 ||
        request.headers["if-match"].size() > 256)
        return false;
    // HTTP tasks use bit 63; USB owns bit 62 with a disjoint bounded generation.
    transaction_ = (1ULL << 62) | (generation_ << 31) | static_cast<unsigned>(sequence);
    pending_ = true;
    // Parsed input and its credential-bearing pages are released before the
    // application allocates its response. A request owns only one body copy.
    clear_input();
    auto response = handler_(request, transaction_);
    const auto status = response.status;
    return respond(status, std::move(response), true);
}
std::size_t ManagementEndpoint::receive(std::span<const std::uint8_t> bytes, std::uint64_t now_ms) {
    poll(now_ms);
    if (closed_ || !output_.empty())
        return 0;
    if (!bytes.empty() && !timing_) {
        started_ms_ = now_ms;
        timing_ = true;
    }
    std::size_t consumed = 0;
    while (consumed < bytes.size() && header_size_ < header_.size())
        header_[header_size_++] = bytes[consumed++];
    if (header_size_ != header_.size())
        return consumed;
    if (!expected_) {
        if (!std::equal(header_.begin(), header_.begin() + 4, "UMP1")) {
            disconnect();
            return consumed;
        }
        for (unsigned i = 4; i < 8; ++i)
            expected_ = (expected_ << 8) | header_[i];
        if (!expected_ || expected_ > maximum_request ||
            !wtp::memory_admitted(expected_, memory_reserve) || !input_.reserve(expected_)) {
            disconnect();
            return consumed;
        }
    }
    const auto count = std::min(expected_ - input_.size(), bytes.size() - consumed);
    input_.append(bytes.subspan(consumed, count));
    consumed += count;
    if (input_.size() == expected_) {
        if (!dispatch())
            disconnect();
        else
            clear_input();
    }
    return consumed;
}
std::span<const std::uint8_t> ManagementEndpoint::output() const {
    if (output_.empty())
        return {};
    if (output_offset_ < output_header_.size())
        return std::span(output_header_).subspan(output_offset_);
    return output_.at(output_offset_ - output_header_.size());
}
void ManagementEndpoint::consume_output(std::size_t bytes) {
    if (bytes > output().size()) {
        disconnect();
        return;
    }
    output_offset_ += bytes;
    if (!output_.empty() && output_offset_ == output_.size() + output_header_.size()) {
        output_ = {};
        output_offset_ = 0;
        if (!pending_)
            timing_ = false;
    }
}
} // namespace wsprrypico::usb
