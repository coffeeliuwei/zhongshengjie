#!/bin/bash
# 众生界项目一键移植脚本（Linux/Mac）

echo "========================================"
echo "众生界项目一键移植脚本"
echo "========================================"
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo "使用方法: ./migrate.sh <目标目录>"
    echo "示例: ./migrate.sh /path/to/new-project"
    exit 1
fi

TARGET_DIR="$1"

echo "目标目录: $TARGET_DIR"
echo ""

# 1. 检查Python
echo "检查Python环境..."
python --version || {
    echo "❌ Python未安装，请先安装Python 3.8+"
    exit 1
}

# 2. 安装依赖
echo "安装依赖..."
pip install -r requirements.txt || {
    echo "⚠️ 依赖安装失败，请手动安装"
}

# 3. 导出模板
echo "导出项目模板..."
python -m modules.migration.export_template --target "$TARGET_DIR" || {
    echo "❌ 模板导出失败"
    exit 1
}

# 4. 初始化环境
echo "初始化新环境..."
cd "$TARGET_DIR"
python -m core config --init || {
    echo "⚠️ 配置初始化失败，请手动配置"
}

# 5. 提示用户
echo ""
echo "========================================"
echo "✅ 移植完成！"
echo "========================================"
echo ""
echo "下一步操作:"
echo "1. 编辑 CONFIG.md 配置小说信息"
echo "2. 编辑 system_config.json 配置资源目录"
echo "3. 编辑设定文件（人物谱、十大势力等）"
echo "4. 启动Qdrant Docker: docker run -p 6333:6333 qdrant/qdrant"
echo "5. 同步设定: python -m core kb --sync novel"
echo "6. 开始创作: python -m core create --workflow"
echo ""

# 创建快捷脚本
cat > "$TARGET_DIR/start.sh" << 'EOF'
#!/bin/bash
# 快捷启动脚本

echo "众生界快速启动..."
python -m core cli --help
EOF

chmod +x "$TARGET_DIR/start.sh"

echo "已创建快捷脚本: start.sh"
echo ""