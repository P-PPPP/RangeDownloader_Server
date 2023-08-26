let PROXY_URL = 'proxy1';
let videoPlayerAppearedOnce = false;    // 跟踪是否已经检测到video-player组件
let videoPlayerDisappearedOnce = false; // 跟踪video-player组件是否已消失
const setProxyURL = (videoURL) => {
    const mappings = {
        'https://proxy1.ddindexs.com': 'proxy1',
        'https://proxy2.ddindexs.com': 'proxy3',
        'https://proxy3.ddindexs.com': 'proxy3',
    };
    const origin = new URL(videoURL).origin;
    PROXY_URL = mappings[origin] || PROXY_URL;
};
function checkForVideoPlayerAndExecute(mutationsList, observer) {
    for (let mutation of mutationsList) {
        if (mutation.type === 'childList') {
            let videoPlayer = document.getElementById('video-player');
            if (videoPlayer && !videoPlayerAppearedOnce) {
                videoPlayerAppearedOnce = true;
                executeFunction();
            } else if (!videoPlayer && videoPlayerAppearedOnce && !videoPlayerDisappearedOnce) {
                videoPlayerDisappearedOnce = true;
                executeWhenVideoPlayerDisappears();
                videoPlayerAppearedOnce = false;
                videoPlayerDisappearedOnce = false;
            }
        }
    }
}
function isEmptyObject(obj) {
    return Object.keys(obj).length === 0 && obj.constructor === Object;
}

const observer = new MutationObserver(checkForVideoPlayerAndExecute);
observer.observe(document.body, { childList: true, subtree: true });

function executeFunction() {
    let videoPlayer = document.getElementById('video-player');
    let videoElement = videoPlayer.querySelector('video');
    let videoURL = videoElement ? videoElement.src : '';

    let grandGrandParentDiv = videoPlayer.parentNode.parentNode.parentNode;
    let grandGrandGrandParentDiv = grandGrandParentDiv.parentNode;
    let clonedDiv = grandGrandParentDiv.cloneNode(false);
    grandGrandGrandParentDiv.appendChild(clonedDiv);
    clonedDiv.id = 'cloned-div';

    clonedDiv.innerHTML = `
            <div style="display: flex; align-items: center; width: 100%; margin-bottom: 10px;">
                <input type="text" id="videoURL" value="${videoURL}" style="flex: 1; width: 50%; height: 50px; font-size: 16px; border-radius: 15px 0 0 15px; border-right: none; padding: 10px; background-color: #f1f3f5;" readonly>
                <button class="hoverEffectButton" id="copyButton" style="background-color: #777f84; height: 52px; border-radius: 0 15px 15px 0; min-width: 60px;">📋</button>
            </div>
            <div style="display: flex;align-items: center;justify-content: start;width: 80%;/* margin-right: 0px; */">
                <input  class="hoverEffectButton" type="number" id="start_time" placeholder="Start time" style="margin-right: -10px;width: 20%;height: 50px;font-size: 16px;border-radius: 15px;padding: 10px;background-color: #f1f3f5;">
                <button class="hoverEffectButton" id="copyStartButton" style="background-color: #f1f3f5;height: 50px;border-radius: 0 15px 15px 0;min-width: 40px;">⚡</button>
                <input  class="hoverEffectButton" type="number" id="end_time" placeholder="End time" style="margin-right: -10px;width: 20%;height: 50px;font-size: 16px;border-radius: 15px;padding: 10px;background-color: #f1f3f5;margin-left: 3vh;">
                <button class="hoverEffectButton" id="copyEndButton" style="background-color: #f1f3f5;height: 50px;border-radius: 0 15px 15px 0;min-width: 40px;">⚡</button>
                <button class="hoverEffectButton" id="sendButton" style="height: 52px;border-radius: 15px;padding: 0 20px;background-color: #fae200;min-width: 100px;margin-left: auto;">点击切片</button>
            </div>
            <div class="Status" style="display: flex; padding: 10px; align-items: center; justify-content: center; width: 80%; min-heigh: 200px">
                <p style="padding: 20px">等待操作中</p>
            </div>
        `;
    updateContent('else');

    document.getElementById('copyButton').onclick = function () {
        let urlField = document.getElementById('videoURL');
        urlField.select();
        document.execCommand('copy');
    };
    function convertTimeToSeconds(timeString) {
        const parts = timeString.split(':');

        if (parts.length === 3) {
            const hours = parseInt(parts[0], 10);
            const minutes = parseInt(parts[1], 10);
            const seconds = parseInt(parts[2], 10);
            return (hours * 3600) + (minutes * 60) + seconds;
        } else if (parts.length === 2) {
            const minutes = parseInt(parts[0], 10);
            const seconds = parseInt(parts[1], 10);
            return (minutes * 60) + seconds;
        }
        return 0;
    }
    document.getElementById('copyStartButton').onclick = function () {
        const fullTextContent = document.querySelector('.art-control-time').textContent;
        const timeValue = fullTextContent.split(" / ")[0].trim();
        const seconds = convertTimeToSeconds(timeValue);
        document.getElementById('start_time').value = seconds;
    };
    document.getElementById('copyEndButton').onclick = function () {
        const fullTextContent = document.querySelector('.art-control-time').textContent;
        const timeValue = fullTextContent.split(" / ")[0].trim();
        const seconds = convertTimeToSeconds(timeValue);
        document.getElementById('end_time').value = seconds;
    };
    document.getElementById('sendButton').onclick = function () {
        const videoURL = document.getElementById('videoURL').value;
        const startTime = document.getElementById('start_time').value;
        const endTime = document.getElementById('end_time').value;
        setProxyURL(videoURL);
        const jsonData = {
            url: videoURL,
            time_start: startTime,
            time_end: endTime
        };
        updateContent('loading');
        fetch(`https://${PROXY_URL}.range.ddindexs.com/api/create_segment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jsonData)
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw err; });
                }
                return response.json();
            })
            .then(enent => {
                let data = JSON.parse(enent)
                if (data.code === 1) {
                    let segkey = data.key;
                    let ws;
                    let reconnectAttempts = 0;
                    timestamp = 0
                    const maxReconnectAttempts = 5;
                    const initialDelay = 5000;
                    function initializeWebSocket() {
                        ws = new WebSocket(`wss://${PROXY_URL}.range.ddindexs.com/api/pools_status`);
                        ws.onopen = function (event) {
                            reconnectAttempts = 0; // 重置重连尝试次数
                            ws.send(JSON.stringify({ "seg_k": segkey }));
                        };
                        ws.onmessage = function (event) {
                            const data = JSON.parse(event.data);
                            if (data.time >= timestamp) {
                                timestamp = data.time
                                if (data.data.running === -1) {
                                    updateContent('Error', "出错了喵🤪🤪");
                                } else if (isEmptyObject(data.data.out)) {
                                    updateContent('loading');
                                } else if (data.data.running === 1) {
                                    updateContent('progress', data.data.progress * 100); // 将0-1的值转化为0-100的百分比
                                } else if (data.data.running === 2) {
                                    updateContent('completed', data.data.Save_Name);
                                } else {
                                    updateContent('else');
                                }
                            }
                        };
                        ws.onerror = function (event) {
                            updateContent('Error', '与服务器的连接断开了😩😩，尝试重连中');
                        }
                        ws.onclose = function (event) {
                            if (event.code === 1000) {
                                return;  // 正常关闭，不尝试重连
                            }
                            if (reconnectAttempts >= maxReconnectAttempts) {
                                updateContent('Error', "重连失败🤥");
                                return;
                            }
                            setTimeout(() => {
                                initializeWebSocket();
                                reconnectAttempts++;
                            }, initialDelay);
                        };
                    }
                    initializeWebSocket();
                } else {
                    updateContent('Error', data.msg);
                }
            })
            .catch(error => {
                updateContent('Error', '连不上服务器了😨😨，什么情况😱😱');
            });
    };
}

function executeWhenVideoPlayerDisappears() {
    let element = document.getElementById('cloned-div');
    if (element) {
        element.parentNode.removeChild(element);
    }
}

function updateContent(status, data = null) {
    const statusDiv = document.querySelector('.Status');
    if (status !== 'loading') {
        statusDiv.innerHTML = "";
    }
    if (status === 'Error') {
        statusDiv.innerHTML = `
                <p id="pStatus" style="padding: 20px"></p>
            `;
        startCycle(data);
    } else if (status === 'loading') {
        const newContent = `
                <div class="loader"></div><p style="padding-left: 2vh;font-size: 20px;">正在准备切片🐌..</p>
            `;
        if (statusDiv.innerHTML !== newContent) {
            statusDiv.innerHTML = newContent;
        }
    } else if (status === 'progress') {
        statusDiv.innerHTML = `
                <label>切片进度✂：</label><progress style="" value="${data}" max="100"></progress>
            `;
    } else if (status === 'completed') {
        statusDiv.innerHTML = `
                <button class="button-gradient" onclick="downloadFile(event, 'https://${PROXY_URL}.file.ddindexs.com/${data}.mp4');">Download</button>
            `;
        var sendButton = document.getElementById("sendButton");
        sendButton.innerHTML = `再切一下`
    } else {
        statusDiv.innerHTML = `
                <p id="pStatus" style="padding: 20px"></p>
            `;
        startCycle("还没开始切片...✂✂✂");
    }
}
function isEmoji(str) {
    const emojiRegEx = /[\u{1f600}-\u{1f64f}\u{1f300}-\u{1f5ff}\u{1f680}-\u{1f6ff}\u{2600}-\u{26ff}\u{2700}-\u{27bf}]/gu;
    return emojiRegEx.test(str);
}
function downloadFile(event, url) {
    event.preventDefault();

    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

let timeout;
let fullText = '';
let currentText = '';
let lastIndex = 0;
let delay = 200;
let extraDelay = 1000;

function displayText() {
    const contentElement = document.getElementById('pStatus');
    try {
        if (!contentElement) {
            clearTimeout(timeout);
            return;
        }

        if (lastIndex < fullText.length) {
            currentText += fullText[lastIndex];

            if (lastIndex < fullText.length - 1 && isEmoji(fullText[lastIndex] + fullText[lastIndex + 1])) {
                currentText += fullText[lastIndex + 1];
                lastIndex++;
            }

            contentElement.innerText = currentText;
            lastIndex++;
            timeout = setTimeout(displayText, delay);
        } else {
            timeout = setTimeout(() => {
                currentText = '';
                lastIndex = 0;
                displayText();
            }, extraDelay);
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

function startCycle(text) {
    if (timeout) {
        clearTimeout(timeout);
    }

    fullText = text;
    currentText = '';
    lastIndex = 0;
    displayText();
}