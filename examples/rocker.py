# 摇杆
import time
from machine import Pin, ADC

# 初始化模拟输入引脚
vrx = ADC(Pin(34))  # 水平输入 (VRX)
vry = ADC(Pin(35))  # 垂直输入 (VRY)

# PS2按钮开关
sw = Pin(32, Pin.IN, Pin.PULL_UP)  # SW按钮（内部上拉）

# 设置ADC的读取范围
vrx.atten(ADC.ATTN_0DB)  # 0-3.3V输入范围
vry.atten(ADC.ATTN_0DB)  # 0-3.3V输入范围

# 设置阈值，只有超过此值才认为发生了摇动
THRESHOLD = 50

# 存储之前的模拟值
last_vrx_value = -1
last_vry_value = -1

def run():
    global last_vrx_value, last_vry_value
    # 持续读取模拟值
    while True:
        # 获取水平方向（VRX）和垂直方向（VRY）的值
        vrx_value = vrx.read()  # 读取VRX的模拟值（0 - 4095）
        vry_value = vry.read()  # 读取VRY的模拟值（0 - 4095）

        # 获取按钮SW的状态
        sw_state = sw.value()  # 按钮状态：0为按下，1为未按下

        # 判断是否有摇动：如果当前值和上次值的差距大于阈值
        if abs(vrx_value - last_vrx_value) > THRESHOLD or abs(vry_value - last_vry_value) > THRESHOLD:
            # 打印输出
            print("摇动 detected:")
            print("VRX (水平):", vrx_value)
            print("VRY (垂直):", vry_value)
            print("SW 按钮状态:", "按下" if sw_state == 0 else "未按下")

            # 更新最后的值
            last_vrx_value = vrx_value
            last_vry_value = vry_value

        time.sleep(0.1)  # 每0.1秒读取一次


if __name__ == '__main__':
    run()
