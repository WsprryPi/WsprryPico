#include "application/config_update.hpp"

namespace wsprrypico::application {
namespace {
using wtp::json::fields;
using wtp::json::quote;
using wtp::json::Value;

bool config_fields(Value value, bool partial, bool drive) {
    if (!drive && value.get("gpio_drive_ma"))
        return false;
    if (partial)
        return fields(value, {},
                      {"version", "enabled", "station", "wifi", "schedules", "expires_utc_s",
                       "pins", "allow_unqualified_frequency", "allow_non_amateur_frequency",
                       "gpio_drive_ma"}) &&
               !fields(value, {});
    return fields(value, {"version", "enabled", "station", "wifi", "schedules"},
                  {"expires_utc_s", "pins", "allow_unqualified_frequency",
                   "allow_non_amateur_frequency", "gpio_drive_ma"});
}

void member(std::string& result, std::string_view name, std::string_view raw) {
    if (result.size() > 1)
        result += ',';
    result += quote(name) + ':' + std::string(raw);
}
} // namespace

Envelope validate_config_update(Value root, std::string_view device, std::string_view boot,
                                bool drive) {
    if (!fields(root, {"schema", "target", "mode", "config"}))
        return Envelope::Invalid;
    const auto schema = *root.get("schema"), target = *root.get("target"), mode = *root.get("mode");
    if (schema.type() != '"' || mode.type() != '"' ||
        (mode.string() != "merge" && mode.string() != "replace") ||
        !fields(target, {"scope", "device_id", "boot_id"}))
        return Envelope::Invalid;
    for (const auto name : {"scope", "device_id", "boot_id"})
        if (target.get(name)->type() != '"')
            return Envelope::Invalid;
    if (schema.string() != (drive ? "transmitter-config-update/2" : config_update_schema))
        return Envelope::UnsupportedSchema;
    if (target.get("scope")->string() != "member" || target.get("device_id")->string() != device ||
        target.get("boot_id")->string() != boot)
        return Envelope::TargetMismatch;
    return Envelope::Valid;
}

std::optional<std::string> config_candidate(Value supplied,
                                            const std::optional<standalone::Config>& current,
                                            ConfigWrite mode, bool drive) {
    const bool partial = mode == ConfigWrite::Merge;
    if (mode == ConfigWrite::Legacy && supplied.raw.size() > standalone::max_config_bytes)
        return {};
    if (!config_fields(supplied, partial, drive) || (partial && !current))
        return {};
    const auto station = supplied.get("station"), wifi = supplied.get("wifi");
    if (partial && station &&
        (!fields(*station, {}, {"callsign", "locator", "power_dbm"}) || fields(*station, {})))
        return {};
    if (wifi &&
        !(partial ? fields(*wifi, {}, {"ssid", "password", "ntp_ipv4"}) && !fields(*wifi, {})
                  : fields(*wifi, {"ssid", "password"}, {"ntp_ipv4"})))
        return {};
    const auto previous_text = current ? standalone::serialize_config(*current) : "{}";
    const auto previous = wtp::json::parse(previous_text);
    if (!previous)
        return {};
    const bool preserve = mode != ConfigWrite::Replace && current.has_value();
    std::string result = "{";
    for (const auto name :
         {"version", "enabled", "station", "wifi", "schedules", "expires_utc_s", "pins",
          "allow_unqualified_frequency", "allow_non_amateur_frequency", "gpio_drive_ma"}) {
        const auto input = supplied.get(name), prior = previous->get(name);
        if (input && ((partial && name == std::string_view("station")) ||
                      name == std::string_view("wifi"))) {
            std::string object = "{";
            const auto append = [&](std::string_view field) -> bool {
                const auto value = input->get(field);
                if (value) {
                    if (name == std::string_view("wifi") && field == "password" &&
                        value->raw == "null") {
                        if (!current)
                            return false;
                        member(object, field, quote(current->password));
                    } else
                        member(object, field, std::string(value->raw));
                } else if (preserve && prior) {
                    if (const auto saved = prior->get(field))
                        member(object, field, std::string(saved->raw));
                }
                return true;
            };
            if (name == std::string_view("station")) {
                for (const auto field : {"callsign", "locator", "power_dbm"})
                    if (!append(field))
                        return {};
            } else {
                for (const auto field : {"ssid", "password", "ntp_ipv4"})
                    if (!append(field))
                        return {};
            }
            object += '}';
            member(result, name, object);
        } else if (input)
            member(result, name, std::string(input->raw));
        else if (preserve && prior)
            member(result, name, std::string(prior->raw));
    }
    result += '}';
    if (result.size() > standalone::max_config_bytes)
        return {};
    return result;
}

std::string config_update_capabilities() {
    return "{\"schema\":\"transmitter-config-update/1\","
           "\"path\":\"/api/v1/config/update\",\"method\":\"POST\","
           "\"modes\":[\"merge\",\"replace\"],\"max_update_bytes\":2048,"
           "\"max_config_bytes\":1800,\"legacy_put_omission\":\"preserve_optional\"}";
}
} // namespace wsprrypico::application
