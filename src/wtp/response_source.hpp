#pragma once

#include "wtp/output_buffer.hpp"

#include <array>
#include <memory>
#include <string>

namespace wsprrypico::wtp {
// Owned immutable response snapshot. copy() is replayable, allocation-free and
// independent of application state. The window is stable until a new offset is
// requested, including transport retries. No wire view outlives its source.
class ResponseSource {
  public:
    static constexpr std::size_t window_bytes = 1024;
    virtual ~ResponseSource() = default;
    bool prepare_output() {
        return window_.reserve(window_bytes);
    }
    void release_output() {
        window_ = InputBuffer{};
        window_size_ = 0;
    }
    virtual bool replayable() const {
        return true;
    }
    virtual std::size_t size() const = 0;
    virtual std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const = 0;
    virtual bool json_document() const {
        return false;
    }
    std::span<const std::uint8_t> at(std::size_t offset) const {
        if (offset >= size())
            return {};
        if (!window_size_ || offset < window_start_ || offset >= window_start_ + window_size_) {
            if (window_.capacity() < window_bytes)
                return {};
            window_.clear();
            window_size_ = copy(offset, {window_.data(), window_bytes});
            window_start_ = offset;
        }
        return std::span(window_.data(), window_size_).subspan(offset - window_start_);
    }

  private:
    mutable InputBuffer window_;
    mutable std::size_t window_start_ = 0, window_size_ = 0;
};
struct ResponseSourceDeleter {
    void operator()(ResponseSource* source) const {
        if (source) {
            source->~ResponseSource();
            deallocate_input(source);
        }
    }
};
using ResponseSourcePtr = std::unique_ptr<ResponseSource, ResponseSourceDeleter>;
template <typename T, typename... Args>
std::unique_ptr<T, ResponseSourceDeleter> make_response_source(Args&&... args) {
    auto* memory = allocate_input(sizeof(T));
    if (!memory)
        return {};
    auto source =
        std::unique_ptr<T, ResponseSourceDeleter>(new (memory) T(std::forward<Args>(args)...));
    if (!source->prepare_output())
        return {};
    return source;
}
inline std::size_t copy_text(std::string_view text, std::size_t offset,
                             std::span<std::uint8_t> out) {
    if (offset >= text.size())
        return 0;
    const auto count = std::min(out.size(), text.size() - offset);
    std::memcpy(out.data(), text.data() + offset, count);
    return count;
}
class TextResponseSource final : public ResponseSource {
  public:
    explicit TextResponseSource(std::string text) : text_(std::move(text)) {}
    ~TextResponseSource() override {
        volatile char* bytes = text_.data();
        for (std::size_t i = 0; i < text_.size(); ++i)
            bytes[i] = 0;
    }
    std::size_t size() const override {
        return text_.size();
    }
    std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
        return copy_text(text_, offset, out);
    }

  private:
    std::string text_;
};
// Snapshot fragments own dynamic values and borrow only static literals. No
// geometrically grown combined string is needed for nested resource documents.
class JoinedResponseSource final : public ResponseSource {
  public:
    JoinedResponseSource(std::string prefix, ResponseSourcePtr body, std::string suffix,
                         bool json = false)
        : prefix_(std::move(prefix)), body_(std::move(body)), suffix_(std::move(suffix)),
          json_(json) {
        body_->release_output();
    }
    bool replayable() const override {
        return body_->replayable();
    }
    std::size_t size() const override {
        return prefix_.size() + body_->size() + suffix_.size();
    }
    bool json_document() const override {
        return json_;
    }
    std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
        std::size_t done = 0;
        if (offset < prefix_.size()) {
            done = copy_text(prefix_, offset, out);
            offset += done;
        }
        if (done < out.size() && offset >= prefix_.size() &&
            offset - prefix_.size() < body_->size()) {
            const auto n = body_->copy(offset - prefix_.size(), out.subspan(done));
            done += n;
            offset += n;
        }
        if (done < out.size() && offset >= prefix_.size() + body_->size())
            done += copy_text(suffix_, offset - prefix_.size() - body_->size(), out.subspan(done));
        return done;
    }

  private:
    std::string prefix_;
    ResponseSourcePtr body_;
    std::string suffix_;
    bool json_;
};
class SlicedResponseSource final : public ResponseSource {
  public:
    SlicedResponseSource(ResponseSourcePtr source, std::size_t start)
        : source_(std::move(source)), start_(start) {
        source_->release_output();
    }
    bool replayable() const override {
        return source_->replayable();
    }
    std::size_t size() const override {
        return start_ <= source_->size() ? source_->size() - start_ : 0;
    }
    std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
        return source_->copy(offset + start_, out);
    }

  private:
    ResponseSourcePtr source_;
    std::size_t start_;
};
// Escape one byte identically for the USB body string and its length counter.
inline std::string_view response_escape(std::uint8_t c, std::array<char, 6>& scratch) {
    if (c == '"')
        return "\\\"";
    if (c == '\\')
        return "\\\\";
    if (c < 32) {
        constexpr char hex[] = "0123456789abcdef";
        scratch = {'\\', 'u', '0', '0', hex[c >> 4], hex[c & 15]};
        return {scratch.data(), scratch.size()};
    }
    scratch[0] = static_cast<char>(c);
    return {scratch.data(), 1};
}
class EscapedResponseSource final : public ResponseSource {
  public:
    explicit EscapedResponseSource(ResponseSourcePtr body, bool incremental = false)
        : body_(std::move(body)) {
        if (!body_->replayable()) {
            valid_ = false;
            return;
        }
        body_->release_output();
        if (!incremental)
            while (valid_ && !ready())
                count_step();
    }
    // One foreground step counts at most one raw window. No bytes may be
    // published until ready(), so USB framing always contains an exact length.
    bool count_step() {
        if (!valid_ || ready())
            return valid_;
        if (checkpoint_count_ == checkpoints_.size()) {
            valid_ = false;
            return false;
        }
        std::array<std::uint8_t, window_bytes> bytes{};
        std::array<char, 6> scratch{};
        checkpoints_[checkpoint_count_++] = {counted_, size_};
        const auto n = body_->copy(counted_, bytes);
        if (!n) {
            valid_ = false;
            return false;
        }
        for (auto c : std::span(bytes).first(n))
            size_ += response_escape(c, scratch).size();
        counted_ += n;
        return true;
    }
    bool ready() const {
        return counted_ == body_->size();
    }
    bool valid() const {
        return valid_;
    }
    std::size_t size() const override {
        return size_;
    }
    std::size_t copy(std::size_t offset, std::span<std::uint8_t> out) const override {
        if (!ready() || offset >= size_)
            return 0;
        auto point = checkpoints_.front();
        for (const auto& p : std::span(checkpoints_).first(checkpoint_count_)) {
            if (p.second > offset)
                break;
            point = p;
        }
        std::array<std::uint8_t, window_bytes> bytes{};
        std::array<char, 6> scratch{};
        std::size_t done = 0, escaped = point.second;
        for (auto input = point.first; input < body_->size() && done < out.size();) {
            const auto n = body_->copy(input, bytes);
            if (!n)
                return done;
            for (auto c : std::span(bytes).first(n)) {
                for (auto b : response_escape(c, scratch)) {
                    if (escaped++ >= offset && done < out.size())
                        out[done++] = b;
                }
                if (done == out.size())
                    break;
            }
            input += n;
        }
        return done;
    }

  private:
    ResponseSourcePtr body_;
    std::array<std::pair<std::size_t, std::size_t>, 64> checkpoints_{};
    std::size_t checkpoint_count_ = 0, counted_ = 0;
    std::size_t size_ = 0;
    bool valid_ = true;
};
} // namespace wsprrypico::wtp
