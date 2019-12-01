# -*- coding: utf-8 -*-
import staticVar

__author__ = "苦叶子"

"""

公众号: 开源优测

Email: lymking@foxmail.com

"""
import os
import sys

from flask_script import Manager
from flask import g

from auto.www.app import  load_all_task
from auto.www.init_app import create_app
from auto.settings import HEADER
from utils.help import check_version

if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
    os.environ["PATH"] = os.environ["PATH"] + ":" + os.getcwd() + "/driver"
else:
    os.environ["PATH"] = os.environ["PATH"] + ";" + os.getcwd() + "/driver"

print(HEADER)

app = create_app('default')
manager = Manager(app)






if __name__ == '__main__':

    # check_version()

    load_all_task(app)

    manager.run()
