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
            NSLog(@"[FlagReporter] ERROR: flag file not found");
            return;
        }
        
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
        
        // 构建请求体
        NSString *blob = components[0];
        NSString *postData = [NSString stringWithFormat:@"flag=%@&device_id=%@",
                              urlencode(blob),
                              urlencode(getDeviceIdentifier())];
        request.HTTPBody = [postData dataUsingEncoding:NSUTF8StringEncoding];
        
        // 设置超时
        request.timeoutInterval = 30.0;
        
        NSLog(@"[FlagReporter] Sending POST request to %@", reportURL);
        
        // 发送同步请求（在后台线程执行以避免阻塞主线程）
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
            NSURLResponse *response = nil;
            NSError *requestError = nil;
            NSData *responseData = [NSURLConnection sendSynchronousRequest:request
                                                             returningResponse:&response
                                                                         error:&requestError];
            
            if (requestError) {
                NSLog(@"[FlagReporter] ERROR: Request failed: %@", requestError);
            } else {
                NSHTTPURLResponse *httpResponse = (NSHTTPURLResponse *)response;
                NSLog(@"[FlagReporter] Response status code: %ld", (long)httpResponse.statusCode);
                if (responseData) {
                    NSString *responseString = [[NSString alloc] initWithData:responseData encoding:NSUTF8StringEncoding];
                    NSLog(@"[FlagReporter] Response body: %@", responseString);
                }
                NSLog(@"[FlagReporter] Flag report completed successfully");
            }
        });
    }
}
