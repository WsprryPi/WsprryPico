#pragma once
#include "wtp/frame_parser.hpp"
#include "wtp/job_service.hpp"

#include <variant>

namespace wsprrypico::wtp {
// Single-owner, inhibited-engine WTP endpoint. Transport is a byte stream and
// does not own job lifecycle. No device USB calls occur in this class.
class Endpoint {
  public:
    Endpoint(JobService& service, std::string device_id, std::string firmware_version);
    void connect(std::string principal);
    void disconnect();
    void poll(std::uint64_t now_ms);
    // At most 64 bytes per call; caller retains all unconsumed input.
    std::size_t receive(std::span<const std::uint8_t> input, std::uint64_t now_ms);
    std::span<const std::uint8_t> output() const;
    void consume_output(std::size_t count, std::uint64_t now_ms);
    bool closed() const {
        return closed_;
    }
    bool can_receive() const {
        return !closed_ && !closing_ && output_.empty();
    }

  private:
    void payload(InputBuffer bytes, std::uint64_t now_ms);
    void frame_events(std::vector<FrameEvent> events, std::uint64_t now_ms);
    bool enqueue(std::string payload, std::uint64_t now_ms, bool advisory);
    bool enqueue(InputBuffer payload, std::uint64_t now_ms);
    void event(std::string_view name, std::string body, std::uint64_t now_ms);
    void observe(std::uint64_t now_ms, bool released = false);
    void close_after_output();
    JobService& service_;
    std::string device_id_, firmware_version_, principal_, session_, boot_;
    FrameParser parser_;
    struct OutputFrame {
        std::array<std::uint8_t, kFrameHeaderBytes> header;
        std::variant<std::string, InputBuffer> payload;
        std::span<const std::uint8_t> bytes() const {
            return std::visit(
                [](const auto& value) {
                    return std::span(reinterpret_cast<const std::uint8_t*>(value.data()),
                                     value.size());
                },
                payload);
        }
        std::size_t size() const {
            return header.size() + bytes().size();
        }
    };
    std::deque<OutputFrame> output_;
    std::size_t offset_ = 0, queued_bytes_ = 0;
    std::uint64_t last_tx_progress_ms_ = 0, event_id_ = 0;
    bool closed_ = true, closing_ = false;
    ServiceStatus observed_;
};
} // namespace wsprrypico::wtp
