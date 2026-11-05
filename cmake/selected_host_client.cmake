include_guard(GLOBAL)

# Only host test consumers share these objects. Different selected peers retain
# independent compilations; firmware and fresh reproducibility builds never use
# this target. Both callers retain their source verifier and buildable archive.
function(wsprry_selected_host_client name source verifier)
    file(REAL_PATH "${source}/src/WTP-Client" client)
    string(SHA256 identity "${client}")
    set(objects "selected_host_client_${identity}")
    if(NOT TARGET ${objects})
        add_library(${objects} OBJECT
            "${client}/src/codec.cpp" "${client}/src/frame_parser.cpp"
            "${client}/src/wire.cpp" "${client}/src/session.cpp"
            "${client}/src/detail/json.cpp")
        target_include_directories(${objects} PRIVATE "${client}/include" "${client}/src")
        target_compile_options(${objects} PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_dependencies(${objects} ${verifier})
    add_library(${name} STATIC $<TARGET_OBJECTS:${objects}>)
    target_include_directories(${name} PUBLIC "${client}/include" PRIVATE "${client}/src")
    add_dependencies(${name} ${verifier})
endfunction()
