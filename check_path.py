import sys
import os

print("--- 当前工作目录 (Current Working Directory) ---")
print(os.getcwd())
print("\n--- Python 模块搜索路径 (sys.path) ---")
for path in sys.path:
    print(path)