#pragma once
#include "wtp/frame_buffer.hpp"

namespace wsprrypico::wtp {
// Precondition: the complete, immutable original payload passed json::parse.
// Never apply this to an unvalidated token stream: e.g. `1 2` must not become
// `12`. The caller retains the original-byte digest for replay identity.
inline void compact_validated_json(FrameBuffer& bytes, void (*poll)(void*) = nullptr,
                                   void* context = nullptr) {
    std::size_t read = 0, write = 0, next_poll = 4096;
    bool quoted = false;
    const auto hex = [](std::uint8_t c) -> unsigned {
        if (c >= '0' && c <= '9')
            return c - '0';
        if (c >= 'a' && c <= 'f')
            return c - 'a' + 10;
        if (c >= 'A' && c <= 'F')
            return c - 'A' + 10;
        return 256;
    };
    const auto append = [&](std::uint8_t c) { bytes.mutable_at(write++)[0] = c; };
    while (read < bytes.size()) {
        if (poll && read >= next_poll) {
            poll(context);
            next_poll = read + 4096;
        }
        const auto c = bytes[read];
        if (quoted && c == '\\') {
            const auto next = bytes[read + 1];
            if (next == '/') {
                append('/');
                read += 2;
                continue;
            }
            if (next == 'u' && read + 6 <= bytes.size() && bytes[read + 2] == '0' &&
                bytes[read + 3] == '0') {
                const auto high = hex(bytes[read + 4]), low = hex(bytes[read + 5]);
                const auto plain = high * 16 + low;
                if (high < 16 && low < 16 && plain >= 32 && plain < 127 && plain != '"' &&
                    plain != '\\') {
                    append(static_cast<std::uint8_t>(plain));
                    read += 6;
                    continue;
                }
            }
            // Preserve every other escape byte-for-byte, including quotes,
            // backslashes, controls, non-ASCII and surrogate-pair sequences.
            append(c);
            append(next);
            read += 2;
            continue;
        }
        if (!quoted && (c == ' ' || c == '\t' || c == '\r' || c == '\n')) {
            ++read;
            continue;
        }
        if (c == '"')
            quoted = !quoted;
        append(c);
        ++read;
    }
    (void)bytes.truncate_release(write);
    if (poll)
        poll(context);
}
} // namespace wsprrypico::wtp
