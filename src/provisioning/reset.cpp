#include "provisioning/reset.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::provisioning {
namespace {
bool zero(const wtp::PayloadDigest& digest) {
    return std::all_of(digest.begin(), digest.end(), [](std::uint8_t value) { return value == 0; });
}
} // namespace

bool ResetCoordinator::save(AccessRecord& record, ResetPhase phase) {
    record.reset.phase = phase;
    return access_.replace(record);
}

ResetResult ResetCoordinator::begin(ResetLevel level, ProfileSource target_source,
                                    const wtp::PayloadDigest& request_digest) {
    if (!access_.healthy() || !profiles_.healthy())
        return ResetResult::StorageFault;
    if (pending())
        return ResetResult::Pending;
    if (!idle_for_access(targets_.activity()))
        return ResetResult::Busy;
    if (level == ResetLevel::None || zero(request_digest) ||
        (level == ResetLevel::Access && target_source != ProfileSource::Unprovisioned) ||
        (level != ResetLevel::Access && target_source != ProfileSource::Unprovisioned &&
         target_source != ProfileSource::BuildBundle))
        return ResetResult::Invalid;
    auto record = *access_.record();
    record.reset.level = level;
    record.reset.target_source = target_source;
    record.reset.request_digest = request_digest;
    if (!save(record, ResetPhase::Intent)) {
        scrub(record);
        return ResetResult::StorageFault;
    }
    scrub(record);
    return ResetResult::Pending;
}

ResetResult ResetCoordinator::resume() {
    if (!access_.healthy() || !profiles_.healthy())
        return ResetResult::StorageFault;
    if (!pending())
        return ResetResult::Complete;
    if (!idle_for_access(targets_.activity()))
        return ResetResult::Busy;
    auto record = *access_.record();
    const auto level = record.reset.level;
    if (record.reset.phase == ResetPhase::Intent) {
        if (level != ResetLevel::Access &&
            !profiles_.select(record.reset.target_source)) {
            scrub(record);
            return ResetResult::StorageFault;
        }
        if (!save(record, ResetPhase::SourceSelected)) {
            scrub(record);
            return ResetResult::StorageFault;
        }
    }
    if (record.reset.phase == ResetPhase::SourceSelected) {
        if (record.epoch == std::numeric_limits<std::uint64_t>::max()) {
            scrub(record);
            return ResetResult::StorageFault;
        }
        ++record.epoch;
        record.password.assign(identity_.default_password);
        record.default_password = true;
        record.field_mode = level != ResetLevel::Full;
        record.ble_disabled = false;
        record.bonds.fill(0);
        record.bond_count = 0;
        if (!save(record, ResetPhase::AccessReset)) {
            scrub(record);
            return ResetResult::StorageFault;
        }
    }
    if (record.reset.phase == ResetPhase::AccessReset) {
        if (level == ResetLevel::Full &&
            (!targets_.erase_operational() || !targets_.operational_erased())) {
            scrub(record);
            return ResetResult::TargetFault;
        }
        if (!save(record, ResetPhase::OperationalErased)) {
            scrub(record);
            return ResetResult::StorageFault;
        }
    }
    if (record.reset.phase == ResetPhase::OperationalErased) {
        if (!targets_.erase_bonds() || !targets_.bonds_erased()) {
            record.ble_disabled = true;
            (void)access_.replace(record);
            scrub(record);
            return ResetResult::TargetFault;
        }
        record.ble_disabled = false;
        if (!save(record, ResetPhase::BondsCleared)) {
            scrub(record);
            return ResetResult::StorageFault;
        }
    }
    if (record.reset.phase != ResetPhase::BondsCleared) {
        scrub(record);
        return ResetResult::StorageFault;
    }
    record.reset = {};
    if (!access_.replace(record)) {
        scrub(record);
        return ResetResult::StorageFault;
    }
    scrub(record);
    return ResetResult::Complete;
}
} // namespace wsprrypico::provisioning
