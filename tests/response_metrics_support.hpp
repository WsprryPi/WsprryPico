#pragma once
#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>
namespace probe {
struct alignas(std::max_align_t) Header {
    std::size_t size;
    bool charged;
};
bool tracking = false;
std::size_t live = 0, peak = 0, largest = 0, calls = 0;
long long max_step_ns = 0;
std::chrono::steady_clock::time_point started;
void* alloc(std::size_t n) {
    auto* h = static_cast<Header*>(std::malloc(sizeof(Header) + (n ? n : 1)));
    if (!h)
        return nullptr;
    *h = {n, tracking};
    if (tracking) {
        live += n;
        peak = std::max(peak, live);
        largest = std::max(largest, n);
        ++calls;
    }
    return h + 1;
}
void release(void* p) {
    if (!p)
        return;
    auto* h = static_cast<Header*>(p) - 1;
    if (h->charged)
        live -= h->size;
    std::free(h);
}
void start() {
    if (live)
        std::abort();
    peak = largest = calls = 0;
    max_step_ns = 0;
    started = std::chrono::steady_clock::now();
    tracking = true;
}
void step(std::chrono::steady_clock::time_point before) {
    max_step_ns = std::max(
        max_step_ns, static_cast<long long>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                                std::chrono::steady_clock::now() - before)
                                                .count()));
}
void report(const char* label, std::size_t bytes) {
    tracking = false;
    const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::steady_clock::now() - started)
                        .count();
    std::printf(
        "%s bytes=%zu live=%zu peak=%zu largest=%zu calls=%zu elapsed_ns=%lld max_step_ns=%lld\n",
        label, bytes, live, peak, largest, calls, static_cast<long long>(ns), max_step_ns);
}
} // namespace probe
void* operator new(std::size_t n) {
    if (auto* p = probe::alloc(n))
        return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept {
    probe::release(p);
}
void operator delete(void* p, std::size_t) noexcept {
    probe::release(p);
}
