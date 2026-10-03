#include "application/resources.hpp"

namespace wsprrypico::application {
Envelope validate_envelope(wtp::json::Value root, std::string_view schema, std::string_view payload,
                           std::string_view device, std::string_view boot) {
    using namespace wtp::json;
    if (!fields(root, {"schema", "target", payload}))
        return Envelope::Invalid;
    const auto version = *root.get("schema"), destination = *root.get("target");
    if (version.type() != '"' || !fields(destination, {"scope", "device_id", "boot_id"}))
        return Envelope::Invalid;
    for (const auto name : {"scope", "device_id", "boot_id"})
        if (destination.get(name)->type() != '"')
            return Envelope::Invalid;
    if (version.string() != schema)
        return Envelope::UnsupportedSchema;
    if (destination.get("scope")->string() != "member" ||
        destination.get("device_id")->string() != device ||
        destination.get("boot_id")->string() != boot)
        return Envelope::TargetMismatch;
    return Envelope::Valid;
}
std::string target(std::string_view device, std::string_view boot) {
    return "{\"scope\":\"member\",\"device_id\":" + wtp::json::quote(device) +
           ",\"boot_id\":" + wtp::json::quote(boot) + "}";
}
std::string station(const standalone::Config& c) {
    return "{\"callsign\":" + wtp::json::quote(c.callsign) +
           ",\"locator\":" + wtp::json::quote(c.locator) +
           ",\"power_dbm\":" + std::to_string(c.power_dbm) + "}";
}
std::string capabilities() {
    return "{\"management_carrier\":\"authenticated_https\","
           "\"application_read\":true,\"station_write\":true,\"hardware_write\":true,"
           "\"max_update_bytes\":1024,\"max_config_bytes\":1800,"
           "\"hardware_activation\":\"restart\",\"station_encoding\":\"wspr_type1\","
           "\"station_power_meaning\":\"reported_wspr_dbm\","
           "\"recurrence_authorities\":[\"member\"],\"autonomous_modes\":[\"wspr\"],"
           "\"unavailable\":[\"recurrence_transfer\",\"si5351\",\"amplifier\",\"lpf\","
           "\"drive\",\"reference_calibration\",\"waveform_preferences\","
           "\"usb_json_management\",\"plain_lan_json_management\",\"ble_json_management\"]}";
}
} // namespace wsprrypico::application
