#pragma once
#include "network/http.hpp"
#include "network/control_contract.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

namespace wsprrypico::network {
// Owned plaintext created by the control adapter is wiped on normal return
// and exception unwinding. Borrowed transport pages retain their own wipers.
class ControlStringWiper {
  public:
    explicit ControlStringWiper(std::string& value) : value_(value) {}
    ~ControlStringWiper() {
        volatile char* bytes = value_.data();
        for (std::size_t at = 0; at < value_.size(); ++at) bytes[at] = 0;
    }
    ControlStringWiper(const ControlStringWiper&) = delete;
    ControlStringWiper& operator=(const ControlStringWiper&) = delete;
  private:
    std::string& value_;
};
// Validate the outer contract once, then pass the closed domain payload to its
// existing authoritative validator. No field other than contract is removed.
inline std::size_t control_workspace_bytes(wtp::InputView bytes) {
    const auto whitespace = [](char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; };
    std::size_t first = 0, last = bytes.size();
    while (first < last && whitespace(bytes[first])) ++first;
    while (last > first && whitespace(bytes[last - 1])) --last;
    return (last - first) * 2 + 16384;
}
inline std::optional<std::string> control_payload(wtp::InputView bytes) {
    if (bytes.size() > max_http_body || !wtp::memory_admitted(control_workspace_bytes(bytes))) return {};
    const auto root = wtp::json::parse(bytes);
    if (!root || root->type() != '{') return {};
    const auto contract = root->get("contract");
    if (!contract || contract->type() != '"' || contract->string() != control_contract) return {};
    std::string raw(root->raw);
    ControlStringWiper wipe(raw);
    const auto position = contract->raw.offset() - root->raw.offset();
    std::size_t start = 1;
    unsigned depth = 1;
    bool quoted = false, escaped = false;
    for (std::size_t at = 1; at < raw.size(); ++at) {
        const auto c = raw[at];
        if (quoted) {
            if (escaped) escaped = false;
            else if (c == '\\') escaped = true;
            else if (c == '"') quoted = false;
            continue;
        }
        if (c == '"') { quoted = true; continue; }
        if (c == '{' || c == '[') ++depth;
        if (c == '}' || c == ']') --depth;
        if ((c == ',' && depth == 1) || depth == 0) {
            if (position >= start && position < at) {
                const auto original_size = raw.size();
                if (c == ',') raw.erase(start, at - start + 1);
                else if (start > 1) raw.erase(start - 1, at - start + 1);
                else raw.erase(start, at - start);
                // erase can leave a duplicate plaintext tail beyond size.
                const auto payload_size = raw.size();
                raw.resize(original_size, '\0');
                raw.resize(payload_size);
                return std::optional<std::string>(std::move(raw));
            }
            start = at + 1;
        }
    }
    return {};
}
inline HttpResponse control_response(HttpResponse response) {
    constexpr std::string_view member = "\"contract\":\"Wsprry-Control/1\",";
    if (!response.buffered_body.empty()) {
        const auto size = response.buffered_body.size();
        if (response.buffered_body.view()[0] != '{' ||
            !response.buffered_body.reserve(size + member.size()) )
            return http_error(503, "resource_exhausted");
        // Reserve and prepend preserve paged output instead of flattening it.
        response.buffered_body.mutable_at(0)[0] = ' ';
        const std::string prefix = "{" + std::string(member);
        if (!response.buffered_body.reserve(size + prefix.size()) ||
            !response.buffered_body.prepend(std::span(reinterpret_cast<const std::uint8_t*>(prefix.data()), prefix.size())))
            return http_error(503, "resource_exhausted");
    } else if (!response.body.empty() && response.body.front() == '{') {
        response.body.insert(1, member);
    }
    return response;
}
} // namespace wsprrypico::network
