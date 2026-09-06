#pragma once
#include "standalone/config.hpp"

#include <span>

namespace wsprrypico::standalone {
// Four 4 KiB sectors: two configuration banks, two append-only watermark banks.
class Flash {
  public:
    virtual ~Flash() = default;
    virtual bool read(std::size_t offset, std::span<std::uint8_t> data) = 0;
    virtual bool erase(std::size_t sector_offset) = 0;
    virtual bool program(std::size_t offset, std::span<const std::uint8_t> page) = 0;
};
class Journal {
  public:
    Journal(Flash& flash, std::size_t base, std::size_t record_size)
        : flash_(flash), base_(base), size_(record_size) {}
    bool load();
    bool append(std::string_view data);
    const std::string& data() const {
        return data_;
    }
    bool healthy() const {
        return healthy_;
    }

  private:
    Flash& flash_;
    std::size_t base_, size_;
    bool healthy_ = false;
    std::uint64_t sequence_ = 0;
    std::size_t latest_ = 0;
    std::string data_;
};
class Store {
  public:
    explicit Store(Flash& flash) : config_(flash, 0, 2048), cursor_(flash, 8192, 256) {}
    bool load();
    bool save(const Config& config);
    bool reserve(std::uint64_t utc_ns);
    const std::optional<Config>& config() const {
        return current_;
    }
    std::uint64_t watermark() const {
        return watermark_;
    }
    bool healthy() const {
        return healthy_;
    }

  private:
    Journal config_, cursor_;
    std::optional<Config> current_;
    std::uint64_t watermark_ = 0;
    bool healthy_ = false;
};
} // namespace wsprrypico::standalone
