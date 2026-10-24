# Explicit caller-selected companion input, including edited working sources.
set(WSPRRY_PICO_NETWORK_CLIENT_SOURCE "" CACHE PATH "Caller-selected WsprryPi network client sources")
if(WSPRRY_PICO_NETWORK_CLIENT_SOURCE AND TARGET network_tls_driver)
    set(parent "${WSPRRY_PICO_NETWORK_CLIENT_SOURCE}")
    execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py"
                    "${parent}" COMMAND_ERROR_IS_FATAL ANY)
    add_custom_target(verify_network_client
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/scripts/verify_wsprrypi_client.py" "${parent}")
    find_package(OpenSSL REQUIRED)
    set(client "${parent}/src/WTP-Client")
    add_library(network_11_1_client STATIC
        ${client}/src/codec.cpp ${client}/src/frame_parser.cpp ${client}/src/wire.cpp
        ${client}/src/session.cpp ${client}/src/detail/json.cpp)
    target_include_directories(network_11_1_client PUBLIC ${client}/include PRIVATE ${client}/src)
    add_dependencies(network_11_1_client verify_network_client)
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
    # Original MIT client and restart orchestrator are built/read unchanged.
    # Pico's own driver supports the same boot/device fault injection arguments.
    add_custom_command(TARGET network_tls_driver POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E create_symlink $<TARGET_FILE:network_tls_driver> ${CMAKE_BINARY_DIR}/pico_tls_server
        COMMAND ${CMAKE_COMMAND} -E create_symlink ${WSPRRY_PICO_TEST_CREDENTIAL_DIR} ${CMAKE_BINARY_DIR}/credentials-v3)
    # Retain the historical target name for existing developer invocations.
    add_test(NAME network_11_1_interop COMMAND ${Python3_EXECUTABLE}
        ${source}/tests/wtp_network_interop_test.py ${CMAKE_BINARY_DIR})
    set_tests_properties(network_11_1_interop PROPERTIES TIMEOUT 200 RUN_SERIAL TRUE)
endif()
