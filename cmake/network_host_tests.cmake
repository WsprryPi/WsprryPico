set(WSPRRY_PICO_TEST_MBEDTLS_PATH "" CACHE PATH "Optional pinned local Mbed TLS for actual TLS host tests")
if(WSPRRY_PICO_TEST_MBEDTLS_PATH)
    # The test executable embeds its ephemeral server private key too.
    file(CHMOD ${CMAKE_BINARY_DIR} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE)
    enable_language(C)
    execute_process(COMMAND git -C "${WSPRRY_PICO_TEST_MBEDTLS_PATH}" rev-parse HEAD
        OUTPUT_VARIABLE tls_revision OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE tls_result)
    if(NOT tls_result EQUAL 0 OR NOT tls_revision STREQUAL "0bebf8b8c7f07abe3571ded48a11aa907a1ffb20")
        message(FATAL_ERROR "TLS tests require the SDK-pinned Mbed TLS revision")
    endif()
    execute_process(COMMAND git -C "${WSPRRY_PICO_TEST_MBEDTLS_PATH}" status --porcelain --untracked-files=normal
        OUTPUT_VARIABLE tls_status OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE tls_status_result)
    if(NOT tls_status_result EQUAL 0 OR NOT tls_status STREQUAL "")
        message(FATAL_ERROR "TLS tests require an unmodified pinned Mbed TLS checkout")
    endif()
    set(MBEDTLS_DIR ${WSPRRY_PICO_TEST_MBEDTLS_PATH})
    set(MBEDTLS_CONFIG_FILE "${CMAKE_SOURCE_DIR}/src/network/pico/mbedtls_config.h")
    set(GEN_FILES OFF)
    set(USE_STATIC_MBEDTLS_LIBRARY ON)
    set(USE_SHARED_MBEDTLS_LIBRARY OFF)
    set(DISABLE_PACKAGE_CONFIG_AND_INSTALL ON)
    add_subdirectory(${WSPRRY_PICO_TEST_MBEDTLS_PATH}/library ${CMAKE_BINARY_DIR}/mbedtls)
    include(${CMAKE_SOURCE_DIR}/cmake/mbedtls_alert_overlay.cmake)
    wsprry_mbedtls_alert_overlay(mbedtls SOURCES "${WSPRRY_PICO_TEST_MBEDTLS_PATH}")
    set(WSPRRY_PICO_TEST_CREDENTIAL_DIR "${CMAKE_BINARY_DIR}/network-test-credentials-v3")
    set(WSPRRY_PICO_TEST_CREDENTIALS_VALID FALSE)
    if(EXISTS "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}/server.key")
        execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/network_certificates.py
            validate --directory "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}"
            OUTPUT_VARIABLE deployment RESULT_VARIABLE credential_result)
        if(credential_result EQUAL 0)
            set(WSPRRY_PICO_TEST_CREDENTIALS_VALID TRUE)
        else()
            file(REMOVE_RECURSE "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}")
        endif()
    elseif(EXISTS "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}")
        file(REMOVE_RECURSE "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}")
    endif()
    if(NOT WSPRRY_PICO_TEST_CREDENTIALS_VALID)
        execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/generate_network_test_credentials.py
            "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}" COMMAND_ERROR_IS_FATAL ANY)
    endif()
    execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/network_certificates.py
        validate --directory "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}"
        OUTPUT_VARIABLE deployment COMMAND_ERROR_IS_FATAL ANY)
    string(JSON WSPRRY_PICO_NETWORK_HOSTNAME GET "${deployment}" hostname)
    string(JSON WSPRRY_PICO_NETWORK_DEVICE_ID GET "${deployment}" device_id)
    if(NOT WSPRRY_PICO_NETWORK_DEVICE_ID STREQUAL "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        message(FATAL_ERROR "Named TLS tests require the generated Phase 11.3 deployment identity")
    endif()
    set(WSPRRY_PICO_NETWORK_PORT 18443)
    file(READ "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}/server.crt" WSPRRY_PICO_CERTIFICATE)
    file(READ "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}/server.key" WSPRRY_PICO_PRIVATE_KEY)
    file(READ "${WSPRRY_PICO_TEST_CREDENTIAL_DIR}/client-ca.crt" WSPRRY_PICO_CLIENT_CA)
    configure_file(${CMAKE_SOURCE_DIR}/cmake/network_credentials.hpp.in
                   ${CMAKE_BINARY_DIR}/network-test-generated/network_credentials.hpp @ONLY)
    file(CHMOD ${CMAKE_BINARY_DIR}/network-test-generated/network_credentials.hpp PERMISSIONS OWNER_READ OWNER_WRITE)
    add_executable(network_tls_driver
        tests/network_tls_driver.cpp tests/network_mock/tcp.cpp
        src/network/pico/psa_lifetime.cpp src/network/pico/server.cpp
        src/provisioning/pico/credential_validator.cpp)
    target_include_directories(network_tls_driver PRIVATE tests/network_mock ${CMAKE_BINARY_DIR}/network-test-generated)
    target_compile_definitions(network_tls_driver PRIVATE MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}")
    target_link_libraries(network_tls_driver PRIVATE wsprrypico_core wsprrypico_rf Threads::Threads mbedtls mbedx509 mbedcrypto)
    target_compile_options(network_tls_driver PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME network_tls_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/network_tls_tests.py
        $<TARGET_FILE:network_tls_driver> ${WSPRRY_PICO_TEST_CREDENTIAL_DIR})
    set_tests_properties(network_tls_tests PROPERTIES TIMEOUT 90 RUN_SERIAL TRUE)
    add_test(NAME network_local_wtp_tests COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_SOURCE_DIR}/tests/network_local_wtp_tests.py
        $<TARGET_FILE:network_tls_driver> ${WSPRRY_PICO_TEST_CREDENTIAL_DIR})
    set_tests_properties(network_local_wtp_tests PROPERTIES TIMEOUT 30 RUN_SERIAL TRUE)
    add_executable(bootstrap_crypto_tests tests/bootstrap_crypto_tests.cpp
        src/network/pico/bootstrap_crypto.cpp src/network/pico/psa_lifetime.cpp)
    target_compile_definitions(bootstrap_crypto_tests PRIVATE
        MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}" WSPRRY_PICO_BOOTSTRAP_CRYPTO_TEST=1)
    target_link_libraries(bootstrap_crypto_tests PRIVATE wsprrypico_core mbedcrypto)
    target_compile_options(bootstrap_crypto_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME bootstrap_crypto_tests COMMAND bootstrap_crypto_tests
        ${CMAKE_SOURCE_DIR}/docs/protocol/WiFi-Bootstrap-v1-vectors.json)
    add_executable(owner_claim_crypto_tests tests/owner_claim_crypto_tests.cpp
        src/network/pico/owner_claim_crypto.cpp src/network/pico/psa_lifetime.cpp)
    target_compile_definitions(owner_claim_crypto_tests PRIVATE
        MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}" WSPRRY_PICO_OWNER_CLAIM_CRYPTO_TEST=1)
    target_link_libraries(owner_claim_crypto_tests PRIVATE wsprrypico_core mbedcrypto)
    target_compile_options(owner_claim_crypto_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME owner_claim_crypto_tests COMMAND owner_claim_crypto_tests)
    add_executable(owner_signature_tests tests/owner_signature_tests.cpp
        src/network/pico/owner_signature.cpp src/network/pico/psa_lifetime.cpp)
    target_compile_definitions(owner_signature_tests PRIVATE
        MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}")
    target_link_libraries(owner_signature_tests PRIVATE wsprrypico_core mbedcrypto)
    target_compile_options(owner_signature_tests PRIVATE -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME owner_signature_tests COMMAND owner_signature_tests)
    add_executable(consumer_tls_generator_tests tests/consumer_tls_generator_tests.cpp
        src/provisioning/pico/consumer_tls_generator.cpp
        src/provisioning/pico/consumer_tls_validator.cpp
        src/provisioning/pico/credential_validator.cpp
        src/network/pico/psa_lifetime.cpp)
    target_compile_definitions(consumer_tls_generator_tests PRIVATE
        MBEDTLS_CONFIG_FILE="${MBEDTLS_CONFIG_FILE}")
    target_link_libraries(consumer_tls_generator_tests PRIVATE
        wsprrypico_core wsprrypico_rf mbedx509 mbedcrypto)
    target_compile_options(consumer_tls_generator_tests PRIVATE
        -Wall -Wextra -Wpedantic -Werror -UNDEBUG)
    add_test(NAME consumer_tls_generator_tests COMMAND consumer_tls_generator_tests)
endif()

include(${CMAKE_SOURCE_DIR}/cmake/network_client_interop.cmake)
