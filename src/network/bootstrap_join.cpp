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
bool BootstrapCommitGate::begin() {
    if (settled_ && result_ != provisioning::SetupCommitResult::NotCommitted)
        return false;
    settled_ = false;
    return true;
}
provisioning::SetupCommitResult BootstrapCommitGate::commit(provisioning::ProfileStore& store,
                                                            provisioning::ProfileSource source,
                                                            std::string_view payload,
                                                            std::uint64_t now_ms) {
    if (settled_)
        return result_;
    result_ = provisioning::commit_setup_profile(store, source, payload);
    settled_ms_ = now_ms;
    settled_ = true;
    return result_;
}
bool BootstrapCommitGate::restart_due(std::uint64_t now_ms) const {
    return reconcile() && now_ms >= settled_ms_ && now_ms - settled_ms_ >= 60'000;
}
} // namespace wsprrypico::network
