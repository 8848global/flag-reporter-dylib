# iOS 26 兼容性修改说明

## 修改内容

### 1. 新增 Security 框架导入
```objc
#import <Security/Security.h>
```
**原因**: iOS 26 需要显式导入 Security 框架以处理 SSL 证书验证

### 2. 增强 SSL 证书处理 (第 30-45 行)
**修改前**:
```objc
NSURLCredential *credential = [NSURLCredential credentialForTrust:challenge.protectionSpace.serverTrust];
completionHandler(NSURLSessionAuthChallengeUseCredential, credential);
```

**修改后**:
```objc
if ([challenge.protectionSpace.authenticationMethod isEqualToString:NSURLAuthenticationMethodServerTrust]) {
    NSURLCredential *credential = [NSURLCredential credentialForTrust:challenge.protectionSpace.serverTrust];
    completionHandler(NSURLSessionAuthChallengeUseCredential, credential);
} else {
    completionHandler(NSURLSessionAuthChallengePerformDefaultHandling, nil);
}
```

**原因**: iOS 26 对 SSL 证书验证有更严格的要求，需要检查认证方法类型

### 3. 后台任务支持 (第 157-163 行)
**新增**:
```objc
__block UIBackgroundTaskIdentifier bgTask = UIBackgroundTaskInvalid;
bgTask = [[UIApplication sharedApplication] beginBackgroundTaskWithExpirationHandler:^{
    [[UIApplication sharedApplication] endBackgroundTask:bgTask];
    bgTask = UIBackgroundTaskInvalid;
}];
```

**原因**: iOS 26 对后台执行有更严格的限制，需要显式声明后台任务

### 4. NSURLSession 配置增强 (第 169-175 行)
**新增**:
```objc
if (@available(iOS 13.0, *)) {
    config.TLSMinimumSupportedProtocolVersion = kTLSProtocol1;
}
config.HTTPShouldUsePipelining = YES;
config.requestCachePolicy = NSURLRequestReloadIgnoringLocalCacheData;
```

**原因**: 显式配置 TLS 和网络设置，确保 iOS 26 兼容性

### 5. 用户代理更新
**修改前**: `FlagReporter/1.0`
**修改后**: `FlagReporter/2.0-iOS26`

**原因**: 标识 iOS 26 兼容版本

## 使用方法

### 编译 iOS 26 兼容版本

```bash
# 在 macOS 上
cd /path/to/flag_report_dlib

# 使用新代码编译
clang -shared -fobjc-arc \
    -target arm64-apple-ios13.0 \
    -isysroot "$(xcrun --sdk iphoneos --show-sdk-path)" \
    -framework Foundation \
    -framework UIKit \
    -framework Security \
    -O2 \
    -o FlagReporter_ios26.dylib \
    FlagReporter_ios26.m
```

### 使用 GitHub Actions

推送代码后，GitHub Actions 会自动编译两个版本：
- `FlagReporter-dylib-standard` - 标准版本
- `FlagReporter-dylib-ios26` - iOS 26 兼容版本

### 重新打包 IPA

```bash
# 1. 替换 dylib
cp FlagReporter_ios26.dylib /www/wwwroot/chain2/backend_c2/flag_report_dlib/FlagReporter.dylib

# 2. 重新打包
python3 repackage_ipa.py input.ipa output_ios26.ipa

# 3. 企业签名（确保对所有 Frameworks 签名）
```

## 兼容性

| iOS 版本 | Standard 版本 | iOS 26 兼容版本 |
|---------|--------------|----------------|
| iOS 13-17 | ✅ 支持 | ✅ 支持 |
| iOS 18 | ✅ 支持 | ✅ 支持 |
| iOS 26+ | ❌ 可能崩溃 | ✅ 支持 |

## 建议

- **iOS 18 及以下设备**: 使用 Standard 版本
- **iOS 26+ 设备**: 使用 iOS 26 兼容版本
- **通用部署**: 使用 iOS 26 兼容版本（向下兼容）

## 注意事项

1. **企业签名**: 必须对所有 Frameworks 中的 dylib 进行签名
2. **Entitlements**: 确保保留原有的权限声明
3. **测试**: 在目标设备上测试后再大规模部署
