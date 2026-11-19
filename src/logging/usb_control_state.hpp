// SPDX-License-Identifier: MIT
#pragma once
#include "logging/logger.hpp"

namespace wsprrypico::logging {
// DTR describes individual control ports, not physical cable health or a
// negotiated protocol session. Ordinary host opens deliberately toggle it.
// Observe only; parser resets and transport servicing retain their own authority.
class UsbControlStateLogger {
  public:
    void observe(Logger& logger, bool management, std::uint64_t monotonic_ns,
                 std::uint64_t utc_ns = 0) {
        if (management != management_) {
            logger.event(7, "USB_STATE",
                         management ? "USB Management port opened" : "USB Management port closed",
                         monotonic_ns, utc_ns);
            management_ = management;
        }
    }

  private:
    bool management_ = false;
};
} // namespace wsprrypico::logging
