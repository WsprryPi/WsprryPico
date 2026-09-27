#include "network/owner_challenge.hpp"

#include <cassert>
#include <cstdint>

using namespace wsprrypico::network;

namespace {
OwnerChallengeBinding binding() {
    OwnerChallengeBinding value;
    value.operation = OwnerOperation::NetworkReplace;
    value.device_id[0] = 1;
    value.boot_id[0] = 2;
    value.session_id[0] = 3;
    value.owner_key_sha256[0] = 4;
    value.owner_epoch = 1;
    value.profile_generation = 9;
    value.request_id[0] = 5;
    value.challenge[0] = 6;
    value.expiry_monotonic_ms = 31'000;
    return value;
}
bool take(OwnerChallengeSlot& slot, const OwnerChallengeBinding& value, std::uint64_t now_ms) {
    const auto route = owner_route(value.operation);
    OwnerSigningFields fields;
    fields.operation = value.operation;
    fields.method = route ? route->method : "POST";
    fields.path = route ? route->path : "/invalid";
    fields.device_id = value.device_id;
    fields.boot_id = value.boot_id;
    fields.owner_epoch = value.owner_epoch;
    fields.profile_generation = value.profile_generation;
    fields.request_id = value.request_id;
    fields.challenge = value.challenge;
    fields.expiry_monotonic_ms = value.expiry_monotonic_ms;
    const std::array<std::uint8_t, 16> sealed{};
    fields.sealed_body = sealed;
    return slot.take(fields, value.session_id, value.owner_key_sha256, now_ms).has_value();
}
} // namespace

int main() {
    OwnerChallengeSlot slot;
    auto ticket = binding();
    assert(!slot.issue(ticket, 0)); // More than 30 seconds.
    assert(slot.issue(ticket, 1'000));
    assert(!slot.issue(ticket, 1'001)); // One pending challenge.
    assert(take(slot, ticket, 1'001));
    assert(!take(slot, ticket, 1'002)); // One use.
    assert(slot.issue(ticket, 1'003));
    auto changed = ticket;
    changed.device_id[0] ^= 1;
    assert(!take(slot, changed, 1'004));
    assert(!take(slot, ticket, 1'005)); // A mismatched attempt burned it.
    assert(slot.issue(ticket, 1'006));
    changed = ticket;
    changed.boot_id[0] ^= 1;
    assert(!take(slot, changed, 1'007));
    assert(slot.issue(ticket, 1'008));
    changed = ticket;
    changed.session_id[0] ^= 1;
    assert(!take(slot, changed, 1'009));
    assert(slot.issue(ticket, 1'010));
    changed = ticket;
    changed.owner_key_sha256[0] ^= 1;
    assert(!take(slot, changed, 1'011));
    assert(slot.issue(ticket, 1'012));
    changed = ticket;
    ++changed.owner_epoch;
    assert(!take(slot, changed, 1'013));
    assert(slot.issue(ticket, 1'014));
    changed = ticket;
    ++changed.profile_generation;
    assert(!take(slot, changed, 1'015));
    assert(slot.issue(ticket, 1'016));
    changed = ticket;
    changed.operation = OwnerOperation::ServerRenew;
    assert(!take(slot, changed, 1'017));
    assert(slot.issue(ticket, 1'018));
    changed = ticket;
    changed.request_id[0] ^= 1;
    assert(!take(slot, changed, 1'019));
    assert(slot.issue(ticket, 1'020));
    changed = ticket;
    changed.challenge[0] ^= 1;
    assert(!take(slot, changed, 1'021));
    assert(slot.issue(ticket, 1'022));
    assert(!take(slot, ticket, 31'000)); // Expired at deadline.
    assert(slot.issue(ticket, 1'023));
    assert(!take(slot, ticket, 1'022)); // Monotonic rollback.
    assert(!slot.pending());
    assert(slot.issue(ticket, 1'024));
    assert(!slot.issue(ticket, 1'023)); // Rollback cancels and rejects.
    assert(!slot.pending());
    assert(slot.issue(ticket, 1'024));
    slot.cancel();
    assert(!take(slot, ticket, 1'025));

    changed = ticket;
    changed.operation = static_cast<OwnerOperation>(0xff);
    assert(!slot.issue(changed, 1'026));
    changed = ticket;
    changed.owner_epoch = 0;
    assert(!slot.issue(changed, 1'026));
    changed = ticket;
    changed.profile_generation = 0;
    assert(!slot.issue(changed, 1'026));
    changed = ticket;
    changed.challenge.fill(0);
    assert(!slot.issue(changed, 1'026));
    changed = ticket;
    changed.expiry_monotonic_ms = 1'026;
    assert(!slot.issue(changed, 1'026));
}
