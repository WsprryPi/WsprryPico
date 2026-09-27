#include "network/bootstrap_join.hpp"

namespace wsprrypico::network {
void BootstrapJoinGate::begin(std::uint64_t now_ms) {
    started_ms_ = now_ms;
    started_ = true;
}
BootstrapJoinResult BootstrapJoinGate::trial(std::uint64_t now_ms, bool link, bool address) const {
    if (!started_ || now_ms < started_ms_ || now_ms - started_ms_ >= 45'000)
        return BootstrapJoinResult::TimedOut;
    return link && address ? BootstrapJoinResult::Ready : BootstrapJoinResult::Waiting;
}
void BootstrapJoinGate::finish() {
    started_ = false;
}
} // namespace wsprrypico::network
