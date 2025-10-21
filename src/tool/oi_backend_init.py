"""系统初始化工具模块"""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import App

from app.deployment import InitializationModeScreen
from config.manager import ConfigManager
from log.manager import get_logger


def backend_init() -> None:
    """初始化后端系统 - 启动 TUI 部署助手"""
    logger = get_logger(__name__)

    try:
        # 首先检查和更新配置文件
        logger.info("检查配置文件...")

        # 在部署阶段，使用普通配置管理器操作 root 用户的配置
        # 这样 Agent 初始化时可以正常写入 AppID 等信息
        # 部署完成后会将完整配置复制为全局模板
        config_manager = ConfigManager()
        config_updated = config_manager.validate_and_update_config()

        if config_updated:
            logger.info("配置文件已更新")
        else:
            logger.info("配置文件检查完成")

        # 获取项目根目录的绝对路径
        project_root = Path(__file__).parent.parent
        css_path = str(project_root / "app" / "css" / "styles.tcss")

        class DeploymentApp(App):
            """部署 TUI 应用"""

            CSS_PATH = css_path
            TITLE = "openEuler Intelligence 部署助手"

            def on_mount(self) -> None:
                """启动时先显示初始化模式选择界面"""
                self.push_screen(InitializationModeScreen())

        app = DeploymentApp()
        result = app.run()
        logger.info("部署结果: %s", result)

        # 部署完成后，强制从全局模板刷新当前用户的配置
        _refresh_user_config_from_template()

    except KeyboardInterrupt:
        logger.warning("用户中断部署")
    except ImportError:
        logger.exception("导入模块失败")
    except RuntimeError:
        logger.exception("部署过程中发生错误")
    except Exception:
        logger.exception("未预期的错误")
        raise


def _refresh_user_config_from_template() -> None:
    """
    部署完成后强制从全局模板刷新当前用户的配置

    确保部署时创建的全局模板配置能够应用到当前用户
    """
    logger = get_logger(__name__)

    try:
        # 检查全局模板是否存在
        if not ConfigManager.GLOBAL_CONFIG_PATH.exists():
            logger.warning("全局配置模板不存在，跳过配置刷新")
            return

        # 确保用户配置目录存在
        ConfigManager.USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # 从全局模板读取配置
        with ConfigManager.GLOBAL_CONFIG_PATH.open(encoding="utf-8") as f:
            template_config = json.load(f)

        # 如果用户配置已存在，保留用户的个性化设置（如 locale）
        user_config = template_config.copy()
        if ConfigManager.USER_CONFIG_PATH.exists():
            try:
                with ConfigManager.USER_CONFIG_PATH.open(encoding="utf-8") as f:
                    existing_config = json.load(f)
                # 保留用户的语言设置
                if "locale" in existing_config:
                    user_config["locale"] = existing_config["locale"]
            except (json.JSONDecodeError, OSError):
                logger.warning("读取现有用户配置失败，将使用模板配置")

        # 写入用户配置
        with ConfigManager.USER_CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(user_config, f, indent=4, ensure_ascii=False)

        logger.info("已从全局模板刷新当前用户配置: %s", ConfigManager.USER_CONFIG_PATH)

    except (OSError, json.JSONDecodeError):
        logger.exception("从全局模板刷新用户配置失败")
    except Exception:
        logger.exception("刷新用户配置时发生未预期的错误")
