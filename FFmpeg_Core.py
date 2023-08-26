# FFmpeg_Core_Single
import subprocess
import shlex
import time
import os
import json
from app import check_disk_space_is_not_good
from concurrent.futures import ThreadPoolExecutor
# {
#     "seg_key": {
#         "running": 1, -> -1:错误,0:等待 1:运行,2:完成
#         "out": "", -> ffmpeg输出
#         "progress": 1, -> ffmpeg分割百分比 (e.g. : 0.03)
#         "Save_Name": "", -> 保存文件名
#         "update" : time.time(), -> 状态最后更新时间
#         ...
#     },
#     ...
# }
Progress = {}
threadPool = ThreadPoolExecutor(max_workers=1)


def Segment(Start_Time: int, End_Time: int, Url: str, Save_Name: str, seg_key: str, Args: str = "", download_path: str = "./"):
    global Progress

    # 初始化任务
    Progress[seg_key]["running"] = 1  # 正在运行此任务
    Progress[seg_key]["progress"] = -1  # 正在解析
    Progress[seg_key]["Save_Name"] = shlex.quote(Save_Name)  # 防止文件名导致不安全注入
    Progress[seg_key]["out"] = ""
    Progress[seg_key]["update"] = time.time()

    fullpath = os.path.abspath(os.path.join(
        download_path, "Video", f"{seg_key}.mp4"))
    cmd = f'ffmpeg -progress "./Log/{seg_key}.log" {Args} -i "{Url}" -to {End_Time} -avoid_negative_ts 1 -c copy "{fullpath}" -y 2>&1' if Start_Time == 0 else f'ffmpeg -progress "./Log/{seg_key}.log" {Args} -ss {Start_Time} -i "{Url}" -to {End_Time-Start_Time}  -avoid_negative_ts 1  -c copy "{fullpath}" -y 2>&1'

    # Run Commands
    try:
        evaule_command(cmd, seg_key, End_Time-Start_Time)
        Progress[seg_key]["running"] = 2  # 执行完成
        Progress[seg_key]["progress"] = 1.00
        Progress[seg_key]["update"] = time.time()
    except Exception as Error:
        print(Error)
        Progress[seg_key]["running"] = -1  # 执行失败
        Progress[seg_key]["update"] = time.time()
    return seg_key


def evaule_command(Command: str, seg_key: str, Duration: int):
    global Progress

    def parse_file(file_path):  # 读取FFMPEG输出文件生成键值对
        data = {}
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()  # 去掉两端的空白字符
                if "=" in line:     # 使用"="分割键和值
                    key, value = line.split("=", 1)
                    data[key] = value
        return data

    p = subprocess.Popen(Command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True, encoding="utf-8", )
    while p.poll() is None:  # 循环提取FFMPEG输出信息直至线程结束
        time.sleep(0.5)
        try:
            if os.path.exists(f"./Log/{seg_key}.log"):
                data = parse_file(f"./Log/{seg_key}.log")
                out = json.loads(json.dumps(data))
                Progress[seg_key]["out"] = out
                if "out_time" in out:   # 提取进度
                    Progress[seg_key]["progress"] = to_seconds_time(
                        out['out_time'])/Duration
                Progress[seg_key]["update"] = time.time()
        except Exception as Error:
            print(Error)
            break

    if os.path.exists(f"./Log/{seg_key}.log"):
        os.remove(f"./Log/{seg_key}.log")    # 清理大师


def to_seconds_time(a: str) -> int:
    if a.count(":") == 1:
        return int(float(a.split(":")[0]))*60+int(float(a.split(":")[1]))
    if a.count(":") == 2:
        return int(float(a.split(":")[0]))*3600+int(float(a.split(":")[1]))*60+int(float(a.split(":")[2]))
    return int(a)


# def check_storage():
#     del_task_seg_key = ""
#     del_task_update = time.time()
#     Progress_list = list(Progress)
#     for seg_key in Progress_list:   # 遍历任务池，冒泡排序找最早的任务来删除
#         if Progress[seg_key] == -1 or Progress[seg_key] == 2:
#             if Progress[seg_key]["update"] < del_task_update:
#                 del_task_update = Progress[seg_key]["update"]
#                 del_task_seg_key = seg_key
#     # 任务创建时间不足一小时 or 硬盘已经没空位了
#     if (time.time() - del_task_update) > 3600 or check_disk_space_is_not_good(3):
#         Save_Name = Progress[del_task_seg_key]["Save_Name"]
#         del Progress[del_task_seg_key]
#         os.remove(f'./Video/{Save_Name}.mp4')

def check_storage():
    oldest_task = min(  # 找到状态为-1或2的最早任务
        [(key, val) for key, val in Progress.items() if val in [-1, 2]],
        key=lambda x: x[1]['update'], default=None
    )
    if not oldest_task: return
    del_task_seg_key, del_task = oldest_task
    
    # 任务完成了两小时 or 硬盘已经没空位了
    if (time.time() - del_task["update"]) > 7200 or check_disk_space_is_not_good(3):
        Save_Name = del_task["Save_Name"]
        del Progress[del_task_seg_key]
        os.remove(f'./Video/{Save_Name}.mp4')
