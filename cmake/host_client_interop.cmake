# Optional test dependency only. Never fetched, installed or linked into firmware.
set(WSPRRY_PICO_WSPRRYPI_SOURCE "" CACHE PATH "Caller-selected WsprryPi sources for host client interoperability")
if(WSPRRY_PICO_WSPRRYPI_SOURCE)
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                    "${WSPRRY_PICO_WSPRRYPI_SOURCE}" COMMAND_ERROR_IS_FATAL ANY)
    add_custom_target(verify_host_client
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                "${WSPRRY_PICO_WSPRRYPI_SOURCE}")
    include(${CMAKE_SOURCE_DIR}/cmake/selected_host_client.cmake)
    wsprry_selected_host_client(reference_host_client "${WSPRRY_PICO_WSPRRYPI_SOURCE}" verify_host_client)
    add_library(host_endpoint_bridge STATIC tests/host_endpoint_bridge.cpp)
    target_link_libraries(host_endpoint_bridge PRIVATE wsprrypico_core wsprrypico_rf)
    target_compile_definitions(host_endpoint_bridge PRIVATE WSPRRY_PICO_RF_SAMPLE_RATE_HZ=${WSPRRY_PICO_RF_SAMPLE_RATE_HZ})
    target_compile_options(host_endpoint_bridge PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_executable(host_client_interop_tests tests/host_client_interop_tests.cpp)
    target_link_libraries(host_client_interop_tests PRIVATE reference_host_client host_endpoint_bridge)
    target_compile_options(host_client_interop_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME host_client_interop_tests COMMAND host_client_interop_tests)
    add_test(NAME companion_source_selection_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/companion_source_selection_tests.py "${WSPRRY_PICO_WSPRRYPI_SOURCE}")
endif()
