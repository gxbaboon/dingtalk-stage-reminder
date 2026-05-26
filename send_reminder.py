#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉巡检提醒推送脚本 v2
- 读取 schedule.json 判断今日是否有演出
- TYPE=morning → 08:30 巡检提醒（有演出每日发，无演出每3天发）
- TYPE=evening → 17:50 演出前提醒（仅演出日发送）
- memory.log 由 workflow 步骤自动 commit push 回仓库
"""

import os, json, sys, urllib.request
from datetime import datetime, timedelta

WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=5426a81fa24bcbe3bfa8f9c595932eb3539fff90adf38a1c61cd01d371d8477a"
SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.json")
MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.log")


def send_dingtalk(content):
    """发送钉钉消息"""
    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"title": "技术部巡检提醒", "text": content}
    }).encode("utf-8")
    req = urllib.request.Request(WEBHOOK, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"  钉钉响应: {result}")
            return result.get("errcode") == 0
    except Exception as e:
        print(f"  发送失败: {e}")
        return False


def get_today_schedule():
    """读取今日是否为演出日"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        is_show = data.get("schedule", {}).get(today, False)
        print(f"  日程查询: {today} -> {'演出日' if is_show else '无演出'}")
        return is_show
    except Exception as e:
        print(f"  读取日程失败: {e}")
        return False


def read_memory():
    """读取上次推送日期"""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            print(f"  上次推送: {content or '(空/首次)'}")
            return content
    except FileNotFoundError:
        print(f"  上次推送: (空/首次)")
        return ""


def write_memory(date_str):
    """记录本次推送日期到 memory.log（由 workflow 自动 commit push）"""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        f.write(date_str)
    print(f"  已记录日期: {date_str}")


def should_send_regular_check():
    """无演出时判断距上次发送是否满3天"""
    last = read_memory()
    if not last:
        return True
    try:
        last_date = datetime.strptime(last, "%Y-%m-%d")
        days_since = (datetime.now() - last_date).days
        print(f"  距上次推送: {days_since} 天 (阈值3天) => {'发送' if days_since >= 3 else '跳过'}")
        return days_since >= 3
    except Exception as e:
        print(f"  日期解析异常: {e}, 默认发送")
        return True


def build_morning_message(is_show_day):
    today = datetime.now().strftime("%Y-%m-%d")
    label = "🎭 演出日巡检" if is_show_day else "📋 定期巡检"
    return f"""## {label}

**日期：** {today}
**类型：** {'演出日 - 完整巡检清单' if is_show_day else '非演出日 - 定期巡检（每3天一次）'}

---

### 💡 灯光专业（含舞台临时接电）
1. 检查舞台灯具工作状态
2. 检查调光台及信号线路
3. 检查灯具固定及安全链
4. 检查硅路负载均衡
5. 检查备用灯具及耗材
6. 检查控制网络连通性
7. 检查舞台临时接电状况
8. 检查主备系统状态
9. 填写灯光运行日志

### 🔊 音响专业
1. 检查主扩声系统状态
2. 检查调音台及信号处理设备
3. 检查话筒及无线系统
4. 检查功放及音箱状态
5. 检查音频线路及接头
6. 测试备用系统切换
7. 检查主备系统状态
8. 填写音响运行日志

### ⚙️ 机械专业
1. 按照演出流程顺序，测试演出机械系统程序（CUE表）
2. 检查升降台运行状态
3. 检查钢丝绳及滑轮系统
4. 检查限位开关及安全装置
5. 检查控制系统及急停功能
6. 检查轨道及传动系统
7. 检查载荷及平衡状态
8. 检查主备系统状态
9. 填写机械运行日志

---
**请各专业人员完成巡检后回复 ✅ 确认**"""


def build_evening_message():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""## ⏰ 演出前确认提醒

**今日演出日期：** {today}
**提醒时间：** 17:50

---

💡 **灯光岗位**
- 检查灯具线路发热情况，排除过热隐患
- 确认场灯、工作灯、字幕机工作状态正常

🔊 **音响岗位**
- 主备系统全面检查，确保切换正常
- 完成前台、后台广播系统测试

⚙️ **机械岗位**
- 按演出流程核对机械系统程序（CUE表）
- 确认所有设备安全装置到位

🎬 **舞台监督**
- 确认各岗位人员到岗情况
- 核对当日演出流程及特殊注意事项
- 组织召开班前会，统一演出指令

---
**请各岗位确认完毕后回复 ✅**"""


def main():
    msg_type = os.environ.get("TYPE", "morning")
    today = datetime.now().strftime("%Y-%m-%d")
    is_show_day = get_today_schedule()

    print(f"[{today}] 类型={msg_type}, 演出日={'✓' if is_show_day else '✗'}")

    if msg_type == "morning":
        # === 08:30 巡检提醒 ===
        if is_show_day:
            print("→ 演出日，发送完整巡检清单")
            ok = send_dingtalk(build_morning_message(True))
            if ok:
                write_memory(today)
        else:
            if should_send_regular_check():
                print("→ 非演出日，满3天周期，发送定期巡检")
                ok = send_dingtalk(build_morning_message(False))
                if ok:
                    write_memory(today)
            else:
                print("→ 非演出日，未满3天，跳过")

    elif msg_type == "evening":
        # === 17:50 演出前提醒（仅演出日）===
        if is_show_day:
            print("→ 演出日，发送演出前提醒")
            send_dingtalk(build_evening_message())
        else:
            print("→ 非演出日，跳过演出前提醒")

    print("=== 执行完毕 ===")


if __name__ == "__main__":
    main()
