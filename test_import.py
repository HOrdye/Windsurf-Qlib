#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试导入 qlib-server 模块的脚本
"""
import os
import sys
import importlib
import inspect

def print_separator(title=""):
    """打印分隔符"""
    print("\n" + "=" * 50)
    if title:
        print(f" {title} ".center(50, "="))
        print("=" * 50)
    print()

# 1. 打印当前工作目录和Python路径
print_separator("环境信息")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python版本: {sys.version}")
print(f"Python可执行文件: {sys.executable}")
print(f"sys.path 内容:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

# 2. 检查qlib-server目录
print_separator("检查qlib-server目录")
qlib_server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qlib-server")
print(f"qlib-server目录: {qlib_server_dir}")
print(f"目录存在: {os.path.exists(qlib_server_dir)}")
if os.path.exists(qlib_server_dir):
    print(f"目录内容:")
    for item in os.listdir(qlib_server_dir):
        item_path = os.path.join(qlib_server_dir, item)
        if os.path.isdir(item_path):
            print(f"  [目录] {item}")
        else:
            print(f"  [文件] {item}")

# 3. 尝试直接导入
print_separator("尝试直接导入")
try:
    import qlib_server
    print(f"导入成功! 模块位置: {qlib_server.__file__}")
except ImportError as e:
    print(f"导入失败: {e}")

# 4. 尝试修改sys.path后导入
print_separator("尝试修改sys.path后导入")
if qlib_server_dir not in sys.path:
    sys.path.insert(0, qlib_server_dir)
    print(f"已将 {qlib_server_dir} 添加到sys.path")
else:
    print(f"{qlib_server_dir} 已经在sys.path中")

try:
    # 尝试导入alpha.alpha_generation
    from alpha.alpha_generation import AlphaExtractorFactory, AlphaSignal
    print(f"导入成功! AlphaExtractorFactory位置: {inspect.getfile(AlphaExtractorFactory)}")
    print(f"导入成功! AlphaSignal位置: {inspect.getfile(AlphaSignal)}")
except ImportError as e:
    print(f"导入失败: {e}")

# 5. 尝试使用importlib动态导入
print_separator("尝试使用importlib动态导入")
try:
    # 尝试动态导入
    alpha_module = importlib.import_module("alpha", package=None)
    print(f"动态导入成功! 模块位置: {alpha_module.__file__}")
    
    alpha_generation = importlib.import_module("alpha.alpha_generation", package=None)
    print(f"动态导入成功! 模块位置: {alpha_generation.__file__}")
except ImportError as e:
    print(f"动态导入失败: {e}")

# 6. 尝试使用相对路径导入
print_separator("尝试使用相对路径导入")
try:
    # 获取qlib-server的父目录
    parent_dir = os.path.dirname(qlib_server_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        print(f"已将 {parent_dir} 添加到sys.path")
    
    # 尝试使用相对路径导入
    import qlib_server.alpha.alpha_generation
    print(f"相对路径导入成功!")
except ImportError as e:
    print(f"相对路径导入失败: {e}")

# 7. 尝试创建符号链接
print_separator("尝试创建符号链接")
try:
    # 创建从qlib_server到qlib-server的符号链接
    symlink_path = os.path.join(os.path.dirname(qlib_server_dir), "qlib_server")
    if not os.path.exists(symlink_path):
        # 在Windows上需要管理员权限
        # os.symlink(qlib_server_dir, symlink_path)
        print(f"需要管理员权限才能创建符号链接: {symlink_path} -> {qlib_server_dir}")
        print(f"请手动运行以下命令 (需要管理员权限):")
        print(f"  mklink /D \"{symlink_path}\" \"{qlib_server_dir}\"")
    else:
        print(f"符号链接已存在: {symlink_path}")
        
    # 尝试导入
    if os.path.exists(symlink_path):
        try:
            import qlib_server.alpha.alpha_generation
            print(f"通过符号链接导入成功!")
        except ImportError as e:
            print(f"通过符号链接导入失败: {e}")
except Exception as e:
    print(f"创建符号链接时出错: {e}")

print_separator("测试完成")
