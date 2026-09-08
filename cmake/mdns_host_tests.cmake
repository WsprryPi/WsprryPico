set(WSPRRY_PICO_TEST_LWIP_PATH "" CACHE PATH "Optional pinned lwIP for isolated mDNS packet tests")
if(NOT WSPRRY_PICO_TEST_LWIP_PATH AND WSPRRY_PICO_TEST_MBEDTLS_PATH)
    get_filename_component(sdk_lib "${WSPRRY_PICO_TEST_MBEDTLS_PATH}" DIRECTORY)
    if(EXISTS "${sdk_lib}/lwip/src/apps/mdns/mdns.c")
        set(WSPRRY_PICO_TEST_LWIP_PATH "${sdk_lib}/lwip")
    endif()
endif()
if(WSPRRY_PICO_TEST_LWIP_PATH)
    execute_process(COMMAND git -C "${WSPRRY_PICO_TEST_LWIP_PATH}" rev-parse HEAD
        OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(NOT revision STREQUAL "77dcd25a72509eb83f72b033d219b1d40cd8eb95")
        message(FATAL_ERROR "mDNS tests require the SDK-pinned lwIP revision")
    endif()
    execute_process(COMMAND git -C "${WSPRRY_PICO_TEST_LWIP_PATH}" status --porcelain
        OUTPUT_VARIABLE changes OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(changes)
        message(FATAL_ERROR "mDNS tests require clean pinned lwIP")
    endif()
    enable_language(C)
    set(lwip_src "${WSPRRY_PICO_TEST_LWIP_PATH}/src")
    file(GLOB lwip_core CONFIGURE_DEPENDS "${lwip_src}/core/*.c" "${lwip_src}/core/ipv4/*.c")
    add_executable(mdns_lwip_tests tests/mdns_lwip/tests.c
        src/standalone/pico/mdns_lwip.c ${lwip_core}
        ${lwip_src}/netif/ethernet.c
        ${lwip_src}/apps/mdns/mdns_domain.c ${lwip_src}/apps/mdns/mdns_out.c)
    target_include_directories(mdns_lwip_tests PRIVATE tests/mdns_lwip src ${lwip_src}/include)
    target_compile_definitions(mdns_lwip_tests PRIVATE
        WSPRRY_PICO_LWIP_MDNS_SOURCE="${lwip_src}/apps/mdns/mdns.c")
    set_target_properties(mdns_lwip_tests PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)
    target_compile_options(mdns_lwip_tests PRIVATE -Wall -Wextra -Werror -UNDEBUG)
    add_test(NAME mdns_lwip_tests COMMAND mdns_lwip_tests)
endif()
