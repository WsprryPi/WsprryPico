#pragma once

#include "time/utc_discipline.hpp"

#include <string>

namespace wsprrypico::time {

class UsbTimeSource {
  public:
    explicit UsbTimeSource(UtcDiscipline& clock) : clock_(clock) {}
    std::string command(std::string_view line);
    void reset();

  private:
    UtcDiscipline& clock_;
    std::optional<std::uint64_t> sample_;
};

} // namespace wsprrypico::time
