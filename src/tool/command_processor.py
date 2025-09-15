"""
命令处理器

功能说明:
1. 异步流式执行系统命令: 逐行输出 STDOUT。
2. 结束后输出总结状态(退出码，成功/失败)。
3. 失败时自动向 LLM 请求分析建议并继续流式输出建议。
"""

import asyncio
import logging
import shutil
from collections.abc import AsyncGenerator

from backend.base import LLMClientBase
from backend.hermes.mcp_helpers import is_mcp_message
from log.manager import get_logger

# 定义危险命令黑名单
BLACKLIST = ["rm", "sudo", "shutdown", "reboot", "mkfs"]


def is_command_safe(command: str) -> bool:
    """
    检查命令是否安全

    检查命令是否安全，若包含黑名单中的子串则返回 False。
    """
    return all(dangerous not in command for dangerous in BLACKLIST)


async def process_command(command: str, llm_client: LLMClientBase) -> AsyncGenerator[tuple[str, bool], None]:
    """
    处理用户输入的命令

    1. 检查 PATH 中是否存在用户输入的命令（取输入字符串的第一个单词）；
    2. 若存在，则检查命令安全性，安全时执行命令；若执行失败则将错误信息附带命令发送给大模型；
    3. 若不存在，则直接将命令内容发送给大模型生成建议。

    返回一个元组 (content, is_llm_output)，其中：
    - content: 输出内容
    - is_llm_output: 是否是LLM输出（True表示LLM输出，应使用富文本；False表示命令输出，应使用纯文本）
    """
    logger = get_logger(__name__)
    logger.debug("开始处理命令: %s", command)

    tokens = command.split()
    if not tokens:
        yield ("请输入有效命令或问题。", True)  # 作为LLM输出处理
        return

    prog = tokens[0]
    if shutil.which(prog) is None:
        # 非系统命令 -> 直接走 LLM
        logger.debug("向 LLM 发送问题: %s", command)
        async for suggestion in llm_client.get_llm_response(command):
            is_mcp_message_flag = is_mcp_message(suggestion)
            yield (suggestion, not is_mcp_message_flag)
        return

    logger.info("检测到系统命令: %s", prog)
    if not is_command_safe(command):
        logger.warning("命令被安全检查阻止: %s", command)
        yield ("检测到不安全命令，已阻止执行。", True)
        return

    # 流式执行
    async for item in _stream_system_command(command, llm_client, logger):
        yield item


async def _stream_system_command(
    command: str,
    llm_client: LLMClientBase,
    logger: logging.Logger,
) -> AsyncGenerator[tuple[str, bool], None]:
    """
    流式执行系统命令。

    逐行产出 STDOUT (is_llm_output=False)。结束后追加一条状态行: 成功 / 失败。
    若失败随后继续产出 LLM 建议 (is_llm_output=True，除非是 MCP 消息)。
    """
    logger.info("(流式) 执行系统命令: %s", command)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        logger.exception("创建子进程失败")
        status = f"[命令启动失败] {exc}"
        yield (status, False)
        query = f"无法启动命令 '{command}'，错误：{exc}\n请分析可能原因并给出解决建议。"
        async for suggestion in llm_client.get_llm_response(query):
            is_mcp_message_flag = is_mcp_message(suggestion)
            yield (suggestion, not is_mcp_message_flag)
        return

    assert proc.stdout is not None  # 类型提示
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        # CR -> LF 规范化
        text = line.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        yield (text, False)

    returncode = await proc.wait()
    success = returncode == 0

    if success:
        yield (f"\n[命令完成] 退出码: {returncode}", False)
        return

    # 失败: 读取 stderr
    stderr_text = ""
    if proc.stderr is not None:
        try:
            stderr_bytes = await proc.stderr.read()
            stderr_text = stderr_bytes.decode(errors="replace")
        except (OSError, asyncio.CancelledError) as exc:  # pragma: no cover
            stderr_text = f"读取 stderr 失败: {exc}"

    yield (f"[命令失败] 退出码: {returncode}", False)

    # 追加 LLM 分析
    logger.info("命令执行失败(returncode=%s)，向 LLM 请求建议", returncode)
    query = (
        f"命令 '{command}' 以非零状态 {returncode} 退出。\n"
        f"标准错误输出如下：\n{stderr_text}\n"
        "请分析原因并提供解决建议。"
    )
    async for suggestion in llm_client.get_llm_response(query):
        is_mcp_message_flag = is_mcp_message(suggestion)
        yield (suggestion, not is_mcp_message_flag)
