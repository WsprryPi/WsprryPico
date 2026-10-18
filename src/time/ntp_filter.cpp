#include "time/ntp_filter.hpp"

#include "wtp/json.hpp"

namespace wsprrypico::time {
std::optional<std::int32_t> oscillator_correction(const RateEstimate& rate) {
    if (!rate.qualified || rate.utc_rate_ppb < -100'000 || rate.utc_rate_ppb > 100'000)
        return {};
    const auto denominator = 1'000'000'000LL + rate.utc_rate_ppb;
    const auto numerator = -std::int64_t(rate.utc_rate_ppb) * 1'000'000'000LL;
    const auto rounded =
        (numerator + (numerator < 0 ? -denominator / 2 : denominator / 2)) / denominator;
    if (rounded < -100'000 || rounded > 100'000)
        return {};
    return std::int32_t(rounded);
}
std::string rate_json(const RateEstimate& r) {
    return "{\"qualified\":" + std::string(r.qualified ? "true" : "false") +
           ",\"utc_rate_ppb\":" + std::to_string(r.utc_rate_ppb) +
           ",\"uncertainty_ppb\":" + std::to_string(r.uncertainty_ppb) + ",\"generation\":\"" +
           std::to_string(r.generation) + "\",\"sampled_raw_ns\":\"" +
           std::to_string(r.sampled_ns) + "\",\"span_ns\":\"" + std::to_string(r.span_ns) +
           "\",\"samples\":" + std::to_string(r.samples) +
           ",\"reason\":" + wtp::json::quote(r.reason) + "}";
}
std::string sample_json(const NtpSample& s) {
    return "{\"id\":\"" + std::to_string(s.id) + "\",\"clock_epoch\":\"" + std::to_string(s.epoch) +
           "\",\"send_raw_ns\":\"" + std::to_string(s.send_ns) + "\",\"receive_raw_ns\":\"" +
           std::to_string(s.raw_ns) + "\",\"reference_utc_ns\":\"" + std::to_string(s.utc_ns) +
           "\",\"uncertainty_ns\":\"" + std::to_string(s.uncertainty_ns) + "\",\"rtt_ns\":\"" +
           std::to_string(s.rtt_ns) + "\",\"server_reference_ns\":\"" +
           std::to_string(s.reference_ns) + "\",\"server_receive_ns\":\"" +
           std::to_string(s.server_receive_ns) + "\",\"server_send_ns\":\"" +
           std::to_string(s.server_send_ns) +
           "\",\"root_delay_16_16\":" + std::to_string(s.root_delay) +
           ",\"root_dispersion_16_16\":" + std::to_string(s.root_dispersion) +
           ",\"stratum\":" + std::to_string(s.stratum) + ",\"leap\":" + std::to_string(s.leap) +
           ",\"precision\":" + std::to_string(s.precision) + "}";
}
} // namespace wsprrypico::time
