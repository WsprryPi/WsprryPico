// SPDX-License-Identifier: MIT
#include "hardware/filter_settings.hpp"

#include "wtp/json.hpp"

#include <charconv>

namespace wsprrypico::hardware {
namespace {
bool name_valid(std::string_view s) {
    if (s.empty() || s.size() > 16 || s.front() == ' ' || s.back() == ' ')
        return false;
    for (const char c : s)
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == ' ' || c == '-' || c == '_' || c == '/'))
            return false;
    return true;
}
bool number(wtp::json::Value v, unsigned& n) {
    if (v.raw.empty() || v.type() < '0' || v.type() > '9')
        return false;
    const std::string raw(v.raw);
    const auto r = std::from_chars(raw.data(), raw.data() + raw.size(), n);
    return r.ec == std::errc{} && r.ptr == raw.data() + raw.size();
}
} // namespace
std::string validate_filters(const FilterSettings& s, const PinPlan& pins) {
    if (s.output_count > s.outputs.size() || s.range_count > s.ranges.size() ||
        s.release_ms > s.maximum_delay_ms || s.settle_ms > s.maximum_delay_ms)
        return "filter_limits";
    auto combined = pins;
    for (unsigned i = 0; i < s.output_count; ++i) {
        const auto& o = s.outputs[i];
        if (!o.id || o.id > s.maximum_outputs || !name_valid(o.name))
            return "invalid_filter_selector";
        for (unsigned j = 0; j < i; ++j)
            if (s.outputs[j].id == o.id || s.outputs[j].name == o.name)
                return "duplicate_filter_selector";
        combined.lpf.push_back(o.gp);
    }
    const auto allocation = validate(combined);
    if (!allocation.valid())
        return "filter_" + allocation.error + "_" + allocation.role + "_" + allocation.owner;
    for (unsigned i = 0; i < s.range_count; ++i) {
        const auto& r = s.ranges[i];
        bool found = false;
        for (unsigned j = 0; j < s.output_count; ++j)
            found = found || s.outputs[j].id == r.selector;
        if (!found || !name_valid(r.name) || !r.low_hz || r.high_hz > 1'000'000'000 ||
            r.low_hz > r.high_hz)
            return "invalid_filter_range";
        for (unsigned j = 0; j < i; ++j) {
            const auto& p = s.ranges[j];
            if (p.name == r.name)
                return "duplicate_filter_range";
            if (p.selector != r.selector && r.low_hz <= p.high_hz && p.low_hz <= r.high_hz)
                return "ambiguous_filter_range";
        }
    }
    return {};
}
std::optional<FilterSettings> parse_filters(std::string_view text) {
    using namespace wtp::json;
    if (text.size() > FilterSettings::maximum_bytes)
        return {};
    const auto root = parse(text);
    if (!root || !fields(*root, {"policy", "release_ms", "settle_ms", "selectors", "ranges"}))
        return {};
    const auto policy = *root->get("policy");
    if (policy.type() != '"' ||
        (policy.string() != "fixed_manual" && policy.string() != "required"))
        return {};
    FilterSettings s;
    s.required = policy.string() == "required";
    if (!number(*root->get("release_ms"), s.release_ms) ||
        !number(*root->get("settle_ms"), s.settle_ms) || root->get("selectors")->type() != '[' ||
        root->get("ranges")->type() != '[')
        return {};
    const auto outputs = root->get("selectors")->elements(s.maximum_outputs + 1);
    const auto ranges = root->get("ranges")->elements(s.maximum_ranges + 1);
    if (outputs.size() > s.maximum_outputs || ranges.size() > s.maximum_ranges)
        return {};
    for (const auto v : outputs) {
        if (!fields(v, {"id", "name", "gp", "active_high"}))
            return {};
        auto& o = s.outputs[s.output_count++];
        if (!number(*v.get("id"), o.id) || !number(*v.get("gp"), o.gp) ||
            v.get("name")->type() != '"' ||
            (v.get("active_high")->raw != "true" && v.get("active_high")->raw != "false"))
            return {};
        o.name = v.get("name")->string();
        o.active_high = v.get("active_high")->boolean();
    }
    for (const auto v : ranges) {
        if (!fields(v, {"name", "selector", "low_hz", "high_hz"}))
            return {};
        auto& r = s.ranges[s.range_count++];
        if (v.get("name")->type() != '"' || !number(*v.get("selector"), r.selector) ||
            !number(*v.get("low_hz"), r.low_hz) || !number(*v.get("high_hz"), r.high_hz))
            return {};
        r.name = v.get("name")->string();
    }
    // Allocation against the actual saved pins is a separate mandatory check.
    // Parsing checks syntax/types only; semantic validation always takes pins.
    return s;
}
std::string serialize_filters(const FilterSettings& s) {
    using wtp::json::quote;
    if (s.output_count > s.outputs.size() || s.range_count > s.ranges.size())
        return {};
    std::string out = "{\"policy\":" + quote(s.required ? "required" : "fixed_manual") +
                      ",\"release_ms\":" + std::to_string(s.release_ms) +
                      ",\"settle_ms\":" + std::to_string(s.settle_ms) + ",\"selectors\":[";
    for (unsigned i = 0; i < s.output_count; ++i) {
        const auto& o = s.outputs[i];
        if (i)
            out += ',';
        out += "{\"id\":" + std::to_string(o.id) + ",\"name\":" + quote(o.name) +
               ",\"gp\":" + std::to_string(o.gp) +
               ",\"active_high\":" + (o.active_high ? "true}" : "false}");
    }
    out += "],\"ranges\":[";
    for (unsigned i = 0; i < s.range_count; ++i) {
        const auto& r = s.ranges[i];
        if (i)
            out += ',';
        out += "{\"name\":" + quote(r.name) + ",\"selector\":" + std::to_string(r.selector) +
               ",\"low_hz\":" + std::to_string(r.low_hz) +
               ",\"high_hz\":" + std::to_string(r.high_hz) + "}";
    }
    return out + "]}";
}
std::string filter_capabilities() {
    return R"({"schema":"transmitter-filter-selector/1","path":"/api/v1/filter-selector"})";
}
} // namespace wsprrypico::hardware
