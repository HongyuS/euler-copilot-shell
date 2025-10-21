#!/usr/bin/env bash
# 国际化翻译管理脚本

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src"
LOCALE_DIR="$SRC_DIR/i18n/locales"
POT_FILE="$LOCALE_DIR/messages.pot"

# 颜色输出函数（使用 printf 确保兼容性）
print_blue() {
    printf "\033[0;34m%s\033[0m\n" "$1"
}

print_green() {
    printf "\033[0;32m%s\033[0m\n" "$1"
}

print_yellow() {
    printf "\033[1;33m%s\033[0m\n" "$1"
}

print_red() {
    printf "\033[0;31m%s\033[0m\n" "$1"
}

# 检查 gettext 工具是否安装
check_gettext() {
    if ! command -v xgettext &>/dev/null; then
        print_red "❌ xgettext command not found. Please install gettext tools:"
        echo "   macOS: brew install gettext"
        echo "   Ubuntu/Debian: sudo apt-get install gettext"
        echo "   Fedora/RHEL/openEuler: sudo dnf install gettext"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    print_blue "国际化翻译管理工具"
    echo ""
    echo "使用方法:"
    echo "  $0 <command>"
    echo ""
    echo "命令:"
    print_green "  extract"
    echo "    从源代码提取可翻译字符串到模板文件"
    print_green "  update"
    echo "    更新所有语言的翻译文件"
    print_green "  compile"
    echo "    编译翻译文件为二进制格式"
    print_green "  all"
    echo "    执行完整流程 (extract -> update -> compile)"
    print_green "  help"
    echo "    显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 extract   # 提取可翻译字符串"
    echo "  $0 compile   # 编译翻译文件"
    echo "  $0 all       # 完整翻译工作流"
    echo ""
    echo "更多信息请参考: docs/development/国际化开发指南.md"
}

# 提取可翻译字符串
extract() {
    print_blue "🔍 提取可翻译字符串..."

    check_gettext

    # 查找所有 Python 源文件（使用相对路径）
    cd "$PROJECT_ROOT"
    python_files=$(find src -name "*.py" -type f)

    if [ -z "$python_files" ]; then
        print_red "❌ No Python files found in src directory"
        exit 1
    fi

    file_count=$(echo "$python_files" | wc -l | sed 's/^[[:space:]]*//')
    echo "   Found $file_count Python files"
    echo "   Output file: $POT_FILE"

    # 使用 xgettext 提取字符串（使用相对路径）
    # shellcheck disable=SC2086
    if xgettext \
        --language=Python \
        --keyword=_ \
        --keyword=_n:1,2 \
        --output="$POT_FILE" \
        --from-code=UTF-8 \
        --package-name=oi-cli \
        --package-version=0.10.2 \
        --msgid-bugs-address=contact@openeuler.org \
        --copyright-holder="openEuler Intelligence Project" \
        --add-comments=Translators \
        $python_files; then
        print_green "✅ Successfully extracted strings to messages.pot"
    else
        print_red "❌ Failed to extract strings"
        exit 1
    fi
}

# 更新翻译文件
update() {
    print_blue "🔄 更新翻译文件..."

    check_gettext

    if [ ! -f "$POT_FILE" ]; then
        print_red "❌ Template file messages.pot not found"
        echo "   Please run: $0 extract first"
        exit 1
    fi

    updated=0

    # 遍历所有语言目录
    for locale_path in "$LOCALE_DIR"/*; do
        if [ ! -d "$locale_path" ]; then
            continue
        fi

        locale_name=$(basename "$locale_path")
        po_file="$locale_path/LC_MESSAGES/messages.po"

        if [ ! -f "$po_file" ]; then
            print_yellow "⚠️  Skipping $locale_name: PO file not found"
            continue
        fi

        echo "   Updating $locale_name..."
        if msgmerge --update --backup=none "$po_file" "$POT_FILE" 2>/dev/null; then
            echo "   ✅ Updated $locale_name"
            updated=$((updated + 1))
        else
            print_yellow "   ⚠️  Failed to update $locale_name"
        fi
    done

    if [ $updated -gt 0 ]; then
        echo ""
        print_green "✅ Successfully updated $updated translation file(s)"
        echo ""
        print_yellow "📝 Next steps:"
        echo "   1. Edit the .po files to add/update translations"
        echo "   2. Run: $0 compile to compile translations"
    else
        echo ""
        print_yellow "⚠️  No translation files were updated"
    fi
}

# 编译翻译文件
compile() {
    print_blue "⚙️  编译翻译文件..."

    check_gettext

    compiled=0
    failed=0

    # 遍历所有语言目录
    for locale_path in "$LOCALE_DIR"/*; do
        if [ ! -d "$locale_path" ]; then
            continue
        fi

        locale_name=$(basename "$locale_path")
        po_file="$locale_path/LC_MESSAGES/messages.po"
        mo_file="$locale_path/LC_MESSAGES/messages.mo"

        if [ ! -f "$po_file" ]; then
            print_yellow "⚠️  Skipping $locale_name: PO file not found"
            continue
        fi

        echo "   Compiling $locale_name..."
        # 临时禁用 set -e 和 set -o pipefail 以捕获错误但继续执行
        set +e
        set +o pipefail
        error_output=$(msgfmt -o "$mo_file" "$po_file" 2>&1)
        msgfmt_status=$?
        set -e
        set -o pipefail

        if [ "$msgfmt_status" -eq 0 ]; then
            echo "   ✅ Compiled $locale_name"
            compiled=$((compiled + 1))
        else
            print_yellow "   ⚠️  Failed to compile $locale_name"
            echo "   Error: $error_output"
            failed=$((failed + 1))
        fi
    done

    echo ""
    if [ "$compiled" -gt 0 ]; then
        print_green "✅ Successfully compiled $compiled translation file(s)"
    fi

    if [ "$failed" -gt 0 ]; then
        print_yellow "⚠️  Failed to compile $failed translation file(s)"
    fi

    if [ "$compiled" -eq 0 ] && [ "$failed" -eq 0 ]; then
        print_yellow "⚠️  No translation files found to compile"
    fi
}

# 执行完整流程
all() {
    extract
    echo ""
    update
    echo ""
    compile
    echo ""
    print_green "✅ 翻译工作流完成！"
    echo ""
    print_yellow "📝 下一步:"
    echo "  1. 编辑 .po 文件添加或更新翻译"
    echo "  2. 重新运行 '$0 compile' 编译翻译"
    echo "  3. 运行 'oi --locale zh_CN' 测试中文"
    echo "  4. 运行 'oi --locale en_US' 测试英文"
}

# 主函数
main() {
    case "${1:-help}" in
    extract)
        extract
        ;;
    update)
        update
        ;;
    compile)
        compile
        ;;
    all)
        all
        ;;
    help | --help | -h)
        show_help
        ;;
    *)
        print_red "❌ 未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
    esac
}

main "$@"
