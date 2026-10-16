#pragma once
#include "standalone/storage.hpp"
#include "wtp/json.hpp"

#include <array>

namespace wsprrypico::standalone {
// Non-runnable, bounded saved progress. This class cannot save Config, reserve a
// slot, change a profile, or reach a scheduler/engine/network adapter.
inline constexpr std::array<std::string_view, 10> progress_fields{
    "callsign", "locator", "power_dbm", "enabled", "schedules", "expires_utc_s",
    "pins", "frequency_policy", "wifi", "ntp_ipv4"};
inline constexpr std::size_t max_progress_bytes = 1400;
bool valid_progress_field(std::string_view name, wtp::json::Value value);
class Progress {
  public:
    explicit Progress(Flash& flash) : flash_(flash), journal_(flash, 0, 2048) {}
    bool load();
    bool erase();
    // Caller validates the envelope, authority and common revision first.
    // Empty optional means no verified commit; never report field success then.
    std::optional<std::string> save(wtp::json::Value fields, std::string_view receipt);
    std::string fields(bool redacted = true, bool station_only = false) const;
    std::string station_fields(const std::optional<Config>& applied) const;
    std::optional<Config> station_candidate(const std::optional<Config>& applied) const;
    std::optional<Config> candidate(const std::optional<Config>& applied, std::string_view domain = "all") const;
    bool healthy() const { return healthy_ && journal_.healthy(); }
    std::uint64_t sequence() const { return journal_.sequence(); }
    const std::string& receipt() const { return receipt_; }
    std::string outcomes(bool station_only = false) const;
  private:
    Flash& flash_;
    Journal journal_;
    bool healthy_ = false;
    std::array<std::optional<std::string>, progress_fields.size()> values_;
    std::string receipt_ = "null", outcomes_ = "{}";
};
} // namespace wsprrypico::standalone
