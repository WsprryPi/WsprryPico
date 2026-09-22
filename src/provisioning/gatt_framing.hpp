#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace wsprrypico::provisioning {
inline constexpr std::size_t gatt_frame_bytes = 64;
inline constexpr std::size_t gatt_frame_header_bytes = 4;
inline constexpr std::size_t gatt_frame_payload_bytes =
    gatt_frame_bytes - gatt_frame_header_bytes;
inline constexpr std::size_t gatt_frame_count = 16;

enum class FrameResult { Pending, Complete, Invalid, Oversize, OutOfOrder };

class GattFrameReceiver {
  public:
    explicit GattFrameReceiver(std::size_t maximum) : maximum_(maximum) {}
    ~GattFrameReceiver();
    FrameResult receive(std::span<const std::uint8_t> frame);
    std::span<const std::uint8_t> message() const {
        return message_;
    }
    void reset();

  private:
    std::size_t maximum_;
    std::vector<std::uint8_t> message_;
    std::uint8_t next_sequence_ = 0;
    bool active_ = false;
};

std::vector<std::vector<std::uint8_t>> gatt_frames(std::span<const std::uint8_t> message);
} // namespace wsprrypico::provisioning
