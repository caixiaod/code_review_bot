# -*- coding: utf-8 -*-

import os


def export_package():
    """
    Export the dependencies of the current project.
    """
    os.system("pipreqs ./ --encoding='utf-8' --force")


def input_package():
    """
    Install the dependencies of the current project.
    """
    os.system("pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple")


if __name__ == '__main__':
    input_package()
