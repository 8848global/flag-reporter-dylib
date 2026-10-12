#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mach-O 二进制文件修改工具：添加 LC_LOAD_DYLIB 命令
用法: python3 inject_dylib.py <binary> <dylib_path>
"""
import sys
import struct
import os
from pathlib import Path

# Mach-O 常量
MH_MAGIC_64 = 0xFEEDFACF
MH_CIGAM_64 = 0xCFFAEDFE
LC_LOAD_DYLIB = 0x0000000C
LC_REQ_DYLD = 0x80000000

# dylib_command 结构
# struct dylib_command {
#     uint32_t cmd;       // LC_LOAD_DYLIB
#     uint32_t cmdsize;   // 包含 dylib 结构体的总大小
#     struct dylib {
#         union lc_str name;      // 字符串偏移
#         uint32_t timestamp;
#         uint32_t current_version;
#         uint32_t compatibility_version;
#     } dylib;
# };

def read_u32(data, offset):
    """读取 32 位无符号整数"""
    return struct.unpack_from('<I', data, offset)[0]

def write_u32(data, offset, value):
    """写入 32 位无符号整数"""
    struct.pack_into('<I', data, offset, value)

def read_u64(data, offset):
    """读取 64 位无符号整数"""
    return struct.unpack_from('<Q', data, offset)[0]

def inject_dylib(binary_path, dylib_path):
    """向 Mach-O 二进制文件注入 LC_LOAD_DYLIB"""
    
    print(f"[*] 读取二进制文件: {binary_path}")
    with open(binary_path, 'rb') as f:
        data = bytearray(f.read())
    
    # 检查 Mach-O 魔数
    magic = read_u32(data, 0)
    if magic != MH_MAGIC_64:
        print(f"[-] 错误: 不是 64 位 Mach-O 文件 (magic: 0x{magic:X})")
        return False
    
    print("[+] 确认 64 位 Mach-O 文件")
    
    # 读取 Mach-O 头部
    # struct mach_header_64 {
    #     uint32_t magic;
    #     cpu_type_t cputype;
    #     cpu_subtype_t cpusubtype;
    #     uint32_t filetype;
    #     uint32_t ncmds;
    #     uint32_t sizeofcmds;
    #     uint32_t flags;
    #     uint32_t reserved;
    # };
    
    ncmds = read_u32(data, 16)
    sizeofcmds = read_u32(data, 20)
    
    print(f"[*] Load commands 数量: {ncmds}")
    print(f"[*] Load commands 总大小: {sizeofcmds} bytes")
    
    # 计算新的 load command 大小
    # dylib_command 结构体大小 = 24 bytes (cmd + cmdsize + name.offset + timestamp + current_version + compatibility_version)
    # 加上 dylib 路径字符串长度（包括 null 终止符）
    dylib_name = f"@executable_path/Frameworks/{os.path.basename(dylib_path)}"
    dylib_name_bytes = dylib_name.encode('utf-8') + b'\x00'
    
    # 计算对齐后的字符串大小（4 字节对齐）
    name_size = len(dylib_name_bytes)
    aligned_name_size = (name_size + 3) & ~3
    
    cmdsize = 24 + aligned_name_size  # dylib_command 固定部分 + 字符串
    
    print(f"[*] 新 LC_LOAD_DYLIB 大小: {cmdsize} bytes")
    print(f"[*] Dylib 路径: {dylib_name}")
    
    # 找到 load commands 的结束位置
    header_size = 32  # mach_header_64 大小
    load_commands_start = header_size
    load_commands_end = header_size + sizeofcmds
    
    # 找到第一个 segment 的位置（通常是 __TEXT）
    # 我们需要找到可以插入新 load command 的空间
    # 通常 load commands 后面跟着 segment 数据
    
    # 查找 __TEXT segment 的偏移
    offset = load_commands_start
    text_segment_offset = None
    for i in range(ncmds):
        cmd = read_u32(data, offset)
        cmd_size = read_u32(data, offset + 4)
        
        if cmd == 0x19:  # LC_SEGMENT_64
            segname = data[offset + 8:offset + 24].split(b'\x00')[0].decode('utf-8')
            if segname == '__TEXT':
                text_segment_offset = offset
                break
        
        offset += cmd_size
    
    if text_segment_offset is None:
        print("[-] 错误: 未找到 __TEXT segment")
        return False
    
    print(f"[*] __TEXT segment 位置: 0x{text_segment_offset:X}")
    
    # 创建新的 dylib_command
    new_cmd = bytearray(cmdsize)
    
    # 填充 dylib_command 结构
    write_u32(new_cmd, 0, LC_LOAD_DYLIB)  # cmd
    write_u32(new_cmd, 4, cmdsize)         # cmdsize
    write_u32(new_cmd, 8, 24)              # dylib.name.offset (指向字符串)
    write_u32(new_cmd, 12, 0)              # dylib.timestamp
    write_u32(new_cmd, 16, 0x00010000)     # dylib.current_version (1.0.0)
    write_u32(new_cmd, 20, 0x00010000)     # dylib.compatibility_version (1.0.0)
    
    # 填充 dylib 名称字符串
    new_cmd[24:24 + len(dylib_name_bytes)] = dylib_name_bytes
    
    # 在 load commands 末尾插入新命令
    # 首先将新命令添加到 load commands 区域之后
    new_data = bytearray()
    new_data.extend(data[:load_commands_end])
    new_data.extend(new_cmd)
    new_data.extend(data[load_commands_end:])
    
    # 更新 mach_header_64
    write_u32(new_data, 16, ncmds + 1)           # ncmds
    write_u32(new_data, 20, sizeofcmds + cmdsize) # sizeofcmds
    
    # 写入新文件
    backup_path = binary_path + '.backup'
    print(f"[*] 备份原文件: {backup_path}")
    os.rename(binary_path, backup_path)
    
    print(f"[*] 写入修改后的二进制: {binary_path}")
    with open(binary_path, 'wb') as f:
        f.write(new_data)
    
    print("[+] 注入成功!")
    print(f"[*] 原文件已备份为: {backup_path}")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python3 inject_dylib.py <binary> <dylib_path>")
        print("示例: python3 inject_dylib.py WebViewShell FlagReporter.dylib")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    dylib_path = sys.argv[2]
    
    if not os.path.exists(binary_path):
        print(f"[-] 错误: 二进制文件不存在: {binary_path}")
        sys.exit(1)
    
    if not os.path.exists(dylib_path):
        print(f"[-] 错误: Dylib 文件不存在: {dylib_path}")
        sys.exit(1)
    
    success = inject_dylib(binary_path, dylib_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
