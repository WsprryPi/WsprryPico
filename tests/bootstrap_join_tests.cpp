#include "network/bootstrap_codec.hpp"
#include "network/bootstrap_join.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <vector>

using namespace wsprrypico::network;
namespace provisioning = wsprrypico::provisioning;

struct FaultMedia : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> bytes{};
    unsigned writes = 0, reads_to_fail = 0;
    bool commit_written = false, fail_program = false;
    FaultMedia() {
        bytes.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> output) override {
        if (commit_written && reads_to_fail) {
            --reads_to_fail;
            return false;
        }
        std::copy_n(bytes.begin() + at, output.size(), output.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        std::fill_n(bytes.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> page) override {
        ++writes;
        if (fail_program)
            return false;
        std::copy(page.begin(), page.end(), bytes.begin() + at);
        if (at % provisioning::profile_slot_size ==
            provisioning::profile_slot_size - provisioning::profile_page_size)
            commit_written = true;
        return true;
    }
};

void resolved_commit_lifecycle() {
    constexpr auto device = "0123456789abcdef0123456789abcdef";
    FaultMedia media;
    provisioning::ProfileStore store(media);
    assert(store.load());
    provisioning::NetworkProfile profile{device, "Home Net", "test-password", "pool.ntp.org",
                                         std::string(64, 'a')};
    auto payload = provisioning::serialize_network_profile(profile);
    BootstrapCommitGate committed;
    assert(committed.begin());
    assert(committed.commit(store, provisioning::ProfileSource::NetworkOnly, payload, 100) ==
           provisioning::SetupCommitResult::Committed);
    const auto writes = media.writes;
    assert(!committed.begin() && !committed.trial_allowed() && committed.result_verified());
    assert(committed.commit(store, provisioning::ProfileSource::NetworkOnly, payload, 200) ==
           provisioning::SetupCommitResult::Committed);
    assert(media.writes == writes && store.sequence() == 1);
    BootstrapCommitGate replacement;
    assert(replacement.begin());
    profile.request_sha256 = std::string(64, 'b');
    payload = provisioning::serialize_network_profile(profile);
    media.fail_program = true;
    assert(replacement.commit(store, provisioning::ProfileSource::NetworkOnly, payload, 300) ==
           provisioning::SetupCommitResult::NotCommitted);
    assert(store.healthy() && store.sequence() == 1);
    assert(replacement.cancellation_allowed() && replacement.result_verified());
    assert(!replacement.restart_due(1'000'000));
    media.fail_program = false;
    assert(replacement.begin() && replacement.trial_allowed());
    assert(replacement.commit(store, provisioning::ProfileSource::NetworkOnly, payload, 400) ==
           provisioning::SetupCommitResult::Committed);
    assert(store.sequence() == 2 &&
           provisioning::setup_request_digest(store, device) == profile.request_sha256);
}

void uncertain_commit_lifecycle() {
    constexpr auto device = "0123456789abcdef0123456789abcdef";
    FaultMedia media;
    provisioning::ProfileStore store(media);
    assert(store.load());
    provisioning::NetworkProfile profile{device, "Home Net", "test-password", "pool.ntp.org",
                                         std::string(64, 'a')};
    auto payload = provisioning::serialize_network_profile(profile);
    BootstrapCommitGate gate;
    assert(gate.begin());
    assert(gate.trial_allowed() && gate.cancellation_allowed());
    media.reads_to_fail = 2; // Commit persists; verification and reconciliation cannot read it.
    assert(gate.commit(store, provisioning::ProfileSource::NetworkOnly, payload, 100) ==
           provisioning::SetupCommitResult::Reconcile);
    const auto writes = media.writes;
    assert(gate.reconcile() && !gate.trial_allowed() && !gate.cancellation_allowed());
    assert(!gate.result_verified() && !gate.begin());
    // Expiry/cancel/ACK and repeated polling cannot invoke another journal save.
    for (unsigned poll = 0; poll < 100; ++poll)
        assert(gate.commit(store, provisioning::ProfileSource::NetworkOnly, payload,
                           100'000 + poll) == provisioning::SetupCommitResult::Reconcile);
    assert(media.writes == writes);
    assert(!gate.restart_due(99) && !gate.restart_due(60'099));
    assert(gate.restart_due(60'100)); // Repeated polls do not move the original deadline.
    provisioning::scrub(profile);
    assert(profile.ssid.empty() && profile.password.empty() && profile.request_sha256.empty());
    payload.clear();
    media.reads_to_fail = 0;
    provisioning::ProfileStore rebooted(media);
    assert(rebooted.load() && rebooted.sequence() == 1);
    assert(provisioning::setup_request_digest(rebooted, device) == std::string(64, 'a'));
    BootstrapCommitGate after_reboot;
    assert(!after_reboot.reconcile() && after_reboot.result_verified() && after_reboot.begin());
    assert(!after_reboot.restart_due(1'000'000));
}

int main() {
    uncertain_commit_lifecycle();
    resolved_commit_lifecycle();
    BootstrapJoinGate gate;
    gate.begin(100);
    assert(gate.trial(200, false, false) == BootstrapJoinResult::Waiting);
    assert(gate.trial(300, true, false) == BootstrapJoinResult::Waiting); // DHCP not ready.
    assert(gate.trial(45'100, true, true) == BootstrapJoinResult::TimedOut);
    gate.finish();
    assert(gate.trial(45'200, true, true) == BootstrapJoinResult::TimedOut);
    gate.begin(300'000);
    assert(gate.trial(301'000, true, true) == BootstrapJoinResult::Ready);
    gate.finish();
    assert(gate.trial(301'001, true, true) == BootstrapJoinResult::TimedOut);
    BootstrapJoinGate reboot;
    assert(reboot.trial(1'000, true, true) == BootstrapJoinResult::TimedOut);

    const std::array<std::uint8_t, 4> bytes{0, 0xff, 0x10, 0x42};
    assert(bootstrap_hex(bytes) == "00ff1042");
    std::array<std::uint8_t, 4> decoded{};
    assert(bootstrap_unhex("00ff1042", decoded) && decoded == bytes);
    assert(!bootstrap_unhex("00FF1042", decoded));
    const auto encoded = bootstrap_b64url(bytes);
    std::vector<std::uint8_t> buffer;
    assert(bootstrap_unb64url(encoded, buffer, 4, 4));
    assert(std::equal(buffer.begin(), buffer.end(), bytes.begin()));
    assert(!bootstrap_unb64url(encoded + "=", buffer, 4, 4));
    assert(!bootstrap_unb64url("AB", buffer, 1, 1)); // Nonzero pad bits.
}
