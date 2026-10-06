#pragma once

#include <algorithm>
#include <string>
#include <string_view>
#include <utility>

namespace wsprrypico::usb {

// Retain one complete response while the bounded USB queue drains. A slow
// Console must not block the RF worker or discard the end of an INFO reply.
class ConsoleReply {
  public:
    bool pending() const {
        return offset_ < response_.size();
    }
    bool begin(std::string response) {
        if (pending() || response.size() > 65'536)
            return false;
        response_ = std::move(response);
        offset_ = 0;
        return true;
    }
    template <typename Write> void poll(Write&& write) {
        if (!pending())
            return;
        const auto bytes = std::string_view(response_).substr(
            offset_, std::min<std::size_t>(64, response_.size() - offset_));
        if (write(bytes)) {
            offset_ += bytes.size();
            if (!pending())
                reset();
        }
    }
    void reset() {
        std::string{}.swap(response_);
        offset_ = 0;
    }

  private:
    std::string response_;
    std::size_t offset_ = 0;
};

} // namespace wsprrypico::usb
