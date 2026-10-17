#pragma once

#include "network/http.hpp"
#include "wtp/frame_buffer.hpp"
#include "wtp/json.hpp"

#include <array>
#include <functional>

namespace wsprrypico::usb {
// Local physical authority only. This adapter never authenticates network input.
class ManagementEndpoint {
  public:
    static constexpr std::size_t maximum_request = 32768, maximum_response = 65536;
    static constexpr std::uint64_t transaction_timeout_ms = 10'000;
    // Keep the unchanged WTP control reserve and bounded workspace. WTP input
    // admission can reclaim this optional session's pages before retrying its
    // original, larger budget; idle RF images need not reserve two whole jobs.
    static constexpr std::size_t memory_reserve = 32768 + 8192 + 1024;
    using Handler =
        std::function<network::HttpResponse(const network::HttpRequest&, std::uint64_t)>;
    using Finish = std::function<void(std::uint64_t, bool)>;
    ManagementEndpoint(std::string device, std::string boot, std::string firmware, Handler handler,
                       Finish finish)
        : device_(std::move(device)), boot_(std::move(boot)), firmware_(std::move(firmware)),
          handler_(std::move(handler)), finish_(std::move(finish)) {}
    void connect(std::string session);
    void disconnect();
    void poll(std::uint64_t now_ms);
    std::size_t receive(std::span<const std::uint8_t>, std::uint64_t now_ms);
    std::span<const std::uint8_t> output() const;
    void consume_output(std::size_t bytes);
    bool closed() const {
        return closed_;
    }
    bool busy() const {
        return header_size_ || expected_ || pending_ || !output_.empty();
    }

  private:
    bool dispatch();
    bool respond(unsigned status, network::HttpResponse response, bool delivery);
    bool binding(wtp::json::Value value) const;
    void clear_input();
    std::string target() const;
    std::string device_, boot_, firmware_, session_;
    Handler handler_;
    Finish finish_;
    std::array<std::uint8_t, 8> header_{};
    std::size_t header_size_ = 0, expected_ = 0, output_offset_ = 0;
    wtp::FrameBuffer input_;
    wtp::OutputBuffer output_;
    std::array<std::uint8_t, 8> output_header_{};
    std::uint64_t started_ms_ = 0, generation_ = 0, transaction_ = 0;
    std::int32_t last_id_ = 0;
    bool closed_ = true, negotiated_ = false, pending_ = false, timing_ = false;
};
} // namespace wsprrypico::usb
