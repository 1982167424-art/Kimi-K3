"""
Kimi K3 视频理解模块
提供完整的视频理解功能，支持多种输入方式和分析模式。
"""

import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Generator

import requests
from openai import OpenAI


class VideoUnderstanding:
    """Kimi K3 视频理解核心类"""

    def __init__(self, api_key: Optional[str] = None, model: str = "kimi-k3"):
        """
        初始化视频理解客户端

        Args:
            api_key: Kimi API密钥，如果未提供则从环境变量 KIMI_API_KEY 读取
            model: 模型名称，默认为 kimi-k3
        """
        self.api_key = api_key or os.environ.get("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "请提供API密钥或设置环境变量 KIMI_API_KEY\n"
                "  export KIMI_API_KEY=\"your_api_key\"\n"
                "  API key 从 https://platform.kimi.ai 获取"
            )

        self.model = model
        self.api_base = "https://api.moonshot.ai/v1"
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    def analyze_video(
        self,
        video_source: str,
        prompt: str = "请仔细观看这个视频，详细描述视频中的内容：画面里有什么？发生了什么？",
        stream: bool = True,
        reasoning_effort: str = "high"
    ) -> Generator[str, None, None] | str:
        """
        分析视频内容

        Args:
            video_source: 视频源，支持以下格式：
                - 本地文件路径: "./video.mp4"
                - HTTP/HTTPS URL: "https://example.com/video.mp4"
                - Base64编码: "base64:..."
            prompt: 分析提示词
            stream: 是否使用流式输出
            reasoning_effort: 推理强度，可选 "low", "medium", "high"

        Returns:
            如果stream=True，返回生成器；否则返回完整响应字符串
        """
        video_b64 = self._load_video(video_source)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": f"data:video/mp4;base64,{video_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=stream,
            reasoning_effort=reasoning_effort,
        )

        if stream:
            return self._process_stream(response)
        else:
            return response.choices[0].message.content

    def describe_video(self, video_source: str) -> str:
        """快速描述视频内容"""
        return self.analyze_video(
            video_source,
            prompt="请用2-3句话简洁地描述这个视频的主要内容。",
            stream=False
        )

    def analyze_timeline(self, video_source: str) -> str:
        """分析视频时间线"""
        return self.analyze_video(
            video_source,
            prompt="请按照时间顺序，详细描述视频中发生的事件，格式为：[时间点] 事件描述",
            stream=False
        )

    def extract_key_frames(self, video_source: str) -> str:
        """提取关键帧描述"""
        return self.analyze_video(
            video_source,
            prompt="请识别视频中的关键画面/场景，描述每个关键画面的内容和出现的大致时间。",
            stream=False
        )

    def analyze_emotion(self, video_source: str) -> str:
        """分析视频情感/氛围"""
        return self.analyze_video(
            video_source,
            prompt="请分析这个视频的情感氛围和情绪基调，包括画面色调、音乐、人物表情等方面。",
            stream=False
        )

    def answer_question(self, video_source: str, question: str) -> str:
        """基于视频回答特定问题"""
        return self.analyze_video(
            video_source,
            prompt=f"请观看视频后回答以下问题：{question}",
            stream=False
        )

    def _load_video(self, video_source: str) -> str:
        """加载视频并转换为base64"""
        if video_source.startswith("base64:"):
            return video_source[7:]

        if video_source.startswith(("http://", "https://")):
            return self._download_video(video_source)

        return self._read_local_file(video_source)

    def _download_video(self, url: str) -> str:
        """从URL下载视频"""
        print(f"正在下载视频: {url}")
        resp = requests.get(url, stream=True, timeout=300)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    print(f"\r  下载进度: {pct}% ({downloaded // 1024}KB / {total // 1024}KB)", end="", flush=True)

            tmp_path = tmp.name

        print(f"\n  下载完成: {tmp_path}")

        with open(tmp_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")

        os.unlink(tmp_path)
        return video_b64

    def _read_local_file(self, file_path: str) -> str:
        """读取本地视频文件"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {file_path}")

        print(f"正在读取视频: {file_path}")
        with open(path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")

        print(f"  读取完成，大小: {len(video_b64) * 3 // 4 // 1024}KB")
        return video_b64

    def _process_stream(self, response) -> Generator[str, None, None]:
        """处理流式响应"""
        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                yield delta.reasoning_content
            if delta.content:
                yield delta.content


def create_client(api_key: Optional[str] = None, model: str = "kimi-k3") -> VideoUnderstanding:
    """便捷函数：创建视频理解客户端"""
    return VideoUnderstanding(api_key=api_key, model=model)
