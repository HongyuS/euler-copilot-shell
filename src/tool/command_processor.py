"""命令处理器"""

import shutil
import subprocess
from collections.abc import AsyncGenerator

from backend.base import LLMClientBase
from log.manager import get_logger

# 定义危险命令黑名单
BLACKLIST = ["rm", "sudo", "shutdown", "reboot", "mkfs"]


def is_command_safe(command: str) -> bool:
    """
    检查命令是否安全

    检查命令是否安全，若包含黑名单中的子串则返回 False。
    """
    return all(dangerous not in command for dangerous in BLACKLIST)


def execute_command(command: str) -> tuple[bool, str]:
    """
    执行命令并返回结果

    尝试执行命令：
    返回 (True, 命令标准输出) 或 (False, 错误信息)。
    """
    try:
        result = subprocess.run(  # noqa: S602
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        return False, str(e)
    else:
        return success, output


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
    if shutil.which(prog) is not None:
        logger.info("检测到系统命令: %s", prog)
        # 检查命令安全性
        if not is_command_safe(command):
            logger.warning("命令被安全检查阻止: %s", command)
            yield ("检测到不安全命令，已阻止执行。", True)  # 作为LLM输出处理
            return

        logger.info("执行系统命令: %s", command)
        success, output = execute_command(command)
        if success:
            logger.debug("命令执行成功，输出长度: %d", len(output))
            yield (output, False)  # 系统命令输出，使用纯文本
        else:
            # 执行失败，将错误信息反馈给大模型
            logger.info("命令执行失败，向 LLM 请求建议")
            query = f"命令 '{command}' 执行失败，错误信息如下：\n{output}\n请帮忙分析原因并提供解决建议。"
            async for suggestion in llm_client.get_llm_response(query):
                yield (suggestion, True)  # LLM输出，使用富文本
    else:
        # 不是已安装的命令，直接询问大模型
        logger.debug("向 LLM 发送问题: %s", command)
        async for suggestion in llm_client.get_llm_response(command):
            yield (suggestion, True)  # LLM输出，使用富文本
