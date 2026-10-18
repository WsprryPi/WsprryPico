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
    std::optional<std::uint64_t> begin(std::uint64_t now_us, bool peer_fresh = false) {
        if (!up_ || pending_ || now_us < next_us_ || (ready_ && peer_fresh))
            return {};
        pending_ = epoch_;
        return pending_;
    }
    // A packet admitted while DNS was pending can make the current peer healthy
    // again. Complete that lookup without replacing the responding association.
    bool finish(std::uint64_t epoch, bool success, std::uint64_t now_us, bool peer_fresh = false) {
        if (!pending_ || *pending_ != epoch)
            return false;
        pending_.reset();
        if (!up_ || epoch != epoch_)
            return false;
        const bool replace = success && !(ready_ && peer_fresh);
        next_us_ = now_us + (success ? 60'000'000 : 5'000'000);
        ready_ = ready_ || success; // A failed refresh retains the last known address.
        return replace;
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
