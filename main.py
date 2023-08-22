#Main For Alist Ver0.1
import json, argparse , uvicorn , uuid , asyncio , schedule
from fastapi import FastAPI , WebSocket
from pydantic import BaseModel
import FFmpeg_Core
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
parser = argparse.ArgumentParser(description="Running a Slave service.")
parser.add_argument('--config','--c',help="Specify an conofig file.")
par = parser.parse_args()
Config = json.loads(open(par.config,"r",encoding="utf-8").read())
app.add_middleware(CORSMiddleware,allow_origins=Config["SAFTY_IP"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)

class depoly(BaseModel):
    url:str
    time_start:int
    time_end :int

def get_download_url(play_url)->str:
    #针对可能需要解析为新链接的情况
    return play_url

@app.get("/ping")
def ping():
    return "pong"

@app.post("/api/create_segment")
def create_segment(depoly_inf:depoly):
    # 创建一个分割任务
    seg_key = uuid.uuid5(namespace=uuid.NAMESPACE_DNS,name=depoly_inf.url+str(depoly_inf.time_start)+str(depoly_inf.time_end)).__str__()# 生成 较为 唯一的ID，但在URL，开始结束时间一致时，对于此台设备的uuid相同
    if (FFmpeg_Core.Progress.get(seg_key) != None): return seg_key # 检测是否已经在队列中
    FFmpeg_Core.Progress.update({seg_key:{"running":0}}) #对于未在队列中的,则注册为新的task
    FFmpeg_Core.threadPool.submit(FFmpeg_Core.Segment,depoly_inf.time_start,depoly_inf.time_end,get_download_url(depoly_inf.url),seg_key,seg_key,"",Config["DOWNLOAD_PATH"]) #新task加入到队列池中
    return seg_key

@app.websocket('/api/pools_status')
async def websocket_endpoint(websocket: WebSocket):
    """返回状态
    Req: {"seg_k":"xxxx"}
    Resp: {"msg":"","data":"","downloadurl":"","code":""}
    """
    await websocket.accept()
    seg_k = await websocket.receive_json()
    while True:
        results = FFmpeg_Core.Progress.get(seg_k["seg_k"])
        await websocket.send_text(f"Message text was: {results}")
        await asyncio.sleep(1)
        if results["running"] in [0,1]:pass
        else: break
    websocket.close()

@app.get('/debug')
def s():
    return FFmpeg_Core.Progress

if __name__ == "__main__":
    schedule.every().day.at(Config["EVERYDAY_CHECK_SCHEDULE"]).do(FFmpeg_Core.check_storage,Config["DOWNLOAD_PATH"])
    uvicorn.run(app="main:app",port=Config["HOSTPORT"],host=Config["HOSTIP"])
