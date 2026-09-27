#include "network/bootstrap_codec.hpp"
#include "provisioning/consumer_claim.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <string>

using namespace wsprrypico;

namespace {
constexpr auto request_id = "11111111111111111111111111111111";

provisioning::ConsumerClaimBinding binding() {
    provisioning::ConsumerClaimBinding value;
    value.device_id = "fd6127d11d6aca42a9905fa3fb1bf1d5";
    value.boot_id = "22222222222222222222222222222222";
    value.slot_id = "33333333333333333333333333333333";
    std::array<std::uint8_t, 65> point{};
    point[0] = 4;
    point[64] = 1;
    value.owner_public_key = network::bootstrap_b64url(point);
    std::array<std::uint8_t, 32> ephemeral{};
    ephemeral[31] = 2;
    value.browser_public_key = network::bootstrap_b64url(ephemeral);
    value.browser_nonce = "44444444444444444444444444444444";
    value.origin = "http://192.168.4.1";
    return value;
}

std::string digest() {
    std::array<std::uint8_t, 16> request{};
    assert(network::bootstrap_unhex(request_id, request));
    return network::bootstrap_digest(request);
}
} // namespace

int main() {
    auto expected = binding();
    provisioning::ConsumerClaimSlot slot;
    assert(!slot.start(expected, 1000, true, true, true)); // Held before prompt.
    assert(!slot.start(expected, 1000, false, false, true));
    assert(!slot.start(expected, 1000, true, false, false));
    auto bad = expected;
    bad.origin = "http://evil.local";
    assert(!slot.start(bad, 1000, true, false, true));
    bad = expected;
    bad.source = provisioning::ProfileSource::RuntimeProfile;
    assert(!slot.start(bad, 1000, true, false, true));
    bad = expected;
    bad.source = provisioning::ProfileSource::NetworkOnly;
    assert(!slot.start(bad, 1000, true, false, true)); // Generation zero.

    assert(slot.start(expected, 1000, true, false, true));
    assert(slot.state() == provisioning::ConsumerClaimState::Identify);
    assert(!slot.start(expected, 1001, true, false, true)); // One claimant.
    assert(slot.binding() && *slot.binding() == expected);
    slot.sample(1100, true, true, true);
    slot.sample(1119, true, false, true); // 19 ms is contact bounce.
    assert(slot.state() == provisioning::ConsumerClaimState::Identify);
    slot.sample(1200, true, true, true);
    slot.sample(1220, true, false, true); // Device-side bounce threshold.
    assert(slot.state() == provisioning::ConsumerClaimState::Granted);
    bad = expected;
    bad.boot_id = "55555555555555555555555555555555";
    assert(!slot.consume(bad, request_id, 1301, true, true));
    assert(!slot.consume(expected, "bad", 1301, true, true));
    assert(slot.consume(expected, request_id, 1301, true, true));
    assert(!slot.consume(expected, request_id, 1302, true, true)); // Replay.
    assert(!slot.finish(true, std::string(64, 'a'), 1, 1303, true));
    assert(!slot.finish(true, digest(), 2, 1303, true));
    assert(slot.finish(true, digest(), 1, 1303, true));
    assert(slot.committed() && slot.committed_generation() == 1);
    assert(slot.request_sha256() == digest());
    assert(!slot.binding());
    slot.expire(1303 + provisioning::ConsumerClaimSlot::terminal_window_ms);
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.request_sha256().empty());

    expected.source = provisioning::ProfileSource::NetworkOnly;
    expected.generation = 1;
    assert(slot.start(expected, 2000, true, false, true));
    slot.sample(2100, true, true, true);
    slot.sample(2802, true, false, true); // Ordinary 702 ms human press.
    assert(slot.state() == provisioning::ConsumerClaimState::Granted);
    assert(slot.consume(expected, request_id, 2803, true, true));
    assert(slot.finish(true, digest(), 2, 2804, true));
    slot.cancel();

    expected.source = provisioning::ProfileSource::Unprovisioned;
    assert(slot.start(expected, 2800, true, false, true)); // Committed reset tombstone.
    slot.sample(2900, true, true, true);
    slot.sample(3000, true, false, true);
    assert(slot.consume(expected, request_id, 3001, true, true));
    assert(slot.finish(true, digest(), 2, 3002, true));
    slot.cancel();
    expected.source = provisioning::ProfileSource::NetworkOnly;

    assert(slot.start(expected, 3005, true, false, true));
    slot.sample(3105, true, true, true);
    slot.sample(3205, true, false, true);
    slot.sample(3206, false, false, true); // Safety drift after grant.
    assert(slot.state() == provisioning::ConsumerClaimState::None);

    assert(slot.start(expected, 3000, true, false, true));
    slot.sample(3100, true, true, true);
    slot.sample(13101, true, false, true); // Stuck hold is bounded internally.
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 4000, true, false, true));
    slot.expire(4000 + provisioning::ConsumerClaimSlot::physical_window_ms);
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 5000, true, false, true));
    slot.sample(5100, false, false, true); // Unsafe sampler.
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 6000, true, false, true));
    slot.sample(6100, true, true, true);
    slot.sample(6200, true, false, true);
    assert(!slot.consume(expected, request_id, 6201, true, false)); // Activity drift.
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 6250, true, false, true));
    slot.sample(6300, true, true, true);
    slot.sample(6400, true, false, true);
    assert(!slot.consume(expected, request_id, 6401, false, true)); // Sampler drift.
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 7000, true, false, true));
    slot.sample(7100, true, true, true);
    slot.sample(7200, true, false, true);
    slot.expire(7200 + provisioning::ConsumerClaimSlot::submit_window_ms);
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 8000, true, false, true));
    slot.sample(8100, true, true, true);
    slot.sample(8200, true, false, true);
    assert(slot.consume(expected, request_id, 8201, true, true));
    slot.expire(8201 + provisioning::ConsumerClaimSlot::trial_window_ms);
    assert(slot.state() == provisioning::ConsumerClaimState::None);

    assert(slot.start(expected, 10000, true, false, true));
    slot.sample(10100, true, true, true);
    slot.sample(10200, true, false, true);
    assert(slot.consume(expected, request_id, 10201, true, true));
    assert(slot.finish(false, {}, 0, 10202, true));
    assert(!slot.committed() && slot.request_sha256().empty());
    assert(!slot.binding());
    slot.cancel();
    assert(slot.start(expected, 11000, true, false, true));
    slot.sample(11100, true, true, true);
    slot.sample(11200, true, false, true);
    assert(slot.consume(expected, request_id, 11201, true, true));
    assert(!slot.finish(true, digest(), 2, 11202, false)); // Output drift.
    assert(slot.state() == provisioning::ConsumerClaimState::None);

    // A whole-gesture callback returns only after release. Its late return
    // must not invalidate a press captured inside the device's prompt window.
    assert(slot.start(expected, 12000, true, false, true));
    assert(slot.grant_captured(12000 + provisioning::ConsumerClaimSlot::physical_window_ms + 50,
                               true, true, 702, true));
    assert(slot.state() == provisioning::ConsumerClaimState::Granted);
    assert(slot.consume(expected, request_id,
                        12000 + provisioning::ConsumerClaimSlot::physical_window_ms + 51, true,
                        true));
    slot.cancel();
    assert(slot.start(expected, 13000, true, false, true));
    assert(!slot.grant_captured(13100, false, true, 702, true));
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 14000, true, false, true));
    assert(!slot.grant_captured(14100, true, false, 0, true));
    assert(slot.state() == provisioning::ConsumerClaimState::None);
    assert(slot.start(expected, 15000, true, false, true));
    assert(!slot.grant_captured(15100, true, true, 11'000, true));
    assert(slot.state() == provisioning::ConsumerClaimState::None);
}
