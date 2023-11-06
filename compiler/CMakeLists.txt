# Reference:
# - https://github.com/fruffy/p4dummy/blob/master/CMakeLists.txt
# - https://github.com/p4lang/p4c/blob/main/backends/bmv2/CMakeLists.txt

set(CAIRN_SRCS
    main.cpp
    midend.h
    options.h
    )

add_executable(p4c-cairn ${CAIRN_SRCS})
target_link_libraries(p4c-cairn ${P4C_LIBRARIES} ${P4C_LIB_DEPS})
add_dependencies(p4c-cairn frontend midend)

install(TARGETS p4c-cairn RUNTIME DESTINATION ${P4C_RUNTIME_OUTPUT_DIRECTORY})

add_custom_target(linkcairn
    COMMAND ${CMAKE_COMMAND} -E create_symlink ${CMAKE_CURRENT_BINARY_DIR}/p4c-cairn ${P4C_BINARY_DIR}/p4c-cairn
    COMMAND ${CMAKE_COMMAND} -E create_symlink ${P4C_BINARY_DIR}/p4include ${CMAKE_CURRENT_BINARY_DIR}/p4include
)
add_dependencies(p4c_driver linkcairn)
