#include "rf/refill_metrics.hpp"

#include <cstdlib>

using wsprrypico::rf::RefillMetrics;
void check(bool condition) {
    if (!condition)
        std::abort();
}
int main() {
    RefillMetrics metrics;
    metrics.ready(1, 0, 1000, false, false, 0, 16384); // Prefill is not a measured refill.
    check(metrics.snapshot().running_links == 0);
    metrics.completed(1, 0, 2000);
    metrics.completed(1, 1, 3000);
    metrics.ready(1, 2, 4000, true, false, 8192, 16384);
    metrics.ready(1, 3, 6000, true, true, 12, 100); // Short predecessor needs its own reserve.
    auto result = metrics.snapshot();
    check(result.pairs == 2 && result.unpaired == 0 && result.running_links == 2);
    check(result.max_irq_to_ready_ns == 3000 && result.min_remaining_words == 12);
    check(result.tail_links == 1 && result.exhausted_links == 0);
    check(result.min_data_remaining_words == 8192 && result.min_tail_remaining_words == 12);
    metrics.ready(1, 3, 7000, true, true, 0, 100); // A reused completion cannot certify a pair.
    check(metrics.snapshot().unpaired == 1 && metrics.snapshot().exhausted_links == 1);
    metrics.completed(1, 2, 8000);
    metrics.ready(2, 4, 9000, true, false, 4096, 16384); // Prior epoch.
    metrics.completed(2, 4, 10000);
    metrics.ready(2, 6, 9999, true, false, 4096, 16384); // Time reversal.
    metrics.completed(2, 6, 11000);
    metrics.ready(2, 10, 12000, true, false, 4096, 16384); // Missing intermediate descriptor.
    result = metrics.snapshot();
    check(result.unpaired == 4 && result.pairs == 2);
    check(result.min_remaining_words == 0 && result.max_irq_to_ready_ns == 3000);
    check(result.full.observations == 4 && result.full.remaining_words == 4096);
    check(result.short_block.observations == 2 && result.short_block.remaining_words == 0);
    check(result.short_block.total_words == 100 && result.short_block.sequence == 3);
    check(result.short_block.epoch == 1 && result.short_block.observed_ns == 7000);
    metrics.ready(2, 12, 13000, true, false, 101, 100);
    metrics.ready(2, 14, 14000, true, false, 0, 0);
    metrics.ready(2, 16, 15000, true, false, 1, 16385);
    check(metrics.snapshot().invalid_reserves == 3);
    check(metrics.snapshot().short_block.observations == 2);
    metrics.completed(3, 0, 0); // A zero timer origin is valid, not a sentinel.
    metrics.ready(3, 2, 0, true, false, 100, 16384);
    check(metrics.snapshot().pairs == 3);
    RefillMetrics fractions;
    fractions.ready(7, 2, 1000, true, true, 10, 20);  // 50%.
    fractions.ready(7, 4, 2000, true, true, 20, 100); // 20%, despite more words.
    fractions.ready(7, 6, 3000, true, true, 5, 10);   // 50%, despite fewer words.
    const auto worst = fractions.snapshot().short_block;
    check(worst.observations == 3 && worst.remaining_words == 20 && worst.total_words == 100);
    check(worst.epoch == 7 && worst.sequence == 4 && worst.observed_ns == 2000);
}
