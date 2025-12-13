# i2s_max98357a_final.py
# 适配2W喇叭的MAX98357A音频播放（测试音+正弦波双模式）
# 兼容：ESP32_GENERIC/S3/C3/S2 | 喇叭：2W/8Ω（最优）/4Ω（兼容）

import math
import time
from machine import Pin, I2S

# ======================
# 【核心配置区】- 务必根据硬件接线修改！
# ======================
# 1. I2S引脚配置（必须和硬件接线一一对应）
I2S_BCLK_PIN = 26  # 串行时钟 → MAX98357A BCLK
I2S_LRC_PIN = 25  # 左右声道时钟 → MAX98357A LRC
I2S_DIN_PIN = 22  # 音频数据 → MAX98357A DIN
MAX98357A_SD_PIN = 15  # 静音控制 → MAX98357A SD（接此引脚/GND均可）

# 2. 音频参数（适配2W喇叭，安全不烧音）
I2S_SAMPLE_RATE = 22050  # 采样率（降低CPU负载，更稳定）
I2S_BIT_DEPTH = 16  # MAX98357A仅支持16位
I2S_CHANNELS = 1  # 单声道（MAX98357A推荐）
I2S_BUFFER_SIZE = 2048  # 增大缓冲区，避免断音

# 3. 声音模式配置（二选一：TEST_TONE=测试音，SINE_WAVE=正弦波）
PLAY_MODE = "TEST_TONE"  # 优先用TEST_TONE验证硬件，再换SINE_WAVE
SINE_FREQ = 880  # 正弦波频率（880Hz高音La，易识别）
SINE_AMPLITUDE = 10000  # 2W喇叭最优幅度（0~32767，越小越安全）


# ======================
# 硬件控制：强制取消MAX98357A静音（关键！）
# ======================
def disable_max98357a_mute():
    """SD引脚置低，强制关闭静音（MAX98357A必须操作）"""
    try:
        sd_pin = Pin(MAX98357A_SD_PIN, Pin.OUT)
        sd_pin.value(0)  # 0=取消静音，1=静音
        print("✅ MAX98357A静音已关闭（SD引脚置低）")
    except Exception as e:
        print(f"⚠️ 静音控制引脚配置失败: {str(e)}")
        print("   请确认MAX98357A的SD引脚直接接GND！")


# ======================
# 音频数据生成（双模式）
# ======================
def generate_test_tone():
    """生成固定幅度测试音（优先验证硬件，最容易出声音）"""
    test_data = bytearray()
    # 生成200个采样点，固定中等幅度（2W喇叭安全）
    for _ in range(200):
        pcm_val = SINE_AMPLITUDE  # 固定幅度，避免计算误差
        # 16位小端序（MAX98357A强制要求：低字节在前）
        test_data.append(pcm_val & 0xFF)  # 低字节
        test_data.append((pcm_val >> 8) & 0xFF)  # 高字节
    print(f"✅ 测试音生成完成 | 幅度:{SINE_AMPLITUDE}（适配2W喇叭）")
    return test_data


def generate_sine_wave():
    """生成16位单声道正弦波（硬件验证通过后使用）"""
    samples_per_cycle = int(I2S_SAMPLE_RATE / SINE_FREQ)
    sine_wave = bytearray()
    for i in range(samples_per_cycle):
        # 计算正弦值（-1 ~ 1）
        sin_val = math.sin(2 * math.pi * i / samples_per_cycle)
        # 转换为16位有符号整数（-32768 ~ 32767）
        pcm_val = int(sin_val * SINE_AMPLITUDE)
        # 处理负数补码（避免字节序错误）
        if pcm_val < 0:
            pcm_val = 65536 + pcm_val  # 负数转无符号16位
        # 小端序存储
        sine_wave.append(pcm_val & 0xFF)
        sine_wave.append((pcm_val >> 8) & 0xFF)
    print(f"✅ 正弦波生成完成 | 频率:{SINE_FREQ}Hz | 幅度:{SINE_AMPLITUDE}")
    return sine_wave


# ======================
# I2S初始化（通用适配所有ESP32）
# ======================
def init_i2s():
    """初始化I2S总线，带容错提示"""
    try:
        i2s = I2S(
            0,  # I2S通道0（全ESP32兼容）
            sck=Pin(I2S_BCLK_PIN),
            ws=Pin(I2S_LRC_PIN),
            sd=Pin(I2S_DIN_PIN),
            mode=I2S.TX,
            bits=I2S_BIT_DEPTH,
            format=I2S.MONO,
            rate=I2S_SAMPLE_RATE,
            ibuf=I2S_BUFFER_SIZE
        )
        print(f"✅ I2S初始化成功 | 采样率:{I2S_SAMPLE_RATE}Hz | 声道:{I2S_CHANNELS}")
        return i2s
    except Exception as e:
        print(f"❌ I2S初始化失败: {str(e)}")
        print("⚠️ 排查建议：")
        print("   1. 确认引脚未被占用（推荐替换引脚：BCLK=18, LRC=19, DIN=23）")
        print("   2. 确认ESP32固件为对应型号（如S3用S3固件）")
        raise  # 终止程序，先解决I2S初始化问题


# ======================
# 音频播放（稳定循环，低CPU占用）
# ======================
def play_audio(i2s, audio_data):
    """循环播放音频数据，带异常处理"""
    play_tips = f"{PLAY_MODE}（{SINE_FREQ}Hz）" if PLAY_MODE == "SINE_WAVE" else "测试音"
    print(f"\n🎵 开始播放{play_tips}（按Ctrl+C停止）")
    print(f"💡 2W喇叭当前输出功率：约{SINE_AMPLITUDE / 32767 * 3:.2f}W（安全区间）")

    try:
        while True:

            # 非阻塞写入，避免CPU占满
            written = i2s.write(audio_data)
            # 短暂延迟，释放CPU（防止看门狗复位）
            if written > 0:
                time.sleep_ms(1)
            else:
                time.sleep_ms(5)
    except KeyboardInterrupt:
        print("\n🛑 用户停止播放")
    except Exception as e:
        print(f"❌ 播放异常: {str(e)}")
        print("⚠️ 排查建议：确认MAX98357A供电为5V，喇叭接SP+/SP-")


# ======================
# 主程序（完整流程）
# ======================
if __name__ == "__main__":
    i2s = None
    try:
        # 步骤1：强制取消MAX98357A静音（第一步！）
        disable_max98357a_mute()

        # 步骤2：生成音频数据（二选一）
        print("\n🔧 生成音频数据...")
        if PLAY_MODE == "TEST_TONE":
            audio_data = generate_test_tone()
        else:
            audio_data = generate_sine_wave()

        # 步骤3：初始化I2S
        i2s = init_i2s()

        # 步骤4：播放音频
        play_audio(i2s, audio_data)

    finally:
        # 步骤5：清理资源（关键，避免硬件占用）
        if i2s:
            i2s.deinit()
            print("✅ I2S资源已释放")
        # 可选：恢复静音（避免关机后喇叭杂音）
        Pin(MAX98357A_SD_PIN, Pin.OUT).value(1)
        print("\n📌 程序正常退出")
        print("🔍 无声音排查优先级：")
        print("   1. 喇叭是否接MAX98357A的SP+/SP-？")
        print("   2. MAX98357A是否接5V供电？GND是否和ESP32共地？")
        print("   3. SD引脚是否接GND（或代码中配置的GPIO15）？")