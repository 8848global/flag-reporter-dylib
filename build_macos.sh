#!/bin/bash
# 在 macOS 上编译 FlagReporter dylib
# 用法: ./build_macos.sh

set -e

echo "=== 编译 FlagReporter dylib ==="

# 检查 Xcode 命令行工具
if ! command -v xcrun &> /dev/null; then
    echo "ERROR: Xcode 命令行工具未安装"
    echo "请运行: xcode-select --install"
    exit 1
fi

# 获取 iOS SDK 路径
SDK_PATH=$(xcrun --sdk iphoneos --show-sdk-path)
if [ ! -d "$SDK_PATH" ]; then
    echo "ERROR: iOS SDK 未找到"
    echo "请安装 Xcode 和 iOS 开发工具"
    exit 1
fi

echo "SDK 路径: $SDK_PATH"

# 编译 dylib (arm64)
echo "编译 arm64 版本..."
clang -shared -fobjc-arc \
    -target arm64-apple-ios13.0 \
    -isysroot "$SDK_PATH" \
    -framework Foundation \
    -framework UIKit \
    -o FlagReporter.arm64.dylib \
    FlagReporter.m

echo "✓ arm64 编译完成"

# 创建最终 dylib
mv FlagReporter.arm64.dylib FlagReporter.dylib
echo "✓ FlagReporter.dylib 创建成功"

# 显示文件信息
file FlagReporter.dylib
ls -lh FlagReporter.dylib

echo ""
echo "=== 编译完成 ==="
echo "将 FlagReporter.dylib 复制到 Linux 服务器的:"
echo "/www/wwwroot/chain2/backend_c2/flag_report_dlib/"
