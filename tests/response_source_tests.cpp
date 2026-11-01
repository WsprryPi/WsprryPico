#include "network/control.hpp"
#include "wtp/codec.hpp"

#include <cassert>
#include <limits>
using namespace wsprrypico;
namespace {
std::string text(const wtp::ResponseSource& source, std::size_t chunk) {
    std::string result;
    while (result.size() < source.size()) {
        const auto part = source.at(result.size());
        assert(!part.empty() && part.size() <= wtp::ResponseSource::window_bytes);
        assert(source.at(result.size()).data() == part.data());
        const auto n = std::min(chunk, part.size());
        result.append(reinterpret_cast<const char*>(part.data()), n);
    }
    return result;
}
void load_equivalence() {
    for (const std::size_t count : {0, 1, 16, 32, 33, 162, 256, 512}) {
        wtp::Request request;
        request.operation = "LOAD";
        request.request_id = std::string(32, 'a');
        wtp::Response response;
        response.ok = true;
        response.job_id = std::string(32, 'b');
        std::vector<wtp::FrequencyAdjustment> values;
        for (std::size_t i = 0; i < count; ++i)
            values.push_back({i, std::numeric_limits<std::uint64_t>::max() - i, i});
        response.adjustments = std::move(values);
        auto expected = wtp::encode_load_response_buffer(request, response, true);
        network::HttpResponse original{200, {}, "application/json", {}, std::move(expected)};
        auto adapted = network::control_response(std::move(original));
        const auto expected_text = adapted.body_text();
        auto selected =
            network::control_response(network::browser_load_response(request, response));
        assert(selected.status == 200 && selected.body_text() == expected_text);
        assert(bool(selected.generated_body) == (count > 32));
        for (const auto chunk : {1, 17, 1024}) {
            network::HttpResponse streamed{200, {}, "application/json", {}};
            auto producer = response;
            streamed.generated_body = wtp::load_response_source(request, producer);
            producer.adjustments.clear();
            producer.job_id = "changed after capture";
            assert(streamed.generated_body && streamed.generated_body->json_document());
            streamed = network::control_response(std::move(streamed));
            assert(streamed.generated_body);
            assert(text(*streamed.generated_body, chunk) == expected_text);
            // Counting/escaping can replay the same immutable document after a
            // complete transfer, independently of live producer lifetimes.
            auto escaped = wtp::make_response_source<wtp::EscapedResponseSource>(
                std::move(streamed.generated_body));
            assert(escaped && escaped->valid());
            const auto wire = text(*escaped, chunk);
            assert(wire.size() == escaped->size());
            const auto quoted = wtp::json::quote(expected_text);
            assert(wire == quoted.substr(1, quoted.size() - 2));
        }
    }
}
void incomplete_output() {
    struct TruncatedSource final : wtp::ResponseSource {
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
    response.generated_body = wtp::make_response_source<TruncatedSource>();
    assert(response.body_text().empty()); // No partial logical document escapes.
    assert(response.wire().empty());      // No header + truncated body masquerades as complete.
}
void escaping() {
    const std::string input = std::string("\"\\\n\r\t\0", 6) + "\xc3\xa9" + std::string(2050, 'x');
    auto source = wtp::make_response_source<wtp::TextResponseSource>(input);
    auto escaped = wtp::make_response_source<wtp::EscapedResponseSource>(std::move(source));
    assert(escaped && escaped->valid());
    const auto quoted = wtp::json::quote(input);
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
    const auto allocator = wtp::allocate_input;
    const auto deallocator = wtp::deallocate_input;
    wtp::Request request;
    request.operation = "LOAD";
    wtp::Response response;
    response.ok = true;
    wtp::allocate_input = fault_allocate;
    wtp::deallocate_input = fault_free;
    // Each nullable object/window allocation, including nested contract
    // adapters, must fail before publication and reclaim preceding nodes.
    for (fault_at = 1; fault_at <= 6; ++fault_at) {
        fault_calls = 0;
        {
            network::HttpResponse reply{200, {}, "application/json", {}};
            reply.generated_body = wtp::load_response_source(request, response);
            if (reply.generated_body)
                reply = network::control_response(std::move(reply));
            assert(!reply.generated_body);
        }
        assert(fault_live == 0);
    }
    fault_at = 0;
    fault_calls = 0;
    {
        network::HttpResponse reply{200, {}, "application/json", {}};
        reply.generated_body = wtp::load_response_source(request, response);
        reply = network::control_response(std::move(reply));
        assert(reply.generated_body);
        const auto calls = fault_calls;
        fault_at = calls + 1;
        assert(!text(*reply.generated_body, 1).empty());
        assert(fault_calls == calls);
    }
    assert(fault_live == 0);
    wtp::allocate_input = allocator;
    wtp::deallocate_input = deallocator;
}

} // namespace
int main() {
    load_equivalence();
    incomplete_output();
    escaping();
    allocation_failure();
}
