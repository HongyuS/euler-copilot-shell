Name:           openEuler-Intelligence-Install
Version:        1.0
Release:        1.oe2403sp2%{?dist}
Summary:        Deployment scripts package for openEuler 24.03 SP2

License:        MIT
URL:            https://gitee.com/openeuler/euler-copilot-shell.git
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

%description
This package contains deployment scripts and resources.

%prep
%setup -q

%install
# 创建安装目录
mkdir -p %{buildroot}/usr/lib/deploy/{scripts,resources}

# 复制脚本和资源
install -m 755 deploy.sh %{buildroot}/usr/lib/deploy/scripts/deploy
cp -r 0-one-click-deploy 1-check-env 2-install-dependency 3-install-server 4-other-script 5-resource %{buildroot}/usr/lib/deploy/scripts/
chmod -R +x %{buildroot}/usr/lib/deploy/scripts/

mkdir -p %{buildroot}/usr/bin
ln -sf /usr/lib/deploy/scripts/deploy %{buildroot}/usr/bin/openEuler-Intelligence-Install

%files
/usr/lib/deploy
/usr/bin/openEuler-Intelligence-Install

%changelog
* Mon Jul 21 2025 houxu 'houxu5@h-partners.com' - 1.0-1.oe2403sp2
- Initial package