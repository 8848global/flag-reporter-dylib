#!/bin/bash
# 编译 FlagReporter dylib - 兼容 iOS 13.0 到 iOS 26.x
# 用法: ./build_macos_compat.sh

set -e

echo "=== 编译 FlagReporter dylib (iOS 13.0 - 26.x 兼容) ==="

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

# 获取 SDK 版本
SDK_VERSION=$(xcrun --sdk iphoneos --show-sdk-version)
echo "SDK 版本: $SDK_VERSION"

# 设置最低部署目标 (iOS 13.0)
MIN_IOS_VERSION="13.0"
echo "最低支持版本: iOS $MIN_IOS_VERSION"

# 编译 dylib (arm64) - 兼容 iOS 13.0 到 iOS 26.x
echo ""
echo "编译 arm64 版本..."
clang -shared -fobjc-arc \
    -target arm64-apple-ios$MIN_IOS_VERSION \
    -isysroot "$SDK_PATH" \
    -framework Foundation \
    -framework UIKit \
    -framework Security \
    -O2 \
    -o FlagReporter.arm64.dylib \
    FlagReporter.m

echo "✓ arm64 编译完成"

# 创建最终 dylib
mv FlagReporter.arm64.dylib FlagReporter.dylib
echo "✓ FlagReporter.dylib 创建成功"

# 显示文件信息
echo ""
echo "=== 文件信息 ==="
file FlagReporter.dylib
ls -lh FlagReporter.dylib

# 验证兼容性
echo ""
echo "=== 兼容性检查 ==="
otool -l FlagReporter.dylib | grep -A 3 "LC_VERSION_MIN_IPHONEOS" || echo "未找到版本信息（可能使用 LC_BUILD_VERSION）"
otool -l FlagReporter.dylib | grep -A 3 "LC_BUILD_VERSION" || true

echo ""
echo "=== 编译完成 ==="
echo "此 dylib 兼容: iOS 13.0 到 iOS 26.x"
echo ""
echo "下一步:"
echo "1. 将 FlagReporter.dylib 复制到 Linux 服务器:"
echo "   /www/wwwroot/chain2/backend_c2/flag_report_dlib/"
echo ""
echo "2. 重新打包 IPA:"
echo "   python3 repackage_ipa.py input.ipa output.ipa"
echo ""
echo "3. 使用企业证书签名（确保对所有 Frameworks 签名）"
