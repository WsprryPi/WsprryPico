#include "network/http.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <source_location>

// C++ allocation ledger for bounded HTTP response lifetime regression.
// It measures reclamation independently of string size/capacity observations.
namespace ledger {
struct alignas(std::max_align_t) Header {
    void* base;
    std::size_t bytes;
    std::uint64_t magic;
};
constexpr std::uint64_t magic = 0x706831346c696665ULL;
std::size_t bytes = 0, blocks = 0;
void require(bool condition, std::source_location location = std::source_location::current()) {
    if (!condition) {
        std::fprintf(stderr, "require failed at %s:%u %s live=%zu blocks=%zu\n",
                     location.file_name(), location.line(), location.function_name(), bytes,
                     blocks);
        std::abort();
    }
}
void* allocate(std::size_t count, std::size_t alignment) {
    alignment = alignment < alignof(Header) ? alignof(Header) : alignment;
    require(alignment && !(alignment & (alignment - 1)));
    if (count > SIZE_MAX - sizeof(Header) - alignment)
        throw std::bad_alloc();
    auto* base = std::malloc(count + sizeof(Header) + alignment);
    if (!base)
        throw std::bad_alloc();
    auto address = (reinterpret_cast<std::uintptr_t>(base) + sizeof(Header) + alignment - 1) &
                   ~(alignment - 1);
    auto* header = reinterpret_cast<Header*>(address) - 1;
    *header = {base, count, magic};
    bytes += count;
    ++blocks;
    return reinterpret_cast<void*>(address);
}
void release(void* pointer) noexcept {
    if (!pointer)
        return;
    auto* header = static_cast<Header*>(pointer) - 1;
    require(header->magic == magic && blocks && bytes >= header->bytes);
    bytes -= header->bytes;
    --blocks;
    header->magic = 0;
    std::free(header->base);
}
} // namespace ledger
void* operator new(std::size_t n) {
    return ledger::allocate(n, alignof(std::max_align_t));
}
void* operator new[](std::size_t n) {
    return ::operator new(n);
}
void* operator new(std::size_t n, std::align_val_t a) {
    return ledger::allocate(n, static_cast<std::size_t>(a));
}
void* operator new[](std::size_t n, std::align_val_t a) {
    return ::operator new(n, a);
}
void operator delete(void* p) noexcept {
    ledger::release(p);
}
void operator delete[](void* p) noexcept {
    ledger::release(p);
}
void operator delete(void* p, std::size_t) noexcept {
    ledger::release(p);
}
void operator delete[](void* p, std::size_t) noexcept {
    ledger::release(p);
}
void operator delete(void* p, std::align_val_t) noexcept {
    ledger::release(p);
}
void operator delete[](void* p, std::align_val_t) noexcept {
    ledger::release(p);
}
void operator delete(void* p, std::size_t, std::align_val_t) noexcept {
    ledger::release(p);
}
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept {
    ledger::release(p);
}

using wsprrypico::network::HttpResponse;
namespace {
constexpr std::array<std::size_t, 5> sizes{0, 15, 16, 1301, 2758};
constexpr std::string_view static_page = "static browser asset";

void check_bytes(const HttpResponse& response, std::size_t count, bool is_static) {
    std::size_t offset = 0;
    while (offset < count) {
        const auto bytes = response.body_at(offset);
        ledger::require(!bytes.empty());
        const auto available = std::min(bytes.size(), count - offset);
        for (std::size_t i = 0; i < available; ++i)
            ledger::require(bytes[i] ==
                            static_cast<std::uint8_t>(is_static ? static_page[offset + i] : 'x'));
        offset += available;
    }
}

void response_reclamation() {
    const auto before_bytes = ledger::bytes;
    const auto before_blocks = ledger::blocks;
    unsigned cases = 0;
    {
        std::array<HttpResponse, 2> slots;
        const auto baseline_bytes = ledger::bytes;
        const auto baseline_blocks = ledger::blocks;
        // Completed responses, cancelled partial responses, then acknowledged
        // keep-alive responses all use the production reset primitive.
        for (unsigned boundary = 0; boundary < 3; ++boundary) {
            for (const auto size : sizes) {
                for (auto& response : slots) {
                    response.body.assign(size, 'x');
                    response.static_body = size == 0 ? static_page : std::string_view{};
                    response.keep_alive = boundary == 2;
                    response.status = 202;
                    response.location = "/next";
                    response.content_security_policy = "default-src 'none'";
                    const auto count = response.body_size();
                    ledger::require(count == (size == 0 ? static_page.size() : size));
                    check_bytes(response, boundary == 1 ? count / 2 : count, size == 0);
                    // Reading a partial body must not release or change unsent bytes.
                    check_bytes(response, count, size == 0);
                    ledger::require(response.status == 202 && response.location == "/next");
                    response.reset();
                    ledger::require(response.body.empty() && response.body_size() == 0);
                    ledger::require(response.status == 200 && response.type == "application/json");
                    ledger::require(!response.keep_alive && response.static_body.empty() &&
                                    response.static_parts.empty() && response.location.empty() &&
                                    response.content_security_policy.empty());
                    ledger::require(ledger::bytes == baseline_bytes &&
                                    ledger::blocks == baseline_blocks);
                    ++cases;
                }
            }
        }
    }
    ledger::require(cases == 30 && ledger::bytes == before_bytes &&
                    ledger::blocks == before_blocks);
    std::printf(
        "HTTP response reclamation passed: %u cases, both slots, full destruction baseline\n",
        cases);
}
} // namespace

int main() {
    response_reclamation();
}
