"""系统初始化工具模块"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App

from log.manager import get_logger

if TYPE_CHECKING:
    from app.deployment.models import DeploymentConfig

from app.deployment.ui import DeploymentConfigScreen, DeploymentProgressScreen


def oi_backend_init() -> None:
    """初始化后端系统 - 启动 TUI 部署助手"""
    logger = get_logger(__name__)

    try:
        # 获取项目根目录的绝对路径
        project_root = Path(__file__).parent.parent
        css_path = str(project_root / "app" / "css" / "styles.tcss")

        class DeploymentApp(App):
            """部署 TUI 应用"""

            CSS_PATH = css_path
            TITLE = "openEuler Intelligence 部署助手"

            def __init__(self) -> None:
                super().__init__()
                self.deployment_config: DeploymentConfig | None = None

            def on_mount(self) -> None:
                """启动时显示配置界面"""
                self.push_screen(DeploymentConfigScreen())

            def on_deployment_config_submitted(self, config: DeploymentConfig) -> None:
                """配置提交后开始部署"""
                self.deployment_config = config
                if self.deployment_config is not None:
                    self.push_screen(
                        DeploymentProgressScreen(self.deployment_config),
                    )

        app = DeploymentApp()
        result = app.run()
        logger.info("部署结果: %s", result)
    except KeyboardInterrupt:
        logger.warning("用户中断部署")
    except ImportError:
        logger.exception("导入模块失败")
    except RuntimeError:
        logger.exception("部署过程中发生错误")
    except Exception:
        logger.exception("未预期的错误")
        raise
