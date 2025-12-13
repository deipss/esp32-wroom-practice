# servo_console_debug.py
# ESP32 控制台调试360度舵机

import time
from machine import Pin, PWM
from base.log import debug, info, warn

# ======================
# 配置360度舵机参数
# ======================
SERVO_PIN = 27          # 舵机 PWM 引脚
FREQ = 50               # 舵机固定频率 50Hz

# 360度舵机脉宽参数（需要根据实际舵机调试）
STOP_US = 1500          # 停止脉宽 1.5ms（中间位置）
CCW_MAX_US = 1000       # 逆时针最大速度脉宽 1.0ms
CW_MAX_US = 2000        # 顺时针最大速度脉宽 2.0ms

# ESP32 PWM 通道：duty范围 0~1023
PWM_MAX = 1023

# 速度档位 (-100 到 100)
# 负数：逆时针，正数：顺时针，0：停止
SPEED_LEVELS = [-100, -75, -50, -25, 0, 25, 50, 75, 100]

# 角度控制参数
ANGLE_SPEED = 50          # 用于角度控制的旋转速度 (%)
MAX_ROTATION_TIME = 3.0   # 最大旋转时间（秒）

# ======================
# 舵机初始化
# ======================
servo = PWM(Pin(SERVO_PIN), freq=FREQ, duty=0)
info("SERVO", "舵机已初始化: pin=%d freq=%dHz", SERVO_PIN, FREQ)

# ======================
# 工具函数：速度转 duty
# ======================
def speed_to_duty(speed):
    """
    速度转换为PWM duty
    speed: -100 到 100 (-100:逆时针最大速度, 0:停止, 100:顺时针最大速度)
    """
    speed = max(-100, min(100, speed))

    if speed == 0:
        us = STOP_US
        direction = "停止"
    elif speed > 0:
        # 顺时针
        us = STOP_US + (CW_MAX_US - STOP_US) * speed / 100
        direction = "顺时针"
    else:
        # 逆时针
        us = STOP_US - (STOP_US - CCW_MAX_US) * abs(speed) / 100
        direction = "逆时针"

    duty = int(PWM_MAX * us / 20000)  # 20ms = 20000us
    debug("CALC", "速度=%d%% -> us=%d -> duty=%d (%s)", speed, us, duty, direction)
    return duty

# ======================
# 设置360度舵机速度
# ======================
def servo_speed(speed):
    """设置360度舵机速度"""
    duty = speed_to_duty(speed)
    servo.duty(duty)

    if speed == 0:
        info("SERVO", "舵机停止 duty=%d", duty)
    elif speed > 0:
        info("SERVO", "舵机顺时针旋转 速度=%d%% duty=%d", speed, duty)
    else:
        info("SERVO", "舵机逆时针旋转 速度=%d%% duty=%d", abs(speed), duty)

def servo_stop():
    """停止舵机"""
    servo_speed(0)

# ======================
# 角度控制功能
# ======================
def servo_rotate_angle(target_angle, speed=ANGLE_SPEED):
    """
    旋转指定角度
    target_angle: 目标角度 (0-360度，正数顺时针，负数逆时针)
    speed: 旋转速度 (%)
    """
    # 归一化角度到0-360范围
    if target_angle < 0:
        target_angle = 360 + target_angle

    # 计算旋转时间 (基于经验的简单换算，需要根据实际舵机调整)
    # 假设在50%速度下，1秒旋转约120度
    degrees_per_second = 120 * (speed / 50.0)
    rotation_time = abs(target_angle) / degrees_per_second

    # 限制最大旋转时间
    rotation_time = min(rotation_time, MAX_ROTATION_TIME)

    if target_angle >= 0:
        direction = "顺时针"
        servo_speed(speed)
    else:
        direction = "逆时针"
        servo_speed(-abs(speed))

    info("ANGLE", "旋转 %d° (%s) 速度=%d%% 时间=%.1f秒",
         abs(target_angle), direction, speed, rotation_time)

    print(f"🔄 开始旋转 {abs(target_angle):.1f}° ({direction}) 速度={speed}%")

    # 旋转指定时间
    time.sleep(rotation_time)

    # 停止舵机
    servo_stop()
    print(f"⏹️ 旋转完成，舵机已停止")

def test_angle_control():
    """测试角度控制功能"""
    print("\n=== 角度控制测试 ===")
    print("舵机将进行角度旋转测试...")

    # 测试各种角度
    test_angles = [
        (90, "顺时针90度"),
        (-90, "逆时针90度"),
        (180, "顺时针180度"),
        (-180, "逆时针180度"),
        (45, "顺时针45度"),
        (-45, "逆时针45度"),
        (360, "顺时针360度"),
        (0, "停止测试")
    ]

    for angle, description in test_angles:
        if angle == 0:
            print(f"\n{description}")
            servo_stop()
        else:
            print(f"\n{description}")
            servo_rotate_angle(angle)

        time.sleep(1)

def calibrate_angle_control():
    """校准角度控制 - 通过多次旋转找到合适的比例"""
    print("\n=== 角度控制校准 ===")
    print("舵机将进行校准测试，请观察实际旋转角度...")

    # 测试不同的旋转时间和角度
    test_cases = [
        (90, 0.5),   # 90度，0.5秒
        (90, 1.0),   # 90度，1秒
        (90, 1.5),   # 90度，1.5秒
        (180, 1.0),  # 180度，1秒
        (180, 2.0),  # 180度，2秒
        (180, 3.0),  # 180度，3秒
    ]

    for angle, test_time in test_cases:
        print(f"\n🧪 测试: 旋转{angle}度，时间{test_time}秒")

        # 根据角度设置方向
        if angle >= 0:
            servo_speed(ANGLE_SPEED)
            direction = "顺时针"
        else:
            servo_speed(-ANGLE_SPEED)
            direction = "逆时针"

        print(f"   开始{direction}旋转 {test_time}秒...")
        time.sleep(test_time)
        servo_stop()

        print("   旋转完成，请观察实际角度")
        input("   按回车继续下一个测试...")

    print("\n✅ 校准测试完成!")

# ======================
# 360度舵机测试函数
# ======================
def test_directions():
    """测试方向和速度"""
    print("\n=== 方向和速度测试 ===")
    print("舵机将测试各个方向的运行...")

    print("1. 停止 (1秒)")
    servo_speed(0)
    time.sleep(1)

    print("2. 顺时针 25% 速度 (2秒)")
    servo_speed(25)
    time.sleep(2)

    print("3. 停止 (1秒)")
    servo_speed(0)
    time.sleep(1)

    print("4. 逆时针 25% 速度 (2秒)")
    servo_speed(-25)
    time.sleep(2)

    print("5. 停止")
    servo_stop()

def test_speed_levels():
    """测试不同速度档位"""
    print("\n=== 速度档位测试 ===")
    print("测试不同速度档位...")

    for speed in SPEED_LEVELS:
        print(f"速度: {speed}%")
        servo_speed(speed)
        time.sleep(1.5)

    print("测试完成，停止舵机")
    servo_stop()

def smooth_speed_test():
    """平滑速度测试"""
    print("\n=== 平滑速度测试 ===")
    print("舵机速度从-100%平滑变化到+100%...")

    # 从-100%到+100%
    for speed in range(-100, 101, 10):
        servo_speed(speed)
        print(f"\r速度: {speed}%", end="")
        time.sleep(0.2)

    print("\n到达100%，准备反向...")
    time.sleep(1)

    # 从+100%回到-100%
    for speed in range(100, -101, -10):
        servo_speed(speed)
        print(f"\r速度: {speed}%", end="")
        time.sleep(0.2)

    print("\n速度测试完成!")
    servo_stop()

def direction_timing_test():
    """方向定时测试 - 用于校准停止点"""
    print("\n=== 方向定时测试 ===")
    print("舵机会运行一段时间，观察停止点是否准确...")

    print("运行顺时针 3秒...")
    servo_speed(50)
    time.sleep(3)

    print("停止")
    servo_speed(0)
    time.sleep(1)

    print("运行逆时针 3秒...")
    servo_speed(-50)
    time.sleep(3)

    print("停止")
    servo_stop()
    print("定时测试完成!")

# ======================
# 控制菜单
# ======================
def show_menu():
    """显示控制菜单"""
    print("\n" + "="*50)
    print("🎛️ ESP32 360度舵机控制调试工具")
    print("="*50)
    print("1. 停止舵机")
    print("2. 顺时针慢速 (25%)")
    print("3. 顺时针中速 (50%)")
    print("4. 顺时针快速 (75%)")
    print("5. 逆时针慢速 (-25%)")
    print("6. 逆时针中速 (-50%)")
    print("7. 逆时针快速 (-75%)")
    print("8. 方向和速度测试")
    print("9. 速度档位测试")
    print("10. 平滑速度测试")
    print("11. 方向定时测试")
    print("12. 自定义速度")
    print("13. 旋转指定角度")
    print("14. 角度控制测试")
    print("15. 角度校准测试")
    print("0. 退出程序")
    print("="*50)

def get_user_input():
    """获取用户输入"""
    try:
        choice = input("\n请选择功能 (0-15): ").strip()
        return int(choice) if choice.isdigit() else -1
    except KeyboardInterrupt:
        return 0
    except:
        return -1

def custom_speed_input():
    """自定义速度输入"""
    try:
        speed = float(input("请输入速度 (-100 到 100): "))
        if -100 <= speed <= 100:
            servo_speed(speed)
            if speed == 0:
                print(f"✅ 舵机已停止")
            elif speed > 0:
                print(f"✅ 舵机顺时针旋转，速度={speed}%")
            else:
                print(f"✅ 舵机逆时针旋转，速度={abs(speed)}%")
        else:
            print("❌ 速度超出范围，请输入-100到100之间的数值")
    except KeyboardInterrupt:
        print("\n操作取消")
    except ValueError:
        print("❌ 输入格式错误，请输入有效数字")

def custom_angle_input():
    """自定义角度输入"""
    try:
        angle = float(input("请输入旋转角度 (-360 到 360): "))
        speed_input = input("请输入旋转速度 (默认50%): ").strip()

        if speed_input:
            speed = float(speed_input)
            if not -100 <= speed <= 100:
                print("❌ 速度超出范围，使用默认50%")
                speed = 50
        else:
            speed = 50

        if -360 <= angle <= 360:
            servo_rotate_angle(angle, speed)
        else:
            print("❌ 角度超出范围，请输入-360到360之间的数值")
    except KeyboardInterrupt:
        print("\n操作取消")
    except ValueError:
        print("❌ 输入格式错误，请输入有效数字")

# ======================
# 主程序
# ======================
def run():
    """主运行函数"""
    try:
        print("\n" + "="*50)
        print("🎯 ESP32 舵机控制台调试工具启动!")
        print(f"📌 舵机连接在GPIO {SERVO_PIN} 引脚")
        print(f"🔧 舵机频率: {FREQ}Hz")
        print("📊 360度连续旋转舵机")
        print("🔄 速度控制: -100% 到 +100%")
        print("⏹️ 中间位置 (0%): 停止")
        print("="*50 + "\n")

        # 初始测试 - 确保舵机停止
        info("INIT", "舵机初始化测试")
        print("正在初始化360度舵机...")
        servo_speed(0)  # 确保舵机停止
        time.sleep(1)
        print("✅ 360度舵机初始化完成!")

        # 主循环
        info("MAIN", "进入控制台交互模式")
        while True:
            show_menu()
            choice = get_user_input()

            if choice == 0:
                print("👋 程序退出中...")
                break
            elif choice == 1:
                servo_speed(0)
                print("✅ 舵机已停止")
            elif choice == 2:
                servo_speed(25)
                print("✅ 舵机顺时针慢速旋转 (25%)")
            elif choice == 3:
                servo_speed(50)
                print("✅ 舵机顺时针中速旋转 (50%)")
            elif choice == 4:
                servo_speed(75)
                print("✅ 舵机顺时针快速旋转 (75%)")
            elif choice == 5:
                servo_speed(-25)
                print("✅ 舵机逆时针慢速旋转 (-25%)")
            elif choice == 6:
                servo_speed(-50)
                print("✅ 舵机逆时针中速旋转 (-50%)")
            elif choice == 7:
                servo_speed(-75)
                print("✅ 舵机逆时针快速旋转 (-75%)")
            elif choice == 8:
                test_directions()
            elif choice == 9:
                test_speed_levels()
            elif choice == 10:
                smooth_speed_test()
            elif choice == 11:
                direction_timing_test()
            elif choice == 12:
                custom_speed_input()
            elif choice == 13:
                custom_angle_input()
            elif choice == 14:
                test_angle_control()
            elif choice == 15:
                calibrate_angle_control()
            else:
                print("❌ 无效选择，请输入 0-15 之间的数字")

            # 清理当前行，准备下次菜单显示
            print("\n按回车键继续...")
            try:
                input()
            except KeyboardInterrupt:
                break

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        warn("MAIN", "主程序异常: %s", str(e))
    finally:
        # 清理资源
        servo.duty(0)  # 关闭舵机信号
        print("\n🔌 舵机信号已关闭")
        info("MAIN", "程序已退出")

# ======================
# 快速测试模式
# ======================
def quick_test():
    """快速测试模式 - 直接执行一系列测试"""
    print("\n🚀 360度舵机快速测试启动!")

    print("1. 停止测试...")
    servo_speed(0)
    print("   舵机停止")

    print("\n2. 方向测试...")
    servo_speed(25)
    print("   顺时针慢速 2秒")
    time.sleep(2)

    servo_speed(-25)
    print("   逆时针慢速 2秒")
    time.sleep(2)

    servo_speed(0)
    print("   舵机停止")

    print("\n3. 速度测试...")
    for speed in [50, 100, -50, -100]:
        servo_speed(speed)
        if speed > 0:
            print(f"   顺时针 {speed}% 速度 1秒")
        elif speed < 0:
            print(f"   逆时针 {abs(speed)}% 速度 1秒")
        else:
            print(f"   舵机停止 1秒")
        time.sleep(1)

    servo_speed(0)
    time.sleep(1)

    print("\n4. 角度测试...")
    print("   旋转90度顺时针")
    servo_rotate_angle(90)
    time.sleep(1)

    print("   旋转180度逆时针")
    servo_rotate_angle(-180)

    print("\n✅ 快速测试完成!")

# ======================
# 程序入口
# ======================
if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        quick_test()
    else:
        run()