#include "network/control.hpp"
#include "runtime/json.hpp"

#include <cassert>
#include <limits>
using namespace wsprrypico;
namespace {
std::string text(const execution::ResponseSource& source, std::size_t chunk) {
    std::string result;
    while (result.size() < source.size()) {
        const auto part = source.at(result.size());
        assert(!part.empty() && part.size() <= execution::ResponseSource::window_bytes);
        assert(source.at(result.size()).data() == part.data());
        const auto n = std::min(chunk, part.size());
        result.append(reinterpret_cast<const char*>(part.data()), n);
    }
    return result;
}
void incomplete_output() {
    struct TruncatedSource final : execution::ResponseSource {
        std::size_t size() const override {
            return 2048;
        }
        std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
            if (offset >= 1024)
                return 0;
            const auto count = std::min<std::size_t>(out.size(), 1024 - offset);
            std::fill_n(out.begin(), count, 'x');
            return count;
        }
    };
    network::HttpResponse response{200, {}, "application/json", {}};
    response.generated_body = execution::make_response_source<TruncatedSource>();
    assert(response.body_text().empty()); // No partial logical document escapes.
    assert(response.wire().empty());      // No header + truncated body masquerades as complete.
}
void escaping() {
    const std::string input = std::string("\"\\\n\r\t\0", 6) + "\xc3\xa9" + std::string(2050, 'x');
    auto source = execution::make_response_source<execution::TextResponseSource>(input);
    auto escaped = execution::make_response_source<execution::EscapedResponseSource>(std::move(source));
    assert(escaped && escaped->valid());
    const auto quoted = execution::json::quote(input);
    assert(text(*escaped, 1) == quoted.substr(1, quoted.size() - 2));
}
std::size_t fault_at = 0, fault_calls = 0, fault_live = 0;
void* fault_allocate(std::size_t bytes) {
    if (++fault_calls == fault_at)
        return nullptr;
    auto* memory = std::malloc(bytes);
    if (memory)
        ++fault_live;
    return memory;
}
void fault_free(void* memory) {
    if (memory) {
        assert(fault_live);
        --fault_live;
    }
    std::free(memory);
}
void allocation_failure() {
    const auto allocator = execution::allocate_input;
    const auto deallocator = execution::deallocate_input;
    execution::allocate_input = fault_allocate;
    execution::deallocate_input = fault_free;
    const auto make_reply = [] {
        auto body = execution::make_response_source<execution::TextResponseSource>("\"saved\":true");
        network::HttpResponse reply{200, {}, "application/json", {}};
        if (body)
            reply.generated_body = execution::make_response_source<execution::JoinedResponseSource>(
                "{", std::move(body), "}", true);
        if (reply.generated_body)
            reply = network::control_response(std::move(reply));
        return reply;
    };
    fault_at = 0;
    fault_calls = 0;
    std::size_t allocations = 0;
    {
        auto reply = make_reply();
        assert(reply.generated_body);
        allocations = fault_calls;
        fault_at = allocations + 1;
        const auto expected = "{\"contract\":\"Wsprry-Control/1\", \"saved\":true}";
        assert(text(*reply.generated_body, 1) == expected);
        assert(text(*reply.generated_body, 17) == expected);
        assert(fault_calls == allocations);
    }
    assert(fault_live == 0);
    for (fault_at = 1; fault_at <= allocations; ++fault_at) {
        fault_calls = 0;
        assert(!make_reply().generated_body);
        assert(fault_live == 0);
    }
    execution::allocate_input = allocator;
    execution::deallocate_input = deallocator;
}

} // namespace
int main() {
    incomplete_output();
    escaping();
    allocation_failure();
}
