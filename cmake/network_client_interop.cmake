# Explicit, read-only companion input. This does not bypass its Pico source gate.
set(WSPRRY_PICO_NETWORK_CLIENT_SOURCE "" CACHE PATH "Pinned WsprryPi client checkout")
if(WSPRRY_PICO_NETWORK_CLIENT_SOURCE AND TARGET network_tls_driver)
    set(parent "${WSPRRY_PICO_NETWORK_CLIENT_SOURCE}")
    set(pin 2e47641f6ebdff104e32999f5194f2e0dc408e06)
    execute_process(COMMAND git -C "${parent}" rev-parse HEAD OUTPUT_VARIABLE revision
        OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    execute_process(COMMAND git -C "${parent}" status --porcelain --untracked-files=no
        OUTPUT_VARIABLE dirty OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
    if(NOT revision STREQUAL pin OR NOT dirty STREQUAL "")
        message(FATAL_ERROR "Client interoperability requires clean WsprryPi ${pin}")
    endif()
    find_package(OpenSSL REQUIRED)
    set(client "${parent}/src/WTP-Client")
    add_library(network_11_1_client STATIC
        ${client}/src/codec.cpp ${client}/src/frame_parser.cpp ${client}/src/wire.cpp
        ${client}/src/session.cpp ${client}/src/detail/json.cpp)
    target_include_directories(network_11_1_client PUBLIC ${client}/include PRIVATE ${client}/src)
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
