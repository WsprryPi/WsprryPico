#include "network/bootstrap_join.hpp"

namespace wsprrypico::network {
void BootstrapJoinGate::begin(std::uint64_t now_ms) {
    started_ms_ = now_ms;
    stable_since_ms_ = 0;
    started_ = true;
    committed_ = stable_ = false;
}
BootstrapJoinResult BootstrapJoinGate::trial(std::uint64_t now_ms, bool link, bool address) const {
    if (!started_ || now_ms < started_ms_ || now_ms - started_ms_ >= 45'000)
        return BootstrapJoinResult::TimedOut;
    return link && address ? BootstrapJoinResult::Ready : BootstrapJoinResult::Waiting;
}
void BootstrapJoinGate::finish(bool committed) {
    started_ = false;
    committed_ = committed;
    stable_ = false;
    stable_since_ms_ = 0;
}
void BootstrapJoinGate::service(std::uint64_t now_ms, bool link, bool address) {
    if (!committed_ || !link || !address) {
        stable_ = false;
        stable_since_ms_ = 0;
    } else if (!stable_ || now_ms < stable_since_ms_) {
        stable_ = true;
        stable_since_ms_ = now_ms;
    }
}
bool BootstrapJoinGate::withdraw(std::uint64_t now_ms, bool acknowledged, bool reply_active) const {
    if (!committed_ || !stable_ || reply_active || now_ms < stable_since_ms_)
        return false;
    return now_ms - stable_since_ms_ >= (acknowledged ? 3'000U : 60'000U);
}
} // namespace wsprrypico::network
