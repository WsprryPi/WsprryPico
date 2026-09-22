#include "provisioning/gatt_framing.hpp"

#include <algorithm>

namespace wsprrypico::provisioning {
namespace {
void secure_clear(std::vector<std::uint8_t>& bytes) {
    volatile std::uint8_t* data = bytes.empty() ? nullptr : bytes.data();
    for (std::size_t i = 0; i < bytes.size(); ++i)
        data[i] = 0;
    std::vector<std::uint8_t>{}.swap(bytes);
}
} // namespace

GattFrameReceiver::~GattFrameReceiver() {
    reset();
}

void GattFrameReceiver::reset() {
    secure_clear(message_);
    next_sequence_ = 0;
    active_ = false;
}

FrameResult GattFrameReceiver::receive(std::span<const std::uint8_t> frame) {
    if (frame.size() < gatt_frame_header_bytes || frame.size() > gatt_frame_bytes ||
        frame[0] != 1 || (frame[1] & ~std::uint8_t{3}) ||
        frame[3] != frame.size() - gatt_frame_header_bytes) {
        reset();
        return FrameResult::Invalid;
    }
    const bool first = frame[1] & 1;
    const bool last = frame[1] & 2;
    const auto sequence = frame[2];
    if ((first && (active_ || sequence != 0)) || (!first && !active_) ||
        sequence != next_sequence_ || sequence >= gatt_frame_count) {
        reset();
        return FrameResult::OutOfOrder;
    }
    if (first) {
        message_.clear();
        active_ = true;
    }
    const auto payload = frame.subspan(gatt_frame_header_bytes);
    if (payload.empty() || payload.size() > maximum_ - std::min(maximum_, message_.size())) {
        reset();
        return FrameResult::Oversize;
    }
    message_.insert(message_.end(), payload.begin(), payload.end());
    ++next_sequence_;
    if (!last)
        return FrameResult::Pending;
    active_ = false;
    next_sequence_ = 0;
    return FrameResult::Complete;
}

std::vector<std::vector<std::uint8_t>> gatt_frames(std::span<const std::uint8_t> message) {
    std::vector<std::vector<std::uint8_t>> result;
    if (message.empty() ||
        message.size() > gatt_frame_payload_bytes * gatt_frame_count)
        return result;
    for (std::size_t offset = 0, sequence = 0; offset < message.size(); ++sequence) {
        const auto count = std::min(gatt_frame_payload_bytes, message.size() - offset);
        std::vector<std::uint8_t> frame(gatt_frame_header_bytes + count);
        frame[0] = 1;
        frame[1] = static_cast<std::uint8_t>((offset == 0 ? 1 : 0) |
                                             (offset + count == message.size() ? 2 : 0));
        frame[2] = static_cast<std::uint8_t>(sequence);
        frame[3] = static_cast<std::uint8_t>(count);
        std::copy_n(message.begin() + offset, count, frame.begin() + gatt_frame_header_bytes);
        result.push_back(std::move(frame));
        offset += count;
    }
    return result;
}
} // namespace wsprrypico::provisioning
