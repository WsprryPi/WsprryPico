#pragma once

#include "provisioning/field_runtime.hpp"
#include "provisioning/local_access.hpp"

#include <string>

namespace wsprrypico::provisioning {
class PicoRandomSource final : public RandomSource {
  public:
    bool fill(std::span<std::uint8_t> bytes) override;
};

class PicoBondStore final : public BondStore {
  public:
    static std::uint64_t identity(int index);
    bool erase(std::uint64_t peer) override;
    bool erase_all() override;
};

class PicoIndicatorOutput final : public IndicatorOutput {
  public:
    bool write(bool on) override;
};

class PicoSoftAp {
  public:
    bool start(const LocalIdentity& identity, std::string_view password);
    void stop();
    bool ready() const;
    bool running() const { return running_; }

  private:
    bool running_ = false;
};
} // namespace wsprrypico::provisioning
