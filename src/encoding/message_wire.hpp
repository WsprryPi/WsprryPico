#pragma once
#include "encoding/morse.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::encoding {
inline std::optional<MorseMessage> decode_message(wtp::json::Value body, bool with_id = true) {
    using namespace wtp;
    if (!json::fields(body,
                      {"mode", "message", "frequency_nhz", "space_frequency_nhz", "timing",
                       "repeat_count", "repeat_gap_ns", "allow_frequency_adjustment"},
                      {"job_id"}))
        return {};
    MorseMessage value;
    const auto id = body.get("job_id");
    const auto mode = *body.get("mode"), message = *body.get("message");
    if (with_id ? (!id || !json::identifier(*id)) : id.has_value())
        return {};
    if (mode.type() != '"' || message.type() != '"')
        return {};
    value.job_id = with_id ? id->string() : std::string(32, '0');
    value.mode = mode.string();
    value.text = message.string();
    if (!json::decimal(*body.get("frequency_nhz"), value.mark_frequency_nhz, true) ||
        !json::decimal(*body.get("space_frequency_nhz"), value.space_frequency_nhz) ||
        !json::decimal(*body.get("repeat_gap_ns"), value.repeat_gap_ns))
        return {};
    const auto timing = *body.get("timing");
    if (!json::fields(timing,
                      {"dot_ns", "dash_ns", "intra_gap_ns", "character_gap_ns", "word_gap_ns"}) ||
        !json::decimal(*timing.get("dot_ns"), value.dot_ns, true) ||
        !json::decimal(*timing.get("dash_ns"), value.dash_ns, true) ||
        !json::decimal(*timing.get("intra_gap_ns"), value.intra_gap_ns, true) ||
        !json::decimal(*timing.get("character_gap_ns"), value.character_gap_ns, true) ||
        !json::decimal(*timing.get("word_gap_ns"), value.word_gap_ns, true))
        return {};
    const auto repeat = *body.get("repeat_count");
    if (repeat.raw.empty() || repeat.raw.size() > 3 ||
        !std::all_of(repeat.raw.begin(), repeat.raw.end(),
                     [](char c) { return c >= '0' && c <= '9'; }) ||
        repeat.integer() < 1 || repeat.integer() > 512)
        return {};
    value.repeat_count = static_cast<std::uint32_t>(repeat.integer());
    const auto allow = *body.get("allow_frequency_adjustment");
    if (allow.raw != "true" && allow.raw != "false")
        return {};
    value.allow_frequency_adjustment = allow.boolean();
    return value;
}
inline std::string serialize_message(const MorseMessage& m) {
    using wtp::json::quote;
    const auto n = [](std::uint64_t value) { return wtp::json::quote(std::to_string(value)); };
    return "{\"mode\":" + quote(m.mode) + ",\"message\":" + quote(m.text) +
           ",\"frequency_nhz\":" + n(m.mark_frequency_nhz) +
           ",\"space_frequency_nhz\":" + n(m.space_frequency_nhz) +
           ",\"timing\":{\"dot_ns\":" + n(m.dot_ns) + ",\"dash_ns\":" + n(m.dash_ns) +
           ",\"intra_gap_ns\":" + n(m.intra_gap_ns) +
           ",\"character_gap_ns\":" + n(m.character_gap_ns) +
           ",\"word_gap_ns\":" + n(m.word_gap_ns) +
           "},\"repeat_count\":" + std::to_string(m.repeat_count) +
           ",\"repeat_gap_ns\":" + n(m.repeat_gap_ns) +
           ",\"allow_frequency_adjustment\":" + (m.allow_frequency_adjustment ? "true" : "false") +
           "}";
}
} // namespace wsprrypico::encoding
