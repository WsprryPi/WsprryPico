#include "provisioning/pico/consumer_claim_platform.hpp"

#include "network/bootstrap_codec.hpp"
#include "network/pico/owner_signature.hpp"
#include "pico/time.h"
#include "provisioning/pico/consumer_tls_generator.hpp"
#include "provisioning/pico/consumer_tls_validator.hpp"
#include "time/sntp.hpp"

#include <algorithm>
#include <array>
#include <vector>

namespace wsprrypico::provisioning {
void PicoConsumerClaimPlatform::begin_station_trial() {
    // A new attempt cannot borrow a time observation made on the previous
    // station association. The next trusted_utc_now() must see fresh SNTP.
    arbiter_.invalidate(time::ObservationSource::Sntp);
}

bool PicoConsumerClaimPlatform::safe_to_commit() {
    const auto access_ok =
        access_.state() == AccessStoreState::Erased ||
        (access_.state() == AccessStoreState::Healthy && access_.record() &&
         !access_.record()->reset.pending() && !access_.record()->field_mode &&
         access_.record()->bond_count == 0 && access_.record()->default_password);
    const auto activity = service_.activity();
    return access_ok && !activity.owned && !activity.output_active &&
           activity.state != wtp::State::Loaded && activity.state != wtp::State::Armed &&
           activity.state != wtp::State::Running && activity.state != wtp::State::Failed;
}

std::uint64_t PicoConsumerClaimPlatform::monotonic_now_ms() {
    return time_us_64() / 1000;
}

bool PicoConsumerClaimPlatform::station_ready(std::string_view ssid) {
    const auto address = network_.ipv4();
    return !ssid.empty() && network_.station_ssid() == ssid && network_.link_up() &&
           !address.empty() && address != "0.0.0.0";
}

std::optional<std::uint64_t> PicoConsumerClaimPlatform::trusted_utc_now() {
    const auto snapshot = service_.clock_snapshot();
    const auto source = arbiter_.status();
    if (source.source != time::ActiveTimeSource::Sntp || source.age_ns > 10'000'000'000ULL ||
        snapshot.state != wtp::ClockState::Synchronized ||
        snapshot.leap != wtp::LeapState::Normal || snapshot.uncertainty_ns > 1'000'000'000ULL ||
        snapshot.utc_now_ns < time::sntp_min_utc_ns || snapshot.utc_now_ns >= time::sntp_max_utc_ns)
        return {};
    return snapshot.utc_now_ns / 1'000'000'000ULL;
}

bool PicoConsumerClaimPlatform::valid_owner_point(std::string_view point_b64url) {
    std::vector<std::uint8_t> decoded;
    if (!network::bootstrap_unb64url(point_b64url, decoded, 65, 65))
        return false;
    std::array<std::uint8_t, 65> point{};
    std::copy(decoded.begin(), decoded.end(), point.begin());
    std::fill(decoded.begin(), decoded.end(), 0);
    const bool valid = network::valid_owner_public_key(point);
    point.fill(0);
    return valid;
}

bool PicoConsumerClaimPlatform::generate_tls(std::string_view device_id, std::string_view hostname,
                                             std::uint64_t utc_now, ConsumerTls& out) {
    return generate_consumer_tls(device_id, hostname, utc_now, out);
}

bool PicoConsumerClaimPlatform::valid_tls(const ConsumerTls& tls, std::string_view device_id,
                                          std::uint64_t utc_now) {
    return validate_consumer_tls(tls, device_id, utc_now);
}
} // namespace wsprrypico::provisioning
