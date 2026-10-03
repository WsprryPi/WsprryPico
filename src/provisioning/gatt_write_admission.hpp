#pragma once

#include <cstddef>
#include <cstdint>
#include <span>

namespace wsprrypico::provisioning {
// One original ATT WriteRequest remains owned by BTstack. No input bytes are
// accepted while Endpoint output is backpressured, and progress cannot renew
// this absolute admission deadline.
class GattWriteAdmission {
  public:
    enum class Result { Ready, Deferred, Rejected };
    static constexpr std::uint64_t deadline_ms = 5000;

    static bool acknowledged_request(std::span<const std::uint8_t> request,
                                     const std::uint8_t* value, std::size_t size,
                                     std::uint16_t handle) {
        return size > 0 && size <= 64 && request.size() == size + 3 && request[0] == 0x12 &&
               value == request.data() + 3 &&
               (request[1] | (std::uint16_t(request[2]) << 8)) == handle;
    }
    Result admit(std::uint64_t now, bool ready, bool valid, bool acknowledged) {
        // Write Commands have no retained request/response. They may not steal
        // or reset an existing acknowledged transaction.
        if (!acknowledged)
            return valid && ready && !pending_ ? Result::Ready : Result::Rejected;
        scheduled_ = false;
        if (!valid || (pending_ && expired(now))) {
            reset();
            return Result::Rejected;
        }
        if (ready) {
            reset();
            return Result::Ready;
        }
        if (!pending_) {
            pending_ = true;
            began_ms_ = now;
        }
        return Result::Deferred;
    }
    bool resume_due(std::uint64_t now, bool ready, bool valid) {
        if (!pending_ || scheduled_ || (!ready && valid && !expired(now)))
            return false;
        // Set before the SDK call: its callback may execute synchronously and
        // re-defer the same original request without renewing began_ms_.
        scheduled_ = true;
        return true;
    }
    bool pending() const {
        return pending_;
    }
    void reset() {
        pending_ = scheduled_ = false;
        began_ms_ = 0;
    }

  private:
    bool expired(std::uint64_t now) const {
        return now < began_ms_ || now - began_ms_ >= deadline_ms;
    }
    std::uint64_t began_ms_ = 0;
    bool pending_ = false;
    bool scheduled_ = false;
};
} // namespace wsprrypico::provisioning
