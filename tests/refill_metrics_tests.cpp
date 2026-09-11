#include "rf/refill_metrics.hpp"

#include <cstdlib>

using wsprrypico::rf::RefillMetrics;
void check(bool condition) {
    if (!condition)
        std::abort();
}
int main() {
    RefillMetrics metrics;
    metrics.ready(1, 0, 1000, false, false, 0); // Prefill is not a measured refill.
    check(metrics.snapshot().running_links == 0);
    metrics.completed(1, 0, 2000);
    metrics.completed(1, 1, 3000);
    metrics.ready(1, 2, 4000, true, false, 8192);
    metrics.ready(1, 3, 6000, true, true, 12); // Short predecessor needs its own reserve.
    auto result = metrics.snapshot();
    check(result.pairs == 2 && result.unpaired == 0 && result.running_links == 2);
    check(result.max_irq_to_ready_ns == 3000 && result.min_remaining_words == 12);
    check(result.tail_links == 1 && result.exhausted_links == 0);
    check(result.min_data_remaining_words == 8192 && result.min_tail_remaining_words == 12);
    metrics.ready(1, 3, 7000, true, true, 0); // A reused completion cannot certify a pair.
    check(metrics.snapshot().unpaired == 1 && metrics.snapshot().exhausted_links == 1);
    metrics.completed(1, 2, 8000);
    metrics.ready(2, 4, 9000, true, false, 4096); // Prior epoch.
    metrics.completed(2, 4, 10000);
    metrics.ready(2, 6, 9999, true, false, 4096); // Time reversal.
    metrics.completed(2, 6, 11000);
    metrics.ready(2, 10, 12000, true, false, 4096); // Missing intermediate descriptor.
    result = metrics.snapshot();
    check(result.unpaired == 4 && result.pairs == 2);
    check(result.min_remaining_words == 0 && result.max_irq_to_ready_ns == 3000);
    metrics.completed(3, 0, 0); // A zero timer origin is valid, not a sentinel.
    metrics.ready(3, 2, 0, true, false, 100);
    check(metrics.snapshot().pairs == 3);
}
