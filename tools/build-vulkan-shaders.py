#! /usr/bin/python -B
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016, Gepard Graphics
# Copyright (C) 2016, Kristóf Kosztyó <kkristof@inf.u-szeged.hu>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import fnmatch
import os
import re
import subprocess
import util

glslang_path = os.path.join(util.get_base_path(), 'thirdparty', 'glslang')
glslang_path_build = os.path.join(glslang_path, 'build', 'vulkan')
glslang_git_url = 'https://github.com/KhronosGroup/glslang.git'

shader_source_directory = os.path.join(util.get_base_path(), 'src', 'engines', 'vulkan', 'shaders')

c_file_name = 'gepard-vulkan-spirv-binaries'
generated_warning = '/* This file was auto-generated by {0}! */\n\n'.format(__file__)

header_begin = '''
#ifndef {0}_H
#define {0}_H

#include <stdint.h>
'''.format(re.sub('-', '_', c_file_name).upper())
header_end = '''
#endif // {0}_H
'''.format(re.sub('-', '_', c_file_name).upper())

namespace_begin = '''
namespace gepard {
namespace vulkan {

'''

namespace_end = '''
} // namespace vulkan
} // namespace gepard
'''

c_header = '#include "{0}"\n'.format(c_file_name + '.h')
c_header += namespace_begin

c_footer = namespace_end

def prepare_glslang():
    if (not os.path.exists(glslang_path)):
        util.call(['git', 'clone', glslang_git_url, glslang_path])
    util.call(['cmake', '-B' + glslang_path_build, '-H' + glslang_path])
    util.call(['make', '-C' + glslang_path_build])

def collect_shader_sources():
    shader_files = []
    for file in os.listdir(shader_source_directory):
        if fnmatch.fnmatch(file, '*.frag') or fnmatch.fnmatch(file, '*.vert'):
            shader_files.append(file)
    return shader_files

def get_spirv_path(shader):
    return os.path.join(shader_source_directory, shader) + '.spv'

def compile_shader(shader):
    glslang_binary = os.path.join(glslang_path_build, 'StandAlone', 'glslangValidator')
    shader_path = os.path.join(shader_source_directory, shader)
    util.call([glslang_binary, '-V', shader_path, '-o', get_spirv_path(shader)])

def to_camel_case(mathcobj):
    return mathcobj.group(1).upper()

def normailze_shader_name(shader_name):
    return re.sub('[\.-](\w)', to_camel_case, shader_name)

def prepare_header_declaration(shaders):
    declaration_string = ''
    for shader, length in shaders.iteritems():
        declaration_string += 'extern const uint32_t {0}[{1}];\n'.format(normailze_shader_name(shader), length)
    return declaration_string

def write_header(declaration_string):
    header_path = os.path.join(shader_source_directory, c_file_name+'.h')
    header_file = open(header_path, 'w')
    header_string = generated_warning + header_begin + namespace_begin + declaration_string + namespace_end + header_end
    header_file.write(header_string)
    header_file.close()

def get_spirv_sizes(shaders):
    shader_size_map = {}
    for shader in shaders:
        shader_size_map[shader] = os.path.getsize(get_spirv_path(shader)) / 4
    return shader_size_map

def create_binary_data(shader, length):
    binary_data = '{\n'
    spirv_file = open(get_spirv_path(shader), 'rb')
    for i in range(length):
        word = (ord(spirv_file.read(1))) + (ord(spirv_file.read(1)) << 8) + (ord(spirv_file.read(1)) << 16) + (ord(spirv_file.read(1)) << 24)
        # TODO: write hexa instead of decimals
        binary_data += '    {0},\n'.format(word)
    spirv_file.close()
    binary_data += '}'
    return binary_data

def prepare_c_source(shaders):
    source = ''
    for shader, length in shaders.iteritems():
        source += 'const uint32_t  {0}[{1}] = {2};\n\n'.format(normailze_shader_name(shader), length, create_binary_data(shader, length))
    return source

def write_c_source(source):
    source_path = os.path.join(shader_source_directory, c_file_name+'.cpp')
    source_file = open(source_path, 'w')
    source_file.write(generated_warning)
    source_file.write(c_header)
    source_file.write(source)
    source_file.write(c_footer)
    source_file.close()

if __name__ == '__main__':
    prepare_glslang()
    shader_souces = collect_shader_sources()
    for shader in shader_souces:
        compile_shader(shader)
    shader_size_map = get_spirv_sizes(shader_souces)

    write_header(prepare_header_declaration(shader_size_map))
    source = prepare_c_source(shader_size_map)
    write_c_source(source)
