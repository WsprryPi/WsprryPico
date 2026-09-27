#pragma once

#include "network/http.hpp"

#include <string>
#include <string_view>

namespace wsprrypico::network {

// Blank-AP read-only page, inert static assets and captive GET redirect. This
// never accepts secrets. The target streams static bodies from flash.
HttpResponse bootstrap_http_response(const HttpRequest& request, std::string_view device,
                                     std::string_view firmware, bool setup_enabled = false);
// Host convenience only: wire() copies static bodies. Target code uses the
// structured response and sends body_at() chunks directly.
std::string bootstrap_http_wire(const HttpRequest& request, std::string_view device,
                                std::string_view firmware);

} // namespace wsprrypico::network
