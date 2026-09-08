#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>

// Separate translation unit keeps identically named client/server headers isolated.
class HostTestEndpoint {
  public:
    virtual ~HostTestEndpoint() = default;
    virtual void connect() = 0;
    virtual void disconnect() = 0;
    virtual void advance(std::uint64_t ns) = 0;
    virtual void synchronize() = 0;
    virtual void invalidate_clock() = 0;
    virtual void reset() = 0;
    virtual std::uint64_t now_ns() const = 0;
    virtual std::uint64_t utc_ns() const = 0;
    virtual bool inactive() const = 0;
    virtual bool closed() const = 0;
    virtual std::size_t receive(std::span<const std::uint8_t>) = 0;
    virtual std::size_t read(std::span<std::uint8_t>) = 0;
};
std::unique_ptr<HostTestEndpoint> host_test_endpoint();
