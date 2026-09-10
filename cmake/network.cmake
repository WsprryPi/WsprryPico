set(WSPRRY_PICO_NETWORK_PORT "0" CACHE STRING "TLS listener port; 0 disables network control")
set(WSPRRY_PICO_NETWORK_CREDENTIAL_DIR "" CACHE PATH "Local directory containing server.crt, server.key, client-ca.crt")
if(NOT WSPRRY_PICO_NETWORK_PORT MATCHES "^(0|[1-9][0-9]*)$" OR WSPRRY_PICO_NETWORK_PORT GREATER 65535)
    message(FATAL_ERROR "Invalid TLS listener port")
endif()
set(WSPRRY_PICO_NETWORK_HOSTNAME "")
set(WSPRRY_PICO_NETWORK_DEVICE_ID "")
set(WSPRRY_PICO_CERTIFICATE "")
set(WSPRRY_PICO_PRIVATE_KEY "")
set(WSPRRY_PICO_CLIENT_CA "")
if(WSPRRY_PICO_NETWORK_PORT)
    file(CHMOD ${CMAKE_BINARY_DIR} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE)
    if(NOT WSPRRY_PICO_NETWORK_CREDENTIAL_DIR)
        message(FATAL_ERROR "Network control requires device-specific local credentials")
    endif()
    execute_process(COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/network_certificates.py
        validate --directory "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}"
        OUTPUT_VARIABLE deployment COMMAND_ERROR_IS_FATAL ANY)
    string(JSON WSPRRY_PICO_NETWORK_HOSTNAME GET "${deployment}" hostname)
    string(JSON WSPRRY_PICO_NETWORK_DEVICE_ID GET "${deployment}" device_id)
    file(READ "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/server.crt" WSPRRY_PICO_CERTIFICATE)
    file(READ "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/server.key" WSPRRY_PICO_PRIVATE_KEY)
    file(READ "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/client-ca.crt" WSPRRY_PICO_CLIENT_CA)
    foreach(value WSPRRY_PICO_CERTIFICATE WSPRRY_PICO_PRIVATE_KEY WSPRRY_PICO_CLIENT_CA)
        if("${${value}}" MATCHES "[)]WP(CERT|KEY|CA)\"")
            message(FATAL_ERROR "Invalid credential encoding")
        endif()
    endforeach()
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/server.crt"
        "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/server.key"
        "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/client-ca.crt"
        "${WSPRRY_PICO_NETWORK_CREDENTIAL_DIR}/deployment.json"
        "${CMAKE_SOURCE_DIR}/scripts/network_certificates.py")
endif()
configure_file(${CMAKE_SOURCE_DIR}/cmake/network_credentials.hpp.in
               ${CMAKE_CURRENT_BINARY_DIR}/generated/network_credentials.hpp @ONLY)
file(CHMOD ${CMAKE_CURRENT_BINARY_DIR}/generated/network_credentials.hpp PERMISSIONS OWNER_READ OWNER_WRITE)
foreach(image WsprryPico WsprryPico-StandaloneRF)
    target_sources(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src/network/pico/server.cpp)
    target_include_directories(${image} PRIVATE ${CMAKE_SOURCE_DIR}/src/network/pico)
    target_link_libraries(${image} PRIVATE pico_mbedtls)
endforeach()

set_source_files_properties(${CMAKE_SOURCE_DIR}/src/network/pico/server.cpp
    PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
