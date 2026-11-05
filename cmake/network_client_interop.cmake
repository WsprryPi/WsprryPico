# Explicit caller-selected companion input, including edited working sources.
set(WSPRRY_PICO_NETWORK_CLIENT_SOURCE "" CACHE PATH "Caller-selected WsprryPi network client sources")
if(WSPRRY_PICO_NETWORK_CLIENT_SOURCE AND TARGET network_tls_driver)
    set(parent "${WSPRRY_PICO_NETWORK_CLIENT_SOURCE}")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                    "${parent}" COMMAND_ERROR_IS_FATAL ANY)
    add_custom_target(verify_network_client
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py" "${parent}")
    find_package(OpenSSL REQUIRED)
    include(${CMAKE_SOURCE_DIR}/cmake/selected_host_client.cmake)
    wsprry_selected_host_client(network_11_1_client "${parent}" verify_network_client)
    set(source "${parent}/src")
    add_executable(wtp_network_interop_test
        ${source}/tests/wtp_network_interop_test.cpp
        ${source}/wtp_integration/tls.cpp ${source}/wtp_integration/network_http.cpp
        ${source}/wtp_integration/application.cpp ${source}/wtp_integration/status.cpp
        ${source}/wtp_integration/scheduler.cpp ${source}/wtp_integration/backend.cpp
        ${source}/wtp_integration/execution_plan.cpp
        ${source}/WSPR-Transmitter/src/execution_plan_compiler.cpp
        ${source}/WSPR-Transmitter/src/transmission_controller.cpp)
    target_include_directories(wtp_network_interop_test PRIVATE ${source})
    target_link_libraries(wtp_network_interop_test PRIVATE network_11_1_client OpenSSL::SSL OpenSSL::Crypto Threads::Threads)
    target_compile_options(wtp_network_interop_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
    # Compile the selected companion's orchestrator and server together. Its
    # READY protocol and real-clock RF adapter belong to that source pair;
    # aliasing Pico's diagnostic driver silently substituted a different fixture.
    add_executable(pico_tls_server
        ${source}/tests/network/pico_tls_server.cpp ${source}/tests/network/tcp.cpp
        src/network/pico/server.cpp src/network/pico/psa_lifetime.cpp
        src/provisioning/pico/credential_validator.cpp)
    target_include_directories(pico_tls_server PRIVATE ${source}/tests/network
        tests tests/network_mock ${CMAKE_BINARY_DIR}/network-test-generated)
    target_compile_definitions(pico_tls_server PRIVATE MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}")
    target_link_libraries(pico_tls_server PRIVATE wsprrypico_core wsprrypico_rf
        Threads::Threads mbedtls mbedx509 mbedcrypto)
    target_compile_options(pico_tls_server PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_dependencies(pico_tls_server verify_network_client)
    add_custom_command(TARGET pico_tls_server POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E create_symlink ${WSPRRY_PICO_TEST_CREDENTIAL_DIR} ${CMAKE_BINARY_DIR}/credentials-v3)
    # Retain the historical target name for existing developer invocations.
    add_executable(wtp_fixture_clock_test ${source}/tests/network/fixture_clock_test.cpp)
    target_include_directories(wtp_fixture_clock_test PRIVATE ${source}/tests/network)
    target_link_libraries(wtp_fixture_clock_test PRIVATE wsprrypico_core)
    target_compile_options(wtp_fixture_clock_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_dependencies(wtp_fixture_clock_test verify_network_client)
    add_test(NAME paired_fixture_clock_test COMMAND wtp_fixture_clock_test)
    add_test(NAME network_11_1_interop COMMAND ${Python3_EXECUTABLE}
        ${source}/tests/wtp_network_interop_test.py ${CMAKE_BINARY_DIR})
    set_tests_properties(network_11_1_interop PROPERTIES TIMEOUT 200 RUN_SERIAL TRUE)
endif()
