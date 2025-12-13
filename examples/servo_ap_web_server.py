# servo_ap_web_server.py
# ESP32 热点 + Web服务器 控制舵机

import network
import time
import socket
from machine import Pin, PWM
from base.log import debug, info, warn

# ======================
# 配置舵机参数
# ======================
SERVO_PIN = 27          # 舵机 PWM 引脚
FREQ = 50               # 舵机固定频率 50Hz
MIN_US = 500            # 0° 脉宽 0.5ms
MAX_US = 2500           # 180° 脉宽 2.5ms


# ESP32 PWM 通道：duty范围 0~1023
PWM_MAX = 1023

# ======================
# 配置热点AP参数
# ======================
AP_SSID = "ESP32-Servo-Controller"
AP_PASSWORD = "12345678"
AP_CHANNEL = 11

# 舵机预设角度
SERVO_ANGLES = [0, 45, 90, 135]  # 4个预设角度

# ======================
# 舵机初始化
# ======================
servo = PWM(Pin(SERVO_PIN), freq=FREQ, duty=0)
info("SERVO", "舵机已初始化: pin=%d freq=%dHz", SERVO_PIN, FREQ)

# ======================
# 工具函数：角度转 duty
# ======================
def angle_to_duty(angle):
    angle = max(0, min(180, angle))
    us = MIN_US + (MAX_US - MIN_US) * angle / 180
    duty = int(PWM_MAX * us / 20000)  # 20ms = 20000us
    debug("CALC", "角度=%d° -> us=%d -> duty=%d", angle, us, duty)
    return duty

# ======================
# 设置舵机角度
# ======================
def servo_angle(angle):
    duty = angle_to_duty(angle)
    servo.duty(duty)
    info("SERVO", "设置角度=%d° duty=%d", angle, duty)
    time.sleep_ms(400)  # 舵机需要时间移动

# ======================
# 创建热点AP
# ======================
def create_ap(ssid=AP_SSID, password=AP_PASSWORD, channel=AP_CHANNEL):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password, channel=channel, authmode=network.AUTH_WPA_WPA2_PSK)

    info("AP", "热点已创建: SSID=%s Password=%s Channel=%d", ssid, password, channel)

    # 等待热点启动
    time.sleep(2)

    # 获取热点IP地址
    ip = ap.ifconfig()[0]
    info("AP", "热点IP地址: %s", ip)
    print(f"请连接热点 {ssid}，然后访问: http://{ip}")

    return ap, ip

# ======================
# HTML页面
# ======================
def get_html_page():
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 舵机控制</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .button-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 30px 0;
        }
        .servo-btn {
            padding: 20px;
            font-size: 18px;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: white;
            min-height: 60px;
        }
        .btn-0 { background-color: #ff6b6b; }
        .btn-45 { background-color: #4ecdc4; }
        .btn-90 { background-color: #45b7d1; }
        .btn-135 { background-color: #96ceb4; }

        .servo-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .servo-btn:active {
            transform: translateY(0);
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            background-color: #e8f5e8;
            border-radius: 5px;
            font-weight: bold;
            color: #2d5a2d;
        }
        .info {
            margin-top: 20px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎛️ ESP32 舵机控制面板</h1>

        <div class="button-grid">
            <button class="servo-btn btn-0" onclick="controlServo(0)">
                0°<br>最小角度
            </button>
            <button class="servo-btn btn-45" onclick="controlServo(45)">
                45°<br>小角度
            </button>
            <button class="servo-btn btn-90" onclick="controlServo(90)">
                90°<br>中间角度
            </button>
            <button class="servo-btn btn-135" onclick="controlServo(135)">
                135°<br>大角度
            </button>
        </div>

        <div class="status" id="status">
            准备就绪 - 点击按钮控制舵机
        </div>

        <div class="info">
            <p>📡 通过WiFi连接ESP32热点进行控制</p>
            <p>🔧 舵机连接在GPIO 27引脚</p>
        </div>
    </div>

    <script>
        function controlServo(angle) {
            const status = document.getElementById('status');
            status.innerHTML = `正在设置舵机角度为 ${angle}°...`;

            fetch(`/servo?angle=${angle}`)
                .then(response => response.text())
                .then(data => {
                    status.innerHTML = `✅ 舵机已设置为 ${angle}°`;
                    status.style.backgroundColor = '#d4edda';

                    // 3秒后恢复默认状态
                    setTimeout(() => {
                        status.innerHTML = '准备就绪 - 点击按钮控制舵机';
                        status.style.backgroundColor = '#e8f5e8';
                    }, 3000);
                })
                .catch(error => {
                    status.innerHTML = `❌ 控制失败: ${error}`;
                    status.style.backgroundColor = '#f8d7da';
                });
        }

        // 页面加载完成提示
        window.onload = function() {
            console.log('ESP32 舵机控制面板已加载');
        };
    </script>
</body>
</html>
    """
    return html

# ======================
# Web服务器
# ======================
def handle_client(client, request):
    """处理客户端请求"""
    try:
        # 解析请求
        first_line = request.decode('utf-8').split('\n')[0]
        url = first_line.split(' ')[1]

        debug("HTTP", "请求URL: %s", url)

        # 处理舵机控制请求
        if url.startswith('/servo?angle='):
            try:
                angle = int(url.split('=')[1])
                if angle in SERVO_ANGLES:
                    servo_angle(angle)
                    response = f"舵机角度已设置为 {angle}°"
                    info("HTTP", "舵机控制: angle=%d", angle)
                else:
                    response = f"无效角度: {angle}。支持的角度: {SERVO_ANGLES}"
                    warn("HTTP", "无效角度请求: %d", angle)
            except ValueError:
                response = "角度参数错误"
                warn("HTTP", "角度参数解析失败")

        # 处理主页请求
        elif url == '/' or url == '/index.html':
            response = get_html_page()
            info("HTTP", "返回主页内容")

        # 404页面
        else:
            response = "404 Not Found"
            warn("HTTP", "未知请求: %s", url)

        # 发送HTTP响应
        client.send('HTTP/1.1 200 OK\r\n')
        client.send('Content-Type: text/html; charset=utf-8\r\n')
        client.send(f'Content-Length: {len(response.encode("utf-8"))}\r\n')
        client.send('Access-Control-Allow-Origin: *\r\n')
        client.send('Connection: close\r\n\r\n')
        client.send(response)

    except Exception as e:
        warn("HTTP", "处理请求异常: %s", str(e))
    finally:
        client.close()

# ======================
# 启动Web服务器
# ======================
def start_web_server(port=80):
    """启动Web服务器"""
    addr = ('0.0.0.0', port)
    server = socket.socket()
    server.bind(addr)
    server.listen(1)

    info("SERVER", "Web服务器已启动: 端口=%d", port)
    print(f"Web服务器监听端口: {port}")

    return server

# ======================
# 主程序
# ======================
def run():
    """主运行函数"""
    try:
        # 1. 舵机初始化测试
        info("INIT", "开始舵机初始化测试")
        servo_angle(90)  # 设置到中间位置
        time.sleep(1)

        # 2. 创建热点AP
        info("INIT", "创建热点AP")
        ap, ip = create_ap()

        # 3. 启动Web服务器
        info("INIT", "启动Web服务器")
        server = start_web_server()

        print("\n" + "="*50)
        print("🎉 ESP32舵机控制服务器已启动!")
        print(f"📱 请连接WiFi热点: {AP_SSID}")
        print(f"🔑 WiFi密码: {AP_PASSWORD}")
        print(f"🌐 打开浏览器访问: http://{ip}")
        print("="*50 + "\n")

        # 4. 主循环处理请求
        info("MAIN", "进入主循环，等待客户端连接")
        while True:
            try:
                client, addr = server.accept()
                info("MAIN", "客户端连接: %s", str(addr))

                # 接收请求数据
                request = client.recv(1024)
                if request:
                    handle_client(client, request)

            except Exception as e:
                warn("MAIN", "处理客户端连接异常: %s", str(e))
                if 'client' in locals():
                    client.close()

    except KeyboardInterrupt:
        info("MAIN", "用户中断，正在关闭服务器...")
    except Exception as e:
        warn("MAIN", "主程序异常: %s", str(e))
    finally:
        # 清理资源
        if 'server' in locals():
            server.close()
        if 'ap' in locals():
            ap.active(False)
        servo.duty(0)  # 关闭舵机信号
        info("MAIN", "服务器已关闭")

# ======================
# 程序入口
# ======================
if __name__ == "__main__":
    run()