# Optional test dependency only. Never fetched, installed or linked into firmware.
set(WSPRRY_PICO_WSPRRYPI_SOURCE "" CACHE PATH "Explicit reviewed WsprryPi checkout for host client interoperability")
if(WSPRRY_PICO_WSPRRYPI_SOURCE)
    set(client_root "${WSPRRY_PICO_WSPRRYPI_SOURCE}/src/WTP-Client")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                    "${WSPRRY_PICO_WSPRRYPI_SOURCE}" COMMAND_ERROR_IS_FATAL ANY)
    add_custom_target(verify_host_client
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                "${WSPRRY_PICO_WSPRRYPI_SOURCE}")
    add_library(phase10_host_client STATIC
        "${client_root}/src/codec.cpp" "${client_root}/src/frame_parser.cpp"
        "${client_root}/src/wire.cpp" "${client_root}/src/session.cpp"
        "${client_root}/src/detail/json.cpp")
    target_include_directories(phase10_host_client PUBLIC "${client_root}/include" PRIVATE "${client_root}/src")
    target_compile_options(phase10_host_client PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_dependencies(phase10_host_client verify_host_client)
    add_library(phase10_endpoint_bridge STATIC tests/host_endpoint_bridge.cpp)
    target_link_libraries(phase10_endpoint_bridge PRIVATE wsprrypico_core wsprrypico_rf)
    target_compile_definitions(phase10_endpoint_bridge PRIVATE WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
    target_compile_options(phase10_endpoint_bridge PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_executable(host_client_interop_tests tests/host_client_interop_tests.cpp)
    target_link_libraries(host_client_interop_tests PRIVATE phase10_host_client phase10_endpoint_bridge)
    target_compile_options(host_client_interop_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME host_client_interop_tests COMMAND host_client_interop_tests)
endif()
