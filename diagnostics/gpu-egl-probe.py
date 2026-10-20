#!/usr/bin/python3
"""Bounded offscreen GPU readback probe; never owns the display or changes it."""
import argparse
import ctypes as c
import hashlib
import json
import os
import time

parser = argparse.ArgumentParser()
parser.add_argument('--frames', type=int, default=3)
parser.add_argument('--size', type=int, default=64)
parser.add_argument('--delay', type=float, default=.01)
args = parser.parse_args()
assert 1 <= args.frames <= 1000 and 1 <= args.size <= 1024
assert .001 <= args.delay <= .25

P, I, U = c.c_void_p, c.c_int, c.c_uint
def declare(lib, name, result, *arguments):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, list(arguments)
    return fn

egl = c.CDLL('libEGL.so.1')
gbm = c.CDLL('libgbm.so.1')
gl = c.CDLL('libGLESv2.so.2')
create_device = declare(gbm, 'gbm_create_device', P, I)
destroy_device = declare(gbm, 'gbm_device_destroy', None, P)
get_proc = declare(egl, 'eglGetProcAddress', P, c.c_char_p)
initialize = declare(egl, 'eglInitialize', U, P, c.POINTER(I), c.POINTER(I))
choose = declare(egl, 'eglChooseConfig', U, P, c.POINTER(I), c.POINTER(P), I, c.POINTER(I))
bind = declare(egl, 'eglBindAPI', U, U)
context_create = declare(egl, 'eglCreateContext', P, P, P, P, c.POINTER(I))
make_current = declare(egl, 'eglMakeCurrent', U, P, P, P, P)
context_destroy = declare(egl, 'eglDestroyContext', U, P, P)
terminate = declare(egl, 'eglTerminate', U, P)
error = declare(egl, 'eglGetError', U)
get_string = declare(gl, 'glGetString', c.c_char_p, U)
gl_error = declare(gl, 'glGetError', U)
gen_tex = declare(gl, 'glGenTextures', None, I, c.POINTER(U))
bind_tex = declare(gl, 'glBindTexture', None, U, U)
tex_image = declare(gl, 'glTexImage2D', None, U, I, I, I, I, I, U, U, P)
tex_param = declare(gl, 'glTexParameteri', None, U, U, I)
gen_fb = declare(gl, 'glGenFramebuffers', None, I, c.POINTER(U))
bind_fb = declare(gl, 'glBindFramebuffer', None, U, U)
attach = declare(gl, 'glFramebufferTexture2D', None, U, U, U, U, I)
check_fb = declare(gl, 'glCheckFramebufferStatus', U, U)
clear_color = declare(gl, 'glClearColor', None, c.c_float, c.c_float, c.c_float, c.c_float)
clear = declare(gl, 'glClear', None, U)
read_pixels = declare(gl, 'glReadPixels', None, I, I, I, I, U, U, P)
delete_fb = declare(gl, 'glDeleteFramebuffers', None, I, c.POINTER(U))
delete_tex = declare(gl, 'glDeleteTextures', None, I, c.POINTER(U))
create_shader = declare(gl, 'glCreateShader', U, U)
shader_source = declare(gl, 'glShaderSource', None, U, I, c.POINTER(c.c_char_p), c.POINTER(I))
compile_shader = declare(gl, 'glCompileShader', None, U)
shader_status = declare(gl, 'glGetShaderiv', None, U, U, c.POINTER(I))
shader_log = declare(gl, 'glGetShaderInfoLog', None, U, I, c.POINTER(I), c.c_char_p)
delete_shader = declare(gl, 'glDeleteShader', None, U)
create_program = declare(gl, 'glCreateProgram', U)
attach_shader = declare(gl, 'glAttachShader', None, U, U)
bind_attribute = declare(gl, 'glBindAttribLocation', None, U, U, c.c_char_p)
link_program = declare(gl, 'glLinkProgram', None, U)
program_status = declare(gl, 'glGetProgramiv', None, U, U, c.POINTER(I))
use_program = declare(gl, 'glUseProgram', None, U)
uniform_location = declare(gl, 'glGetUniformLocation', I, U, c.c_char_p)
uniform4 = declare(gl, 'glUniform4f', None, I, c.c_float, c.c_float, c.c_float, c.c_float)
delete_program = declare(gl, 'glDeleteProgram', None, U)
gen_buffers = declare(gl, 'glGenBuffers', None, I, c.POINTER(U))
bind_buffer = declare(gl, 'glBindBuffer', None, U, U)
buffer_data = declare(gl, 'glBufferData', None, U, c.c_ssize_t, P, U)
vertex_pointer = declare(gl, 'glVertexAttribPointer', None, U, I, U, c.c_ubyte, I, P)
enable_attribute = declare(gl, 'glEnableVertexAttribArray', None, U)
draw_arrays = declare(gl, 'glDrawArrays', None, U, I, I)
viewport = declare(gl, 'glViewport', None, I, I, I, I)
delete_buffers = declare(gl, 'glDeleteBuffers', None, I, c.POINTER(U))

def shader(kind, source):
    handle = create_shader(kind)
    text = c.c_char_p(source)
    shader_source(handle, 1, c.byref(text), None)
    compile_shader(handle)
    status = I()
    shader_status(handle, 0x8B81, c.byref(status))
    if not status.value:
        log = c.create_string_buffer(2048)
        shader_log(handle, len(log), None, log)
        raise RuntimeError(log.value.decode())
    return handle

def require(ok, stage):
    if not ok:
        raise RuntimeError(f'{stage}: EGL error {error():#x}')

fd = os.open('/dev/dri/renderD128', os.O_RDWR | os.O_CLOEXEC)
device = display = context = None
texture, framebuffer = U(), U()
vertices = U()
program = 0
start = time.monotonic()
try:
    device = create_device(fd)
    require(device, 'gbm_create_device')
    get_platform = c.CFUNCTYPE(P, U, P, c.POINTER(I))(get_proc(b'eglGetPlatformDisplayEXT'))
    display = get_platform(0x31D7, device, None)  # EGL_PLATFORM_GBM_KHR
    major, minor = I(), I()
    require(initialize(display, c.byref(major), c.byref(minor)), 'eglInitialize')
    require(bind(0x30A0), 'eglBindAPI')  # OpenGL ES
    config, count = P(), I()
    attributes = (I * 3)(0x3040, 4, 0x3038)  # ES2 renderable, EGL_NONE
    require(choose(display, attributes, c.byref(config), 1, c.byref(count)) and count.value, 'eglChooseConfig')
    context = context_create(display, config, None, (I * 3)(0x3098, 2, 0x3038))
    require(context, 'eglCreateContext')
    require(make_current(display, None, None, context), 'surfaceless eglMakeCurrent')
    renderer = get_string(0x1F01).decode()
    print(json.dumps({'renderer': renderer, 'version': get_string(0x1F02).decode(),
                      'debug': os.environ.get('FD_MESA_DEBUG', '')}), flush=True)
    assert 'FD610' in renderer or 'Adreno' in renderer, 'Hardware renderer required'
    gen_tex(1, c.byref(texture))
    bind_tex(0x0DE1, texture)
    tex_param(0x0DE1, 0x2801, 0x2600)
    tex_param(0x0DE1, 0x2800, 0x2600)
    tex_image(0x0DE1, 0, 0x1908, args.size, args.size, 0, 0x1908, 0x1401, None)
    gen_fb(1, c.byref(framebuffer))
    bind_fb(0x8D40, framebuffer)
    attach(0x8D40, 0x8CE0, 0x0DE1, texture, 0)
    assert check_fb(0x8D40) == 0x8CD5, 'Framebuffer incomplete'
    vs = shader(0x8B31, b'attribute vec2 position; void main(){gl_Position=vec4(position,0.0,1.0);}')
    fs = shader(0x8B30, b'precision mediump float; uniform vec4 color; void main(){gl_FragColor=color;}')
    program = create_program()
    attach_shader(program, vs)
    attach_shader(program, fs)
    bind_attribute(program, 0, b'position')
    link_program(program)
    linked = I()
    program_status(program, 0x8B82, c.byref(linked))
    assert linked.value, 'Shader program link failed'
    delete_shader(vs)
    delete_shader(fs)
    use_program(program)
    color_location = uniform_location(program, b'color')
    triangle = (c.c_float * 6)(-1, -1, 3, -1, -1, 3)
    gen_buffers(1, c.byref(vertices))
    bind_buffer(0x8892, vertices)
    buffer_data(0x8892, c.sizeof(triangle), triangle, 0x88E4)
    vertex_pointer(0, 2, 0x1406, 0, 0, None)
    enable_attribute(0)
    viewport(0, 0, args.size, args.size)
    pixels = (c.c_ubyte * (args.size * args.size * 4))()
    for frame in range(args.frames):
        color = (1, 0, 0, 1) if frame % 2 == 0 else (0, 1, 0, 1)
        clear_color(0, 0, 1, 1)
        clear(0x4000)
        uniform4(color_location, *color)
        draw_arrays(4, 0, 3)
        read_pixels(0, 0, args.size, args.size, 0x1908, 0x1401, pixels)
        assert gl_error() == 0, 'OpenGL error'
        expected = bytes(v * 255 for v in color) * (args.size * args.size)
        assert bytes(pixels) == expected, f'Readback mismatch in frame {frame}'
        time.sleep(args.delay)
    print(json.dumps({'result': 'PASS', 'frames': args.frames, 'size': args.size,
                      'seconds': round(time.monotonic() - start, 3),
                      'sha256': hashlib.sha256(bytes(pixels)).hexdigest()}), flush=True)
finally:
    if context:
        delete_buffers(1, c.byref(vertices))
        if program: delete_program(program)
        delete_fb(1, c.byref(framebuffer))
        delete_tex(1, c.byref(texture))
        make_current(display, None, None, None)
        context_destroy(display, context)
    if display: terminate(display)
    if device: destroy_device(device)
    os.close(fd)
