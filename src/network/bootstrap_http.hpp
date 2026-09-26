#pragma once

#include "network/http.hpp"

#include <string>
#include <string_view>

namespace wsprrypico::network {

// Blank-AP read-only page and captive GET redirect. This never accepts secrets.
std::string bootstrap_http_wire(const HttpRequest& request, std::string_view device,
                                std::string_view firmware);

} // namespace wsprrypico::network
