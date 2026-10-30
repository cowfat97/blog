#!/usr/bin/env python3
"""兼容旧命令：导航现在由构建钩子生成，不再回写配置。

设计说明：../.mkdocs/REFACTOR.md
"""
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    raise SystemExit(subprocess.call([sys.executable, '-m', 'mkdocs', 'build', '-f', str(root / '.mkdocs/mkdocs.yml')], cwd=root))
