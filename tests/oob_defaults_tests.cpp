// SPDX-License-Identifier: MIT
#include "application/config_update.hpp"
#include "encoding/morse.hpp"
#include "encoding/wspr.hpp"
#include "network_support.hpp"
#include "standalone/progress.hpp"

using namespace wsprrypico;
using network_test::Flash;
int main() {
    // An old record's omissions retain the original meanings on upgrade.
    const std::string legacy =
        R"({"version":1,"enabled":false,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":0},"wifi":{"ssid":"","password":""},"schedules":[]})";
    auto old = standalone::parse_config(legacy);
    REQUIRE(old && old->gpio_drive_ma == 4 && old->pins.amplifier_active_high);
    REQUIRE(!old->wspr_dial_frequency_hz && old->schedules.empty());
    Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load() && store.save(*old));
    const auto bytes = flash.bytes;
    standalone::Store reboot(flash);
    REQUIRE(reboot.load() && reboot.config() == old && flash.bytes == bytes);
    // Fresh station application gets the selected defaults, with no RF enablement.
    Flash drafts;
    standalone::Progress progress(drafts);
    REQUIRE(progress.load());
    auto fields = wtp::json::parse(R"({"callsign":"N0CALL","locator":"ZZ99","power_dbm":0})");
    REQUIRE(progress.save(*fields, std::string(64, 'a')));
    REQUIRE(!progress.station_candidate({}) && !progress.candidate({}, "station"));
    fields = wtp::json::parse(R"({"callsign":"AA0NT","locator":"EM18","power_dbm":0})");
    REQUIRE(progress.save(*fields, std::string(64, 'b')));
    const auto fresh = progress.candidate({}, "station");
    REQUIRE(fresh && !fresh->enabled && fresh->gpio_drive_ma == 12);
    REQUIRE(fresh->wspr_dial_frequency_hz == 14'095'600);
    REQUIRE(fresh->schedules == std::vector<standalone::Schedule>({{600, 0}}));
    REQUIRE(!fresh->pins.amplifier && !fresh->pins.amplifier_active_high);
    REQUIRE(fresh->pins.rf == 2 && fresh->pins.button == 14);
    // Applying a station edit to an existing installation retains its choices.
    auto custom = *old;
    custom.gpio_drive_ma = 8;
    custom.wspr_dial_frequency_hz = 10'138'700;
    custom.schedules = {{1200, 120}};
    const auto edited = progress.candidate(custom, "station");
    REQUIRE(edited && edited->gpio_drive_ma == 8 && edited->pins.amplifier_active_high);
    REQUIRE(edited->wspr_dial_frequency_hz == custom.wspr_dial_frequency_hz &&
            edited->schedules == custom.schedules);
    // Complete configuration saves go through the same fresh/default boundary.
    const std::string input = "{" + legacy.substr(13);
    auto supplied = wtp::json::parse(input);
    const auto candidate =
        application::config_candidate(*supplied, {}, application::ConfigWrite::Legacy, true, true);
    REQUIRE(candidate);
    const auto applied = standalone::parse_config(*candidate);
    REQUIRE(applied && applied->gpio_drive_ma == 12 &&
            applied->wspr_dial_frequency_hz == 14'095'600);
    REQUIRE(!applied->enabled && applied->schedules.empty()); // Explicit empty schedule wins.
    REQUIRE(!encoding::valid_station_details("N0CALL", "EM18", 0));
    REQUIRE(!encoding::valid_station_details("<N0CALL>", "EM18IG", 0));
    REQUIRE(!encoding::valid_station_details("AA0NT", "ZZ99", 0));
    encoding::MorseMessage message;
    message.text = "73 DE n0call";
    REQUIRE(encoding::measure_message(message).error == "replace_placeholder_callsign");
    std::cout << "Fresh defaults, placeholder refusal and saved-setting preservation passed\n";
}
