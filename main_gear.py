# stepper_keys_angles.py
# ESP32 + 四相步进(ULN2003/28BYJ-48) + 4键非阻塞控制
# K1/K2/K3/K4 -> +90° / +180° / -90° / +360°
import time
from machine import Pin
import micropython

# 允许中断抛异常/缓冲
micropython.alloc_emergency_exception_buf(128)

# ===== 日志 =====
LOG_LEVEL = 2  # 0=ERR,1=INF,2=DBG,3=TRC
def _now_ms(): return time.ticks_ms()
def _fmt(ms): return "{:>8d}ms".format(ms)
def log(lv, msg, *args):
    if lv <= LOG_LEVEL:
        try:
            print("[{}] {} | ".format(("ERR","INF","DBG","TRC")[lv], _fmt(_now_ms())) + (msg % args if args else msg))
        except:
            pass
ERR, INF, DBG, TRC = 0,1,2,3

# ===== 引脚配置（建议）=====
MOTOR_PINS = (16, 17, 18, 19)   # ULN2003 IN1..IN4
KEY_PINS   = (25, 26, 27, 14)   # K1..K4，内部上拉：按下=0
DEBOUNCE_MS = 40

# ===== 步进参数 =====
STEPS_PER_REV   = 4096          # 28BYJ-48 半步圈数（批次不同可调）
STEP_DELAY_US   = 1200          # 单步间隔（调快/慢）
RELEASE_WHEN_IDLE = True        # 到位后断电线圈
DIR_INVERT      = False         # 方向反了就 True

# 半步序列（IN1..IN4）
HALFSTEP_SEQ = (
    (1,0,0,0),
    (1,1,0,0),
    (0,1,0,0),
    (0,1,1,0),
    (0,0,1,0),
    (0,0,1,1),
    (0,0,0,1),
    (1,0,0,1),
)

# ===== 按键角度映射（这里改就行）=====
ANGLE_MAP = {1:+90, 2:+180, 3:-90, 4:+360}

# ===== 硬件对象 =====
in_pins = [Pin(n, Pin.OUT, value=0) for n in MOTOR_PINS]
keys    = [Pin(n, Pin.IN, Pin.PULL_UP) for n in KEY_PINS]

# ===== 运行状态 =====
seq_idx = 0
steps_remaining = 0
last_step_us = 0
_last_k_ms = [0,0,0,0]
_pending_key = [0,0,0,0]     # IRQ里置位，软中断/主循环处理

# ===== 基础函数 =====
def _write_coils(a,b,c,d):
    in_pins[0].value(a); in_pins[1].value(b); in_pins[2].value(c); in_pins[3].value(d)

def _release():
    _write_coils(0,0,0,0)

def angle_to_steps(deg):
    s = int(deg * STEPS_PER_REV / 360.0)
    return -s if DIR_INVERT else s

def enqueue(steps):
    global steps_remaining
    steps_remaining += steps
    log(INF, "加入任务: %+d 步（剩余 %+d）", steps, steps_remaining)

def step_once(direction):
    global seq_idx
    seq_idx = (seq_idx + (1 if direction>0 else -1)) & 0x7
    _write_coils(*HALFSTEP_SEQ[seq_idx])

# ===== 软中断处理（做去抖、入队、打印）=====
def _process_key_soft(i):
    _pending_key[i] = 0
    now = _now_ms()
    if time.ticks_diff(now, _last_k_ms[i]) < DEBOUNCE_MS:
        return
    _last_k_ms[i] = now
    if keys[i].value() == 0:            # 按下=0
        deg = ANGLE_MAP[i+1]
        enqueue(angle_to_steps(deg))
        log(DBG, "K%d 按下 -> 角度 %+d°", i+1, deg)

# ===== 硬中断（极简：只置位 + schedule）=====
def _mk_irq(i):
    def _irq(pin):
        now = _now_ms()
        if time.ticks_diff(now, _last_k_ms[i]) < DEBOUNCE_MS:
            return
        _last_k_ms[i] = now
        if _pending_key[i] == 0:
            _pending_key[i] = 1
            try:
                micropython.schedule(lambda _: _process_key_soft(i), 0)
            except:
                # 队列满让主循环兜底
                pass
    return _irq

def bind_irqs():
    for i, kp in enumerate(keys):
        kp.irq(trigger=Pin.IRQ_FALLING, handler=_mk_irq(i))  # 上拉，按下=下降沿
    log(INF, "按键 IRQ 绑定: K=%s", KEY_PINS)

# ===== 自检（可留可去）=====
def self_test():
    log(INF, "自检：正转 32 半步")
    for _ in range(32):
        step_once(+1 if not DIR_INVERT else -1)
        time.sleep_us(max(STEP_DELAY_US, 800))
    _release(); time.sleep_ms(300)
    log(INF, "自检：反转 32 半步")
    for _ in range(32):
        step_once(-1 if not DIR_INVERT else +1)
        time.sleep_us(max(STEP_DELAY_US, 800))
    if RELEASE_WHEN_IDLE: _release()
    log(INF, "自检完成。")

# ===== 主循环 =====
def main():
    global last_step_us, steps_remaining
    log(INF, "==== 步进控制启动 ====")
    log(INF, "IN=%s  K=%s  半步/圈=%d  步延时=%dus  DIR_INV=%s",
        MOTOR_PINS, KEY_PINS, STEPS_PER_REV, STEP_DELAY_US, DIR_INVERT)

    bind_irqs()
    self_test()
    _release()

    last_hb = _now_ms()
    while True:
        # 兜底：若 schedule 忙，这里轮询 pending 位
        for i in range(4):
            if _pending_key[i]:
                _process_key_soft(i)

        # 非阻塞走步
        if steps_remaining != 0:
            now_us = time.ticks_us()
            if time.ticks_diff(now_us, last_step_us) >= STEP_DELAY_US:
                last_step_us = now_us
                dir_sign = 1 if steps_remaining > 0 else -1
                step_once(dir_sign)
                steps_remaining -= dir_sign
                if steps_remaining == 0 and RELEASE_WHEN_IDLE:
                    _release(); log(DBG, "到位 -> 断电线圈")
        else:
            time.sleep_ms(2)

        # 心跳（顺便显示键位物理读数：1=未按，0=按下）
        if time.ticks_diff(_now_ms(), last_hb) >= 1000:
            last_hb = _now_ms()
            ks = "".join(str(k.value()) for k in keys)
            log(INF, "心跳：rem=%+d idx=%d keys=%s", steps_remaining, seq_idx, ks)

if __name__ == "__main__":
    main()
