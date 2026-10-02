#include "runtime/pool_metrics.hpp"

#include <cassert>
int main() {
    wsprrypico::runtime::PoolMetrics<2> pool;
    int a, b, foreign;
    assert(pool.allocated(&a));
    assert(pool.allocated(&b));
    assert(pool.allocated(nullptr));
    assert(!pool.allocated(&a));
    assert(!pool.allocated(&foreign));
    assert(!pool.released(&foreign));
    assert(pool.released(&a));
    assert(!pool.released(&a));
    assert(pool.released(&b));
    auto empty = pool.snapshot();
    assert(empty.used == 0 && empty.peak == 2 && empty.failures == 1 && empty.faults == 4);
    assert(empty.capacity == 2);
    assert(pool.allocated(&a));
    assert(pool.released(&a));
    assert(pool.snapshot().used == 0 && pool.snapshot().peak == 2);
}
