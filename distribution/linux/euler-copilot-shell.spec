%global pypi_name oi-cli
%global shortcut_name oi
%global debug_package %{nil}

Name:           euler-copilot-shell
Version:        0.10.0
Release:        4%{?dist}
Summary:        openEuler Intelligence 智能命令行工具集
License:        MulanPSL-2.0
URL:            https://gitee.com/openeuler/euler-copilot-shell
Source0:        %{name}-%{version}.tar.gz

ExclusiveArch:  x86_64 aarch64 riscv64 loongarch64

BuildRequires:  python3-devel
BuildRequires:  python3-virtualenv
BuildRequires:  python3-pip

%description
openEuler Intelligence 智能命令行工具集，包含智能 Shell 命令行程序和部署安装工具。

# 智能命令行工具子包
%package -n openeuler-intelligence-cli
Summary:        openEuler Intelligence 智能 Shell 命令行工具
Requires:       glibc
# 替换原来的 euler-copilot-shell 包
Obsoletes:      euler-copilot-shell < %{version}-%{release}
Provides:       euler-copilot-shell = %{version}-%{release}

%description -n openeuler-intelligence-cli
openEuler Intelligence 智能 Shell 是一个智能命令行程序。
它允许用户输入命令，通过集成大语言模型提供命令建议，帮助用户更高效地使用命令行。

# 部署安装工具子包
%package -n openeuler-intelligence-installer
Summary:        openEuler Intelligence 部署安装脚本
Requires:       python3-aiohttp
Requires:       python3-requests
BuildArch:      noarch

%description -n openeuler-intelligence-installer
openEuler Intelligence 部署安装工具包，包含部署脚本和相关资源文件。

%prep
%autosetup -n %{name}-%{version}

%build
# 创建虚拟环境
python3 -m venv %{_builddir}/venv
source %{_builddir}/venv/bin/activate

# 升级 pip 和 setuptools
pip install --upgrade pip setuptools wheel

# 安装项目依赖
pip install -r requirements.txt

# 安装 PyInstaller
pip install pyinstaller

# 使用虚拟环境中的 PyInstaller 创建单一可执行文件
pyinstaller --noconfirm \
            --distpath dist \
            oi-cli.spec

# 退出虚拟环境
deactivate

%install
# 安装智能命令行工具
mkdir -p %{buildroot}%{_bindir}
install -m 0755 dist/%{pypi_name} %{buildroot}%{_bindir}/%{pypi_name}

# 创建快捷链接
ln -sf %{pypi_name} %{buildroot}%{_bindir}/%{shortcut_name}

# 安装部署脚本和资源
mkdir -p %{buildroot}/usr/lib/openeuler-intelligence/{scripts,resources}
mkdir -p %{buildroot}%{_bindir}

# 复制部署脚本和资源
install -m 755 scripts/deploy/deploy.sh %{buildroot}/usr/lib/openeuler-intelligence/scripts/deploy
cp -r scripts/deploy/0-one-click-deploy scripts/deploy/1-check-env scripts/deploy/2-install-dependency scripts/deploy/3-install-server scripts/deploy/4-other-script scripts/deploy/5-resource %{buildroot}/usr/lib/openeuler-intelligence/scripts/
chmod -R +x %{buildroot}/usr/lib/openeuler-intelligence/scripts/

# 创建可执行文件的符号链接
ln -sf /usr/lib/openeuler-intelligence/scripts/deploy %{buildroot}%{_bindir}/openeuler-intelligence-installer

%files -n openeuler-intelligence-cli
%license LICENSE
%doc README.md
%{_bindir}/%{pypi_name}
%{_bindir}/%{shortcut_name}

%files -n openeuler-intelligence-installer
%license LICENSE
%doc scripts/deploy/安装部署手册.md
/usr/lib/openeuler-intelligence
%{_bindir}/openeuler-intelligence-installer

%changelog
* Tue Sep 09 2025 openEuler <contact@openeuler.org> - 0.10.0-4
- 优化安装脚本：添加内核版本检查和架构支持，优化 MongoDB 和 MinIO 安装逻辑
- 优化 MCP 交互相关 TUI 样式

* Thu Sep 04 2025 openEuler <contact@openeuler.org> - 0.10.0-3
- 部署功能新增支持全量部署（含 RAG、Web）
- 允许构建 riscv64 loongarch64 版本

* Thu Aug 28 2025 openEuler <contact@openeuler.org> - 0.10.0-2
- 新增 openEuler Intelligence 部署功能 TUI
- 新增选择默认 Agent 功能

* Wed Aug 13 2025 openEuler <contact@openeuler.org> - 0.10.0-1
- 重构为子包形式：openeuler-intelligence-cli 和 openeuler-intelligence-installer
- openeuler-intelligence-cli 替换原 euler-copilot-shell 包
- 新增 openeuler-intelligence-installer 子包，包含部署安装脚本

* Thu Jun 26 2025 Wenlong Zhang <zhangwenlong@loongson.cn> - 0.9.2-12
- enable loongarch64 build

* Fri Jun 20 2025 misaka00251 <liuxin@iscas.ac.cn> - 0.9.2-11
- Enable riscv64 build

* Tue May 20 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-10
- Fix OpenAI backend issue

* Mon Apr 07 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-9
- Fix OpenAI backend issue

* Wed Mar 12 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-8
- Set default backend to openai

* Mon Mar 10 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-7
- Update build 7

* Fri Feb 28 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-6
- Update build 6

* Mon Feb 24 2025 Hongyu Shi <shywzt@iCloud.com> - 0.9.2-5
- Add euler-copilot-shell
