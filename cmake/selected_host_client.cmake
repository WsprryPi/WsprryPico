include_guard(GLOBAL)
# Caller-selected retained byte-stream API, with source verification before
# every consuming build. No wire protocol objects are linked into fixtures.
function(wsprry_selected_host_client name source verifier)
    file(REAL_PATH "${source}/src/WTP-Client" client)
    add_library(${name} INTERFACE)
    target_include_directories(${name} INTERFACE "${client}/include")
    add_dependencies(${name} ${verifier})
endfunction()
