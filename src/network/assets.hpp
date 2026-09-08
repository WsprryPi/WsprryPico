#pragma once
#include <optional>
#include <string_view>
namespace wsprrypico::network {
struct WebAsset {
    std::string_view body, type;
};
std::string_view web_csp();
std::optional<WebAsset> web_asset(std::string_view path);
} // namespace wsprrypico::network
