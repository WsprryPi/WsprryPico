#pragma once
#include <optional>
#include <string_view>
namespace wsprrypico::network {
struct WebAsset {
    std::string_view body, type;
};
std::string_view web_csp();
std::optional<WebAsset> web_asset(std::string_view path);
std::string_view bootstrap_csp();
// The credential document is served only when the target admission gate is active.
std::optional<WebAsset> bootstrap_asset(std::string_view path);
} // namespace wsprrypico::network
