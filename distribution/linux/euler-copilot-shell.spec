%global pypi_name oi-cli
%global shortcut_name oi
%global debug_package %{nil}

Name:           euler-copilot-shell
Version:        0.10.0
Release:        3%{?dist}
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
BuildArch:      noarch

%description -n openeuler-intelligence-installer
openEuler Intelligence 部署安装工具包，包含部署脚本和相关资源文件。

%prep
%autosetup -n %{name}-%{version}

%build
# 创建虚拟环境
python3 -m venv %{_builddir}/venv
source %{_builddir}/venv/bin/activate

# 升级pip和setuptools
pip install --upgrade pip setuptools wheel

# 安装项目依赖
pip install -r requirements.txt

# 安装PyInstaller
pip install pyinstaller

# 使用虚拟环境中的 PyInstaller 创建单一可执行文件
# 使用专用的 .spec 文件解决 Textual 动态导入问题
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