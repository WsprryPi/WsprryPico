// Project-owned instrumentation of the pinned newlib entry points. No allocator
// implementation is copied or replaced. The SDK's outer panic policy is intact.
#include "runtime/pico/heap_metrics.h"

#include "pico/mutex.h"
#include "pico/time.h"

#include <errno.h>
#include <malloc.h>
#include <reent.h>

auto_init_recursive_mutex(heap_mutex);
static wsprry_heap_metrics metrics;
static uint32_t depth;

extern void* __real__malloc_r(struct _reent*, size_t);
extern void* __real__calloc_r(struct _reent*, size_t, size_t);
extern void* __real__realloc_r(struct _reent*, void*, size_t);
extern void __real__free_r(struct _reent*, void*);
extern struct mallinfo __real_mallinfo(void);

static uint32_t maximum(uint32_t a, uint32_t b) {
    return a > b ? a : b;
}
static uint32_t bounded(uint64_t value) {
    return value > UINT32_MAX ? UINT32_MAX : (uint32_t)value;
}
static void sample(void) {
    const uint64_t start = time_us_64();
    const struct mallinfo heap = __real_mallinfo();
    const uint32_t cost = bounded(time_us_64() - start);
    metrics.live_bytes = (uint32_t)heap.uordblks;
    metrics.peak_bytes = maximum(metrics.peak_bytes, metrics.live_bytes);
    metrics.max_sample_us = maximum(metrics.max_sample_us, cost);
    metrics.sample_time_us += cost;
}
static uint64_t enter(size_t requested) {
    recursive_mutex_enter_blocking(&heap_mutex);
    ++depth;
    ++metrics.entries;
    metrics.max_depth = maximum(metrics.max_depth, depth);
    metrics.largest_request_bytes = maximum(metrics.largest_request_bytes, bounded(requested));
    return time_us_64();
}
static void leave(uint64_t start, bool failed, size_t successful_bytes) {
    metrics.largest_successful_request_bytes =
        maximum(metrics.largest_successful_request_bytes, bounded(successful_bytes));
    sample();
    if (failed)
        ++metrics.failures;
    metrics.max_entry_us = maximum(metrics.max_entry_us, bounded(time_us_64() - start));
    --depth;
    recursive_mutex_exit(&heap_mutex);
}
void* __wrap__malloc_r(struct _reent* context, size_t size) {
    const uint64_t start = enter(size);
    void* result = __real__malloc_r(context, size);
    leave(start, !result && size != 0, result ? size : 0);
    return result;
}
void* __wrap__calloc_r(struct _reent* context, size_t count, size_t size) {
    const bool overflow = size && count > SIZE_MAX / size;
    const uint64_t start = enter(overflow ? SIZE_MAX : count * size);
    void* result = NULL;
    if (overflow)
        context->_errno = ENOMEM;
    else
        result = __real__calloc_r(context, count, size);
    leave(start, !result && (overflow || (count && size)), result ? count * size : 0);
    return result;
}
void* __wrap__realloc_r(struct _reent* context, void* pointer, size_t size) {
    const uint64_t start = enter(size);
    void* result = __real__realloc_r(context, pointer, size);
    leave(start, !result && size != 0, result ? size : 0);
    return result;
}
void __wrap__free_r(struct _reent* context, void* pointer) {
    const uint64_t start = enter(0);
    __real__free_r(context, pointer);
    leave(start, false, 0);
}
struct mallinfo __wrap_mallinfo(void) {
    recursive_mutex_enter_blocking(&heap_mutex);
    const struct mallinfo result = __real_mallinfo();
    recursive_mutex_exit(&heap_mutex);
    return result;
}
wsprry_heap_metrics wsprry_heap_snapshot(void) {
    recursive_mutex_enter_blocking(&heap_mutex);
    sample();
    const wsprry_heap_metrics result = metrics;
    recursive_mutex_exit(&heap_mutex);
    return result;
}
void* wsprry_heap_try_calloc(size_t count, size_t size) {
    return _calloc_r(_REENT, count, size);
}
bool wsprry_heap_probe(size_t bytes) {
    void* pointer = _malloc_r(_REENT, bytes);
    if (!pointer)
        return false;
    _free_r(_REENT, pointer);
    return true;
}
