#pragma once

#include <cstdint>
#include <optional>

namespace wsprrypico::time {
// One outstanding asynchronous lookup. A link transition invalidates its
// result, but does not reuse its callback storage before the resolver finishes.
class ServerLookup {
  public:
    void link(bool up) {
        if (up != up_) {
            up_ = up;
            ++epoch_;
            ready_ = false;
            next_us_ = 0;
        }
    }
    std::optional<std::uint64_t> begin(std::uint64_t now_us) {
        if (!up_ || pending_ || now_us < next_us_)
            return {};
        pending_ = epoch_;
        return pending_;
    }
    bool finish(std::uint64_t epoch, bool success, std::uint64_t now_us) {
        if (!pending_ || *pending_ != epoch)
            return false;
        pending_.reset();
        if (!up_ || epoch != epoch_)
            return false;
        next_us_ = now_us + (success ? 60'000'000 : 5'000'000);
        ready_ = ready_ || success; // A failed refresh retains the last known address.
        return success;
    }
    bool ready() const {
        return ready_;
    }
    bool pending() const {
        return pending_.has_value();
    }

  private:
    std::uint64_t epoch_ = 0, next_us_ = 0;
    std::optional<std::uint64_t> pending_;
    bool up_ = false, ready_ = false;
};
} // namespace wsprrypico::time
