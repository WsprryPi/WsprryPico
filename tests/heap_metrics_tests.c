#include "malloc.h"
#include "reent.h"
#include "runtime/pico/heap_metrics.h"

#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

struct _reent test_reent;
static unsigned char blocks[16][4096];
static size_t lengths[16];
static atomic_uint_fast64_t ticks;
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
    assert(wsprry_heap_snapshot().live_bytes == 0);
    unsigned char* p = wsprry_heap_try_calloc(1, 100);
    assert(p);
    assert(p[0] == 0 && p[99] == 0);
    p[0] = 42;
    p = __wrap__realloc_r(_REENT, p, 300);
    assert(p && p[0] == 42);
    wsprry_heap_metrics m = wsprry_heap_snapshot();
    assert(m.live_bytes == 316 && m.peak_bytes == 432 && m.max_depth >= 2);
    assert(!__wrap__realloc_r(_REENT, p, 4097) && p[0] == 42);
    assert(wsprry_heap_snapshot().live_bytes == 316);
    assert(!wsprry_heap_try_calloc(SIZE_MAX, 2) && test_reent._errno == ENOMEM);
    assert(!wsprry_heap_probe(4097));
    assert(wsprry_heap_snapshot().largest_successful_request_bytes == 300);
    assert(wsprry_heap_probe(4000));
    assert(wsprry_heap_snapshot().largest_successful_request_bytes == 4000);
    assert(wsprry_heap_snapshot().live_bytes == 316);
    assert(!__wrap__realloc_r(_REENT, p, 0));
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
