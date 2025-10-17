#!/bin/bash

# 创建Mac DMG安装包的脚本

# 设置变量
APP_NAME="FlyClimbingAnalyzer"
VERSION="1.0"
DMG_NAME="${APP_NAME}_${VERSION}"
SOURCE_DIR="./dist"
DMG_DIR="./dmg"
DMG_TEMP="${DMG_DIR}/${DMG_NAME}_temp"
DMG_FINAL="${DMG_DIR}/${DMG_NAME}.dmg"

# 清理并创建目录
echo "清理并创建目录..."
rm -rf "${DMG_DIR}"
mkdir -p "${DMG_TEMP}"

# 复制应用程序到临时目录
echo "复制应用程序..."
cp -R "${SOURCE_DIR}/${APP_NAME}.app" "${DMG_TEMP}/"

# 创建应用程序文件夹链接
echo "创建应用程序文件夹链接..."
ln -s /Applications "${DMG_TEMP}/Applications"

# 创建DMG
echo "创建DMG..."
hdiutil create -volname "${APP_NAME}" -srcfolder "${DMG_TEMP}" -ov -format UDZO "${DMG_FINAL}"

# 清理临时目录
echo "清理临时目录..."
rm -rf "${DMG_TEMP}"

echo "DMG安装包创建完成: ${DMG_FINAL}"