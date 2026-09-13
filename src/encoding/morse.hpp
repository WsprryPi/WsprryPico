#pragma once

#include "wtp/job_service.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <string_view>

namespace wsprrypico::encoding {
inline constexpr std::size_t max_message_characters = 32;
inline constexpr std::uint64_t max_message_duration_ns = 3'600'000'000'000;
inline constexpr std::uint64_t message_tail_ns = 1000;
// Existing WsprryPi alphabet and gap semantics; no prosigns or new punctuation.
inline constexpr std::string_view morse_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/?.,-+=";
inline constexpr std::array<std::string_view, 43> morse_codes{
    ".-",    "-...",   "-.-.",   "-..",    ".",      "..-.",  "--.",   "....",  "..",
    ".---",  "-.-",    ".-..",   "--",     "-.",     "---",   ".--.",  "--.-",  ".-.",
    "...",   "-",      "..-",    "...-",   ".--",    "-..-",  "-.--",  "--..",  "-----",
    ".----", "..---",  "...--",  "....-",  ".....",  "-....", "--...", "---..", "----.",
    "-..-.", "..--..", ".-.-.-", "--..--", "-....-", ".-.-.", "-...-"};
inline constexpr bool message_space(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}
inline constexpr std::string_view morse_code(char c) {
    if (c >= 'a' && c <= 'z')
        c -= 'a' - 'A';
    const auto index = morse_alphabet.find(c);
    return index == std::string_view::npos ? std::string_view{} : morse_codes[index];
}
inline constexpr std::size_t maximum_morse_elements = [] {
    std::size_t n = 0;
    for (auto code : morse_codes)
        n = std::max(n, code.size());
    return n;
}();
inline constexpr std::size_t worst_single_message_events =
    max_message_characters * maximum_morse_elements * 2; // Includes final off.
static_assert(worst_single_message_events == 384 && worst_single_message_events <= 512);

struct MorseMessage {
    std::string job_id, mode, text;
    std::uint64_t mark_frequency_nhz = 0, space_frequency_nhz = 0;
    std::uint64_t dot_ns = 0, dash_ns = 0, intra_gap_ns = 0, character_gap_ns = 0, word_gap_ns = 0;
    std::uint32_t repeat_count = 1;
    std::uint64_t repeat_gap_ns = 0;
    bool allow_frequency_adjustment = false;
};
struct MorseResult {
    std::optional<wtp::Job> job;
    std::string_view error;
    std::uint64_t calculated_duration_ns = 0;
    std::size_t calculated_events = 0;
};

inline MorseResult compile_message(const MorseMessage& input, std::size_t event_limit = 512,
                                   std::uint64_t duration_limit = max_message_duration_ns) {
    MorseResult result;
    auto fail = [&](std::string_view reason) {
        result.error = reason;
        return result;
    };
    if (input.text.empty() || input.text.size() > max_message_characters)
        return fail("message_length_limit_32");
    if (input.mode != "qrss" && input.mode != "fskcw" && input.mode != "dfcw")
        return fail("unsupported_message_mode");
    if (!input.mark_frequency_nhz ||
        (input.mode != "qrss" &&
         (!input.space_frequency_nhz || input.mark_frequency_nhz == input.space_frequency_nhz ||
          (input.mode == "fskcw" && input.mark_frequency_nhz < input.space_frequency_nhz))))
        return fail("invalid_message_frequency");
    if (!input.dot_ns || !input.dash_ns || !input.intra_gap_ns || !input.character_gap_ns ||
        !input.word_gap_ns || !input.repeat_count || input.repeat_count > 512 ||
        (input.repeat_count > 1 && !input.repeat_gap_ns))
        return fail("invalid_message_timing_or_repetition");
    for (char c : input.text)
        if (!message_space(c) && morse_code(c).empty())
            return fail("unsupported_message_character");
    const auto maximum = std::numeric_limits<std::uint64_t>::max();
    bool overflow = false;
    std::uint64_t pattern_duration = 0;
    std::size_t pattern_events = 0;
    auto visit = [&](auto emit) {
        for (std::size_t i = 0; i < input.text.size(); ++i) {
            if (message_space(input.text[i]))
                continue;
            const auto code = morse_code(input.text[i]);
            for (std::size_t n = 0; n < code.size(); ++n) {
                emit(input.mode == "dfcw" || code[n] == '.' ? input.dot_ns : input.dash_ns, true,
                     input.mode == "dfcw" && code[n] == '-' ? input.space_frequency_nhz
                                                            : input.mark_frequency_nhz);
                if (n + 1 < code.size())
                    emit(input.intra_gap_ns, input.mode == "fskcw", input.space_frequency_nhz);
            }
            auto next = i + 1;
            while (next < input.text.size() && message_space(input.text[next]))
                ++next;
            if (next < input.text.size())
                emit(next == i + 1 ? input.character_gap_ns : input.word_gap_ns,
                     input.mode == "fskcw", input.space_frequency_nhz);
        }
    };
    visit([&](std::uint64_t duration, bool, std::uint64_t) {
        if (duration > maximum - pattern_duration)
            overflow = true;
        else
            pattern_duration += duration;
        ++pattern_events;
    });
    if (!pattern_events)
        return fail("message_has_no_marks");
    if (overflow || pattern_duration > maximum / input.repeat_count ||
        (input.repeat_count > 1 && input.repeat_gap_ns > maximum / (input.repeat_count - 1)))
        return fail("message_duration_overflow");
    const auto repeated = pattern_duration * input.repeat_count;
    const auto gaps = input.repeat_gap_ns * (input.repeat_count - 1);
    if (gaps > maximum - repeated || message_tail_ns > maximum - repeated - gaps)
        return fail("message_duration_overflow");
    result.calculated_duration_ns = repeated + gaps + message_tail_ns;
    result.calculated_events = pattern_events * input.repeat_count + input.repeat_count;
    if (result.calculated_duration_ns > std::min(duration_limit, max_message_duration_ns))
        return fail("message_duration_limit_exceeded");
    if (result.calculated_events > std::min<std::size_t>(event_limit, 512))
        return fail("message_event_limit_exceeded");
    wtp::Job job;
    job.job_id = input.job_id;
    job.mode = input.mode;
    job.allow_frequency_adjustment = input.allow_frequency_adjustment;
    job.total_duration_ns = result.calculated_duration_ns;
    job.events.reserve(result.calculated_events);
    std::uint64_t offset = 0;
    auto emit = [&](std::uint64_t duration, bool on, std::uint64_t frequency) {
        job.events.push_back({offset, duration, on, on ? std::optional(frequency) : std::nullopt});
        offset += duration;
    };
    for (std::uint32_t repeat = 0; repeat < input.repeat_count; ++repeat) {
        visit(emit);
        if (repeat + 1 < input.repeat_count)
            emit(input.repeat_gap_ns, false, 0);
    }
    emit(message_tail_ns, false, 0);
    result.job = std::move(job);
    return result;
}
} // namespace wsprrypico::encoding
