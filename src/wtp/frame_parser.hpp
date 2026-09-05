#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace wsprrypico::wtp {

constexpr std::size_t kFrameHeaderBytes = 16;
constexpr std::size_t kMaximumPayloadBytes = 65'536;

std::uint32_t crc32c(std::span<const std::uint8_t> bytes);
std::vector<std::uint8_t> encode_frame(std::span<const std::uint8_t> payload);

enum class FrameEventKind { Payload, InvalidFrame, Closed };

struct FrameEvent {
    FrameEventKind kind;
    std::vector<std::uint8_t> payload;
};

class FrameParser {
  public:
    std::vector<FrameEvent> feed(std::span<const std::uint8_t> bytes, std::uint64_t now_ms);
    std::vector<FrameEvent> check_timeout(std::uint64_t now_ms);
    void end_of_stream();

    [[nodiscard]] bool closed() const {
        return closed_;
    }
    [[nodiscard]] std::size_t buffered_bytes() const {
        return buffer_.size();
    }

  private:
    void process(std::vector<FrameEvent>& events);
    void discard_prefix(std::size_t count, std::vector<FrameEvent>& events);
    void invalid_frame(std::vector<FrameEvent>& events);
    void close(std::vector<FrameEvent>& events);

    std::vector<std::uint8_t> buffer_;
    std::size_t consecutive_invalid_frames_ = 0;
    std::size_t resync_discard_bytes_ = 0;
    std::uint64_t last_progress_ms_ = 0;
    bool partial_ = false;
    bool closed_ = false;
};

} // namespace wsprrypico::wtp
