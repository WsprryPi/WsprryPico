#include "malloc.h"
#include "reent.h"
#include "runtime/allocation_fault.h"
#include "runtime/pico/heap_metrics.h"

#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

struct _reent test_reent;
_Thread_local unsigned test_core_num;
static unsigned char blocks[16][4096];
static size_t lengths[16];
static atomic_uint_fast64_t ticks;
static atomic_uint mallinfo_calls;
uint64_t time_us_64(void) {
    return atomic_fetch_add(&ticks, 1);
}
void* __real__malloc_r(struct _reent* c, size_t size) {
    if (size <= 4096)
        for (unsigned i = 0; i < 16; ++i)
            if (!lengths[i]) {
                lengths[i] = size ? size : 1;
                return blocks[i];
            }
    c->_errno = ENOMEM;
    return NULL;
}
void __real__free_r(struct _reent* c, void* pointer) {
    (void)c;
    if (!pointer)
        return;
    for (unsigned i = 0; i < 16; ++i)
        if (pointer == blocks[i]) {
            assert(lengths[i]);
            lengths[i] = 0;
            return;
        }
    assert(!"foreign free");
}
void* __real__calloc_r(struct _reent* c, size_t count, size_t size) {
    void* p = __wrap__malloc_r(c, count * size);
    if (p)
        memset(p, 0, count * size);
    return p;
}
void* __real__realloc_r(struct _reent* c, void* p, size_t size) {
    if (!size) {
        __wrap__free_r(c, p);
        return NULL;
    }
    void* next = __wrap__malloc_r(c, size);
    if (!next)
        return NULL;
    for (unsigned i = 0; i < 16; ++i)
        if (p == blocks[i])
            memcpy(next, p, size < lengths[i] ? size : lengths[i]);
    __wrap__free_r(c, p);
    return next;
}
struct mallinfo __real_mallinfo(void) {
    atomic_fetch_add(&mallinfo_calls, 1);
    int total = 0;
    for (unsigned i = 0; i < 16; ++i)
        if (lengths[i])
            total += (int)lengths[i] + 16;
    return (struct mallinfo){total};
}
static void* concurrent(void* unused) {
    (void)unused;
    for (unsigned i = 0; i < 1000; ++i) {
        void* p = wsprry_heap_try_calloc(1, 64);
        assert(p);
        assert(wsprry_heap_snapshot().live_bytes >= 80);
        __wrap__free_r(_REENT, p);
    }
    return NULL;
}
int main(void) {
    uint32_t attempt[2];
    wsprry_heap_panic_attempt(attempt);
    assert(!wsprry_allocation_fault_valid(true, WSPRRY_ALLOCATION_FAULT_HASH, attempt[1]));
    for (uint32_t tag = WSPRRY_ALLOCATION_FAULT_TAG; tag <= WSPRRY_ALLOCATION_FAULT_TAG + 1;
         ++tag) {
        assert(wsprry_allocation_fault_valid(true, WSPRRY_ALLOCATION_FAULT_HASH, tag));
        assert(!wsprry_allocation_fault_valid(false, WSPRRY_ALLOCATION_FAULT_HASH, tag));
        assert(!wsprry_allocation_fault_valid(true, 0, tag));
    }
    assert(!wsprry_allocation_fault_valid(true, WSPRRY_ALLOCATION_FAULT_HASH,
                                          WSPRRY_ALLOCATION_FAULT_TAG + 2));
    assert(wsprry_heap_snapshot().live_bytes == 0);
    void* transient = __wrap__malloc_r(_REENT, 64);
    assert(transient);
    const unsigned walks = atomic_load(&mallinfo_calls);
    __wrap__free_r(_REENT, transient);
    __wrap__free_r(_REENT, NULL);
    assert(atomic_load(&mallinfo_calls) == walks);
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == 64 && attempt[1] == WSPRRY_ALLOCATION_FAULT_TAG);
    assert(atomic_load(&mallinfo_calls) == walks); // Panic capture does not walk the heap.
    test_core_num = 1;
    void* other_core = __wrap__malloc_r(_REENT, 33);
    assert(other_core);
    __wrap__free_r(_REENT, other_core);
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == 33 && attempt[1] == WSPRRY_ALLOCATION_FAULT_TAG);
    test_core_num = 0;
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == 64 && attempt[1] == WSPRRY_ALLOCATION_FAULT_TAG);
    wsprry_heap_metrics fresh = wsprry_heap_snapshot();
    assert(fresh.live_bytes == 0 && fresh.peak_bytes == 80);
    assert(atomic_load(&mallinfo_calls) == walks + 2);
    unsigned char* p = wsprry_heap_try_calloc(1, 100);
    assert(p);
    assert(p[0] == 0 && p[99] == 0);
    p[0] = 42;
    p = __wrap__realloc_r(_REENT, p, 300);
    assert(p && p[0] == 42);
    wsprry_heap_metrics m = wsprry_heap_snapshot();
    assert(m.live_bytes == 316 && m.peak_bytes == 432 && m.max_depth >= 2);
    assert(!__wrap__realloc_r(_REENT, p, 4097) && p[0] == 42);
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == 4097 && attempt[1] == (WSPRRY_ALLOCATION_FAULT_TAG | 1U));
    assert(wsprry_heap_snapshot().live_bytes == 316);
    assert(!wsprry_heap_try_calloc(SIZE_MAX, 2) && test_reent._errno == ENOMEM);
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == UINT32_MAX && attempt[1] == (WSPRRY_ALLOCATION_FAULT_TAG | 1U));
    assert(!wsprry_heap_probe(4097));
    assert(wsprry_heap_snapshot().largest_successful_request_bytes == 300);
    assert(wsprry_heap_probe(4000));
    assert(wsprry_heap_snapshot().largest_successful_request_bytes == 4000);
    assert(wsprry_heap_snapshot().live_bytes == 316);
    assert(!__wrap__realloc_r(_REENT, p, 0));
    wsprry_heap_panic_attempt(attempt);
    assert(attempt[0] == 0 && attempt[1] == (WSPRRY_ALLOCATION_FAULT_TAG | 1U));
    const uint64_t failures = wsprry_heap_snapshot().failures;
    assert(failures >= 3 && wsprry_heap_snapshot().live_bytes == 0);
    pthread_t a, b;
    assert(!pthread_create(&a, NULL, concurrent, NULL));
    assert(!pthread_create(&b, NULL, concurrent, NULL));
    pthread_join(a, NULL);
    pthread_join(b, NULL);
    m = wsprry_heap_snapshot();
    assert(m.live_bytes == 0 && m.failures == failures && m.entries >= 6000);
    assert(m.max_sample_us && m.sample_time_us && m.max_entry_us);
    puts("Heap hooks: transient realloc peak, failed realloc retention, overflow, nullable "
         "recovery, probe release and concurrent recursion passed");
}
