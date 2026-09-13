#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint64_t entries;
    uint64_t failures;
    uint64_t sample_time_us;
    uint32_t live_bytes;
    uint32_t peak_bytes;
    uint32_t largest_request_bytes;
    uint32_t largest_successful_request_bytes;
    uint32_t max_sample_us;
    uint32_t max_entry_us;
    uint32_t max_depth;
} wsprry_heap_metrics;

wsprry_heap_metrics wsprry_heap_snapshot(void);
// Panic-only snapshot of this core's last completed allocation attempt. No allocation,
// lock or free-list walk; the SDK calls its panic after its wrapper returns.
// Output 0 is the requested byte count, output 1 tags NULL versus non-NULL.
void wsprry_heap_panic_attempt(uint32_t record[2]);
// Nullable newlib allocation, serialized with every instrumented allocator
// entry. Only callers which already handle NULL may use this bypass of the
// SDK's panic-on-null wrapper. Free through the ordinary allocator.
void* wsprry_heap_try_calloc(size_t count, size_t size);
// One allocation/free, never a retained block. Caller must establish idle
// authority and enforce the requested byte limit before entering.
bool wsprry_heap_probe(size_t bytes);
#ifdef __cplusplus
}
#endif
