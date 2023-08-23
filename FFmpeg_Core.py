# FFmpeg_Core_Single
import subprocess
import shlex
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor
# {
#     "seg_key": {
#         "running": 1, -> -1:错误,0:等待 1:运行,2:完成
#         "out": "", -> ffmpeg输出
#         "progress": 1 -> ffmpeg分割百分比 (e.g. : 0.03)
#         ...
#     },
#     ...
# }
Progress = {}
threadPool = ThreadPoolExecutor(max_workers=1)


def Segment(Start_Time: int, End_Time: int, Url: str, Save_Name: str, seg_key: str, Args: str = "", download_path: str = "./"):
    global Progress
    Progress[seg_key]["running"] = 1  # 正在运行此任务
    Progress[seg_key]["progress"] = -1  # 正在解析
    Progress[seg_key]["Save_Name"] = shlex.quote(Save_Name)  # 防止文件名导致不安全注入
    Progress[seg_key]["out"] = ""
    fullpath = os.path.abspath(os.path.join(
        download_path, "Video", f"{seg_key}.mp4"))
    cmd = f'ffmpeg -progress "./Log/{seg_key}.log" {Args} -i "{Url}" -to {End_Time} -avoid_negative_ts 1 -c copy "{fullpath}" -y 2>&1' if Start_Time == 0 else f'ffmpeg -progress "./Log/{seg_key}.log" {Args} -ss {Start_Time} -i "{Url}" -to {End_Time-Start_Time}  -avoid_negative_ts 1  -c copy "{fullpath}" -y 2>&1'
    # Run Commands
    try:
        evaule_command(cmd, seg_key, End_Time-Start_Time)
        Progress[seg_key]["running"] = 2  # 执行完成
        Progress[seg_key]["progress"] = 1.00
    except Exception as Error:
        print(Error)
        Progress[seg_key]["running"] = -1  # 执行失败

    # print(Progress)
    return seg_key


def evaule_command(Command: str, seg_key: str, Duration: int):
    global Progress

    def parse_file(file_path):
        data = {}
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()  # 去掉两端的空白字符
                if "=" in line:     # 使用"="分割键和值
                    key, value = line.split("=", 1)
                    data[key] = value
        return data

    p = subprocess.Popen(Command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True, encoding="utf-8")
    while p.poll() is None:
        # print("Inside main loop")
        time.sleep(0.5)
        # print(Progress)
        ###### 分割中的操作 ######

        # 记录ffmpeg最新输出(包含时间信息)
        if os.path.exists(f"./Log/{seg_key}.log"):
            data = parse_file(f"./Log/{seg_key}.log")

            out = json.loads(json.dumps(data))
            Progress[seg_key]["out"] = out
            # print(out)

            if "out_time" in out:
                Progress[seg_key]["progress"] = to_seconds_time(
                    out['out_time'])/Duration  # 提取进度

    if os.path.exists(f"./Log/{seg_key}.log"):
        os.remove(f"./Log/{seg_key}.log")    # 清理大师


def to_seconds_time(a: str) -> int:
    if a.count(":") == 1:
        return int(float(a.split(":")[0]))*60+int(float(a.split(":")[1]))
    if a.count(":") == 2:
        return int(float(a.split(":")[0]))*3600+int(float(a.split(":")[1]))*60+int(float(a.split(":")[2]))
    return int(a)


def check_storage(filepath: os.PathLike = "./"):
    for i in os.listdir(filepath):
        if i.endswith(".mp4"):
            os.remove(os.path.join(filepath, i))
