# Main For Alist Ver0.1
import os
import json
import argparse
import uvicorn
import uuid
import asyncio
import schedule
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import FFmpeg_Core
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
parser = argparse.ArgumentParser(description="Running a Slave service.")
parser.add_argument('--config', '--c', help="Specify an conofig file.")
par = parser.parse_args()
Config = json.loads(open(par.config, "r", encoding="utf-8").read())
app.add_middleware(CORSMiddleware, allow_origins=Config["SAFTY_IP"], allow_credentials=True, allow_methods=[
                   "*"], allow_headers=["*"],)


class depoly(BaseModel):
    url: str
    time_start: int
    time_end: int


def get_download_url(play_url) -> str:
    # 针对可能需要解析为新链接的情况
    return play_url


def check_disk_space_good(path="/"):
    """检查给定路径的磁盘剩余空间是否小于3GB并执行相应的操作。"""
    stat = os.statvfs(path)
    free_space_bytes = stat.f_bsize * stat.f_bavail
    free_space_gb = free_space_bytes / (1024**3)

    if free_space_gb < 3.5:
        return False
    else:
        return True


@app.get("/ping")
def ping():
    return "pong"


@app.post("/api/create_segment")  # 创建分割任务
def create_segment(depoly_inf: depoly):
    # 校验阶段
    if depoly_inf.url.startswith("https://proxy1.ddindexs.com/") or depoly_inf.url.startswith("https://proxy2.ddindexs.com/") or depoly_inf.url.startswith("https://proxy3.ddindexs.com/"):
        if (depoly_inf.time_end - depoly_inf.time_start) > 1800:
            return {"msg": "时间太长了"}
        if not check_disk_space_good:   # 磁盘空间不乐观
            return {"msg": "磁盘空间不够了"}
        # 生成UUID，在URL，开始结束时间一致时，对于此台设备的UUID相同
        seg_key = uuid.uuid5(namespace=uuid.NAMESPACE_DNS, name=depoly_inf.url +
                             str(depoly_inf.time_start) +
                             str(depoly_inf.time_end)
                             ).__str__()

        # 检测是否已经在队列中，未在队列中的，则注册为新的TASK
        if (FFmpeg_Core.Progress.get(seg_key) != None):
            return {"key": seg_key}
        FFmpeg_Core.Progress.update({seg_key: {"running": 0}})
        FFmpeg_Core.threadPool.submit(FFmpeg_Core.Segment,
                                      depoly_inf.time_start,
                                      depoly_inf.time_end,
                                      get_download_url(depoly_inf.url),
                                      seg_key,
                                      seg_key,
                                      "",
                                      Config["DOWNLOAD_PATH"]
                                      )  # 新TASK加入到队列池中

        return {"key": seg_key}
    return {"msg": "链接不对劲"}


@app.websocket('/api/pools_status')
async def websocket_endpoint(websocket: WebSocket):
    """返回状态
    Req: {"seg_k":"xxxx"}
    Resp: {"msg":"","data":"","downloadurl":"","code":""}
    """
    await websocket.accept()
    seg_k = await websocket.receive_json()
    results = {}
    while True:
        results = FFmpeg_Core.Progress.get(seg_k["seg_k"])
        await websocket.send_text(f"{json.dumps(results)}")
        await asyncio.sleep(0.5)
        if results:
            if results["running"] not in [0, 1]:
                break
        else:
            break

    await websocket.send_text(f"{json.dumps(results)}")
    await websocket.close()


@app.get('/debug')
def s():
    return FFmpeg_Core.Progress


if __name__ == "__main__":
    schedule.every().day.at(Config["EVERYDAY_CHECK_SCHEDULE"]).do(
        FFmpeg_Core.check_storage, Config["DOWNLOAD_PATH"])
    uvicorn.run(app="main:app", port=Config["HOSTPORT"], host=Config["HOSTIP"])
