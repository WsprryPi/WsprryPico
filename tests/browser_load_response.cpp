// SPDX-License-Identifier: MIT
#include "browser_load_response.hpp"
namespace wsprrypico::network {
HttpResponse browser_load_response(const wtp::Request& request, const wtp::Response& response) {
    HttpResponse result{200, {}, "application/json", {}};
    // The fixed index/window costs more than ordinary short replies. Retain
    // the prior allocation/sealing/framing path for up to 32 adjustments.
    if (response.adjustments.size() <= 32) {
        result.buffered_body = wtp::encode_load_response_buffer(request, response, true);
        if (result.buffered_body.empty())
            return http_error(503, "resource_exhausted");
    } else {
        result.generated_body = wtp::load_response_source(request, response);
        if (!result.generated_body)
            return http_error(503, "resource_exhausted");
    }
    return result;
}
}
