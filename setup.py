"""
setup.py

This is a setup script for the oi-cli package.
"""

from setuptools import find_packages, setup

setup(
    name="oi-cli",
    version="0.10.0",
    description="智能 Shell 命令行工具",
    author="openEuler",
    author_email="contact@openeuler.org",
    url="https://gitee.com/openeuler/euler-copilot-shell",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "httpx==0.28.1",
        "openai==1.99.6",
        "rich==14.1.0",
        "textual==5.3.0",
    ],
    entry_points={
        "console_scripts": [
            "oi=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MulanPSL-2.0 License",
    ],
    python_requires=">=3.11",
)
