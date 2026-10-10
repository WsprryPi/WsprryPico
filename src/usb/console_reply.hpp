#pragma once

#include "wtp/frame_buffer.hpp"

#include <algorithm>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::usb {

// INFO can exceed 8 KiB while a maximum job fragments the heap. Keep its
// complete bytes in nullable 4 KiB pages, without a doubled string allocation.
class ConsoleResponse {
  public:
    ConsoleResponse() = default;
    ConsoleResponse(std::string text) : text_(std::move(text)) {}
    ConsoleResponse(const char* text) : text_(text) {}
    ConsoleResponse(const ConsoleResponse&) = delete;
    ConsoleResponse& operator=(const ConsoleResponse&) = delete;
    ConsoleResponse(ConsoleResponse&&) noexcept = default;
    ConsoleResponse& operator=(ConsoleResponse&&) noexcept = default;
    static ConsoleResponse paged() {
        ConsoleResponse result;
        result.paged_ = true;
        return result;
    }
    // Only static literals may be borrowed. This also supplies an error reply
    // when a nullable page allocation fails, without another heap allocation.
    static ConsoleResponse constant(std::string_view text) {
        ConsoleResponse result;
        result.constant_ = text;
        return result;
    }
    bool valid() const {
        return !failed_;
    }
    std::size_t size() const {
        return paged_ ? pages_.size() : constant_.empty() ? text_.size() : constant_.size();
    }
    std::string_view at(std::size_t offset, std::size_t count) const {
        if (paged_) {
            const auto bytes = pages_.view().at(offset);
            return {reinterpret_cast<const char*>(bytes.data()), std::min(count, bytes.size())};
        }
        return (constant_.empty() ? std::string_view(text_) : constant_).substr(offset, count);
    }
    ConsoleResponse& append(std::string_view bytes) {
        if (!paged_ || failed_ || bytes.size() > 65'536 - pages_.size()) {
            failed_ = true;
            return *this;
        }
        const auto total = pages_.size() + bytes.size();
        const auto capacity = (total + wtp::FrameBuffer::page_bytes - 1) /
                              wtp::FrameBuffer::page_bytes * wtp::FrameBuffer::page_bytes;
        if (!pages_.reserve(capacity)) {
            failed_ = true;
            return *this;
        }
        pages_.append({reinterpret_cast<const std::uint8_t*>(bytes.data()), bytes.size()});
        return *this;
    }
    ConsoleResponse& append(const char* first, const char* last) {
        return append(std::string_view(first, static_cast<std::size_t>(last - first)));
    }
    ConsoleResponse& operator+=(std::string_view bytes) {
        return append(bytes);
    }
    void push_back(char byte) {
        append(std::string_view(&byte, 1));
    }

  private:
    std::string text_;
    std::string_view constant_;
    wtp::FrameBuffer pages_;
    bool paged_ = false, failed_ = false;
};

// Retain one complete response while the bounded USB queue drains. A slow
// Console must not block the RF worker or discard the end of an INFO reply.
class ConsoleReply {
  public:
    bool pending() const {
        return offset_ < response_.size();
    }
    bool begin(ConsoleResponse response) {
        if (pending() || !response.valid() || response.size() > 65'536)
            return false;
        response_ = std::move(response);
        offset_ = 0;
        return true;
    }
    template <typename Write> void poll(Write&& write) {
        if (!pending())
            return;
        const auto bytes =
            response_.at(offset_, std::min<std::size_t>(64, response_.size() - offset_));
        if (write(bytes)) {
            offset_ += bytes.size();
            if (!pending())
                reset();
        }
    }
    void reset() {
        response_ = {};
        offset_ = 0;
    }

  private:
    ConsoleResponse response_;
    std::size_t offset_ = 0;
};

} // namespace wsprrypico::usb
