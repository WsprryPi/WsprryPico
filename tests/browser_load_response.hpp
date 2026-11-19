// SPDX-License-Identifier: MIT
#pragma once
#include "network/http.hpp"
#include "wtp/codec.hpp"
namespace wsprrypico::network {
// Offline fixture for retained paging/stream/crypto resource-limit checks.
HttpResponse browser_load_response(const wtp::Request&, const wtp::Response&);
}
