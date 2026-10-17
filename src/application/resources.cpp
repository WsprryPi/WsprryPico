#include "application/resources.hpp"

#include "encoding/wspr.hpp"

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
std::string capabilities(bool usb_management) {
    return "{\"management_carrier\":" +
           wtp::json::quote(usb_management ? "usb_physical" : "authenticated_https") +
           ","
           "\"application_read\":true,\"station_write\":true,\"hardware_write\":true,"
           "\"max_update_bytes\":1024,\"max_config_bytes\":1800,"
           "\"hardware_activation\":\"restart\",\"station_encoding\":\"wspr_type1\","
           "\"station_power_meaning\":\"reported_wspr_dbm\","
           "\"recurrence_authorities\":[\"member\"],\"autonomous_modes\":[\"wspr\"],"
           "\"unavailable\":[\"recurrence_transfer\",\"si5351\",\"amplifier\",\"lpf\","
           "\"drive\",\"reference_calibration\",\"waveform_preferences\"," +
           (usb_management ? "" : "\"usb_json_management\",") +
           "\"plain_lan_json_management\",\"ble_json_management\"]}";
}
std::string wspr_plan(const standalone::Config& config) {
    const auto plan = encoding::wspr_plan(config.callsign, config.locator, config.power_dbm);
    std::string types = "[";
    if (plan)
        for (unsigned i = 0; i < plan->count; ++i) {
            if (i)
                types += ',';
            types += wtp::json::quote("type" + std::to_string(unsigned(plan->frames[i].type)));
        }
    types += ']';
    std::string rationale =
        !plan ? "Unsupported station " + config.callsign + " with locator " + config.locator +
                    ". Check affix lengths, brackets and six-character locator requirements."
        : plan->count == 2
            ? "Type 2 announces the compound call; Type 3 carries its hash and six-character "
              "locator in the next even-minute window. Receiver hash context may be needed."
        : plan->frames[0].type == encoding::WsprType::Type3
            ? "Type 3 carries a callsign hash and six-character locator. Receiver hash context is "
              "needed to resolve the full call."
        : plan->frames[0].type == encoding::WsprType::Type2
            ? "Type 2 carries the compound call and power; it carries no locator."
            : "Type 1 carries the call, first four locator characters and power. All six saved "
              "locator characters are retained.";
    const std::string_view alternate =
        plan ? std::string_view(plan->alternate_call.data(), plan->alternate_length)
             : std::string_view{};
    if (!alternate.empty())
        rationale += " Type 2 is ambiguous with " + std::string(alternate) +
                     "; receivers may choose either. The saved call and Type 3 hash retain the "
                     "requested identity.";
    return "{\"schema\":\"wspr-plan/1\",\"supported\":" + std::string(plan ? "true" : "false") +
           ",\"type2_ambiguous\":" + (plan && plan->type2_ambiguous ? "true" : "false") +
           ",\"alternate_callsign\":" + (alternate.empty() ? "null" : wtp::json::quote(alternate)) +
           ",\"frame_types\":" + types + ",\"frames\":" + std::to_string(plan ? plan->count : 0) +
           ",\"slot_separation_s\":120,\"rationale\":" + wtp::json::quote(rationale) + "}";
}
} // namespace wsprrypico::application
