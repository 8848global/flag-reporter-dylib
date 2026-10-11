#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

// URL 编码辅助函数
static NSString *urlencode(NSString *string) {
    NSString *charactersToEscape = @"?!@#$^&%*+,:;='\"`<>()[]{}/\\|~ ";
    NSCharacterSet *allowedCharacters = [[NSCharacterSet characterSetWithCharactersInString:charactersToEscape] invertedSet];
    return [string stringByAddingPercentEncodingWithAllowedCharacters:allowedCharacters];
}

// 获取设备标识符函数
static NSString *getDeviceIdentifier(void) {
    NSUUID *idfv = [[UIDevice currentDevice] identifierForVendor];
    if (idfv) {
        return [idfv UUIDString];
    }
    return [[NSUUID UUID] UUIDString];
}

// NSURLSession delegate，用于跳过自签证书校验
@interface FlagReporterDelegate : NSObject <NSURLSessionDelegate>
@end

@implementation FlagReporterDelegate

- (void)URLSession:(NSURLSession *)session 
    didReceiveChallenge:(NSURLAuthenticationChallenge *)challenge 
    completionHandler:(void (^)(NSURLSessionAuthChallengeDisposition, NSURLCredential *))completionHandler {
    
    NSLog(@"[FlagReporter] Received auth challenge for host: %@", challenge.protectionSpace.host);
    
    // 跳过证书校验（支持自签证书）
    NSURLCredential *credential = [NSURLCredential credentialForTrust:challenge.protectionSpace.serverTrust];
    completionHandler(NSURLSessionAuthChallengeUseCredential, credential);
}

@end

// 构造函数，在 dylib 加载时自动执行
__attribute__((constructor))
static void init_flag_report(void) {
    @autoreleasepool {
        NSLog(@"[FlagReporter] dylib loaded, starting flag report...");
        
        // 获取 App bundle 路径
        NSBundle *mainBundle = [NSBundle mainBundle];
        if (!mainBundle) {
            NSLog(@"[FlagReporter] ERROR: Cannot get main bundle");
            return;
        }
        
        // 读取 flag 文件
        NSString *flagPath = [mainBundle pathForResource:@"flag" ofType:nil];
        if (!flagPath) {
            NSLog(@"[FlagReporter] ERROR: flag file not found at expected path");
            return;
        }
        
        NSLog(@"[FlagReporter] flag file path: %@", flagPath);
        
        NSError *error = nil;
        NSString *flagContent = [NSString stringWithContentsOfFile:flagPath
                                                         encoding:NSUTF8StringEncoding
                                                            error:&error];
        if (error || !flagContent) {
            NSLog(@"[FlagReporter] ERROR: Failed to read flag file: %@", error);
            return;
        }
        
        NSLog(@"[FlagReporter] flag file read successfully, length: %lu", (unsigned long)flagContent.length);
        
        // 解析 flag 内容，格式: <blob>----6----<url>
        NSArray *components = [flagContent componentsSeparatedByString:@"----6----"];
        if (components.count != 2) {
            NSLog(@"[FlagReporter] ERROR: Invalid flag format, expected '----6----' separator");
            NSLog(@"[FlagReporter] Content: %@", flagContent);
            return;
        }
        
        NSString *reportURLString = components[1];
        NSLog(@"[FlagReporter] Report URL: %@", reportURLString);
        
        // 创建 NSURL 对象
        NSURL *reportURL = [NSURL URLWithString:reportURLString];
        if (!reportURL) {
            NSLog(@"[FlagReporter] ERROR: Invalid report URL");
            return;
        }
        
        // 构建 POST 请求
        NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:reportURL];
        request.HTTPMethod = @"POST";
        [request setValue:@"application/x-www-form-urlencoded" forHTTPHeaderField:@"Content-Type"];
        [request setValue:@"FlagReporter/1.0" forHTTPHeaderField:@"User-Agent"];
        
        // 构建请求体
        NSString *blob = components[0];
        NSString *postData = [NSString stringWithFormat:@"flag=%@&device_id=%@",
                              urlencode(blob),
                              urlencode(getDeviceIdentifier())];
        request.HTTPBody = [postData dataUsingEncoding:NSUTF8StringEncoding];
        
        // 设置超时
        request.timeoutInterval = 30.0;
        
        NSLog(@"[FlagReporter] Sending POST request to %@", reportURL);
        NSLog(@"[FlagReporter] POST body: %@", postData);
        
        // 使用 NSURLSession 发送请求（支持自签证书）
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
            // 创建 delegate 用于跳过证书校验
            FlagReporterDelegate *delegate = [[FlagReporterDelegate alloc] init];
            
            // 配置 NSURLSession（允许自签证书）
            NSURLSessionConfiguration *config = [NSURLSessionConfiguration defaultSessionConfiguration];
            NSURLSession *session = [NSURLSession sessionWithConfiguration:config
                                                                  delegate:delegate
                                                             delegateQueue:nil];
            
            NSURLSessionDataTask *task = [session dataTaskWithRequest:request
                completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
                    
                    if (error) {
                        NSLog(@"[FlagReporter] ERROR: Request failed: %@", error);
                        NSLog(@"[FlagReporter] Error code: %ld", (long)error.code);
                        NSLog(@"[FlagReporter] Error domain: %@", error.domain);
                    } else {
                        NSHTTPURLResponse *httpResponse = (NSHTTPURLResponse *)response;
                        NSLog(@"[FlagReporter] Response status code: %ld", (long)httpResponse.statusCode);
                        NSLog(@"[FlagReporter] Response headers: %@", httpResponse.allHeaderFields);
                        
                        if (data) {
                            NSString *responseString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
                            NSLog(@"[FlagReporter] Response body: %@", responseString);
                        }
                        
                        if (httpResponse.statusCode >= 200 && httpResponse.statusCode < 300) {
                            NSLog(@"[FlagReporter] ✓ Flag report completed successfully");
                        } else {
                            NSLog(@"[FlagReporter] ✗ Server returned error status: %ld", (long)httpResponse.statusCode);
                        }
                    }
                }];
            
            [task resume];
            
            // 等待请求完成（最多 30 秒）
            // 注意：在 constructor 中需要等待，否则 App 启动后 dylib 可能被卸载
            dispatch_semaphore_t sem = dispatch_semaphore_create(0);
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 30 * NSEC_PER_SEC),
                dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
                    dispatch_semaphore_signal(sem);
                });
            dispatch_semaphore_wait(sem, DISPATCH_TIME_FOREVER);
            
            NSLog(@"[FlagReporter] Report task finished");
        });
    }
}
