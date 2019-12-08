# -*- coding: utf-8 -*-
import platform
from email.mime.multipart import MIMEMultipart

import robot
from flask_script import Manager
from flask import current_app
import pdfkit

from auto.configuration import Config
from auto.www.init_app import create_app, get_app

__author__ = "苦叶子"

"""

公众号: 开源优测

Email: lymking@foxmail.com

"""
import sys
import codecs
from flask import current_app, session, url_for
from flask_mail import Mail, Message
import threading
from threading import Thread
import multiprocessing
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import json

from robot.api import TestSuiteBuilder, ResultWriter, ExecutionResult,TestSuite

from utils.file import exists_path, make_nod, write_file, read_file, mk_dirs


def robot_job(app, name, username):

    with app.app_context():
        project = app.config["AUTO_HOME"] + "/workspace/%s/%s" % (username, name)
        output = app.config["AUTO_HOME"] + "/jobs/%s/%s" % (username, name)
        if not is_run(app, project):
            p = multiprocessing.Process(target=robot_run, args=(username, name, project, output))
            p.start()
            app.config["AUTO_ROBOT"].append({"name": project, "process": p})
            print("-+" * 15)
            print(app.config["AUTO_ROBOT"])
            print("-+" * 15)


def robot_run(username, name, project, output):

    if not exists_path(output):
        mk_dirs(output)

    suite = TestSuiteBuilder().build(project)

    (out, index) = reset_next_build_numb(output)

    result = suite.run(output_directory=out,
                       output=out + "/output.xml",
                       debugfile=out + "/debug.txt",
                       loglevel="TRACE")

    # reset_last_status(result, output, index)

    # Report and xUnit files can be generated based on the result object.
    # ResultWriter(result).write_results(report=out + '/report.html', log=out + '/log.html')
    detail_result = ExecutionResult(out + "/output.xml")

    # detail_result.save(out + "/output_new.xml")
    reset_last_status(detail_result, output, index)

    # Report and xUnit files can be generated based on the result object.
    ResultWriter(detail_result).write_results(report=out + '/report.html', log=out + '/log.html')

    send_robot_report(username, name, index, detail_result, out)
def robot_run_cli(username, project,test_case_name, case_file_path, output):
    if not exists_path(output):
        mk_dirs(output)
    (out, index) = reset_next_build_numb(output)
    import os
    retval = os.getcwd()
    os.chdir(os.path.join(Config.AUTO_WORKSPACE,username,project))
    robot.run_cli(['--test',test_case_name,'--outputdir',out,case_file_path])
    os.chdir(os.getcwd())
    detail_result = ExecutionResult(out + "/output.xml")

    # detail_result.save(out + "/output_new.xml")
    reset_last_status(detail_result, output, index)


    # detail_result = ExecutionResult(out + "/output.xml")

    # detail_result.save(out + "/output_new.xml")
    # reset_last_status(detail_result, output, index)

    # Report and xUnit files can be generated based on the result object.
    # ResultWriter(detail_result).write_results(report=out + '/report.html', log=out + '/log.html')

    send_robot_report(username, name, index, out + '/report.html', out)

def reset_next_build_numb(output):
    next_build_number = output + "/nextBuildNumber"
    index = 1
    data = "%d" % (index + 1)
    if not exists_path(next_build_number):
        make_nod(next_build_number)
    else:
        index = int(read_file(next_build_number)["data"])
        data = "%d" % (index + 1)
    write_file(next_build_number, data)

    out = output + "/%d" % index
    if not exists_path(output):
        mk_dirs(output)

    return (out, index)


def reset_last_status(result, output, index):
    stats = result.statistics
    fail = stats.total.critical.failed

    last_fail = output + "/lastFail"
    last_passed = output + "/lastPassed"
    data = "%d" % index

    if fail != 0:
        if not exists_path(last_fail):
            make_nod(last_fail)

        write_file(last_fail, data)
    else:
        if not exists_path(last_passed):
            make_nod(last_passed)
        write_file(last_passed, data)


def remove_robot(app):
    lock = threading.Lock()
    lock.acquire()
    for p in app.config["AUTO_ROBOT"]:
        if not p["process"].is_alive():
            app.config["AUTO_ROBOT"].remove(p)
            break
    lock.release()


def stop_robot(app, name):
    lock = threading.Lock()
    lock.acquire()
    for p in app.config["AUTO_ROBOT"]:
        if name == p["name"]:
            if p["process"].is_alive():
                p["process"].terminate()
                time.sleep(0.2)
                app.config["AUTO_ROBOT"].remove(p)
                break

    lock.release()

    return True


def is_run(app, name):
    remove_robot(app)
    for p in app.config["AUTO_ROBOT"]:
        if name == p["name"]:
            return True

    return False


def send_robot_report(username, name, task_no, result, output):
    app = get_app()
    with app.app_context():
        print(current_app.name)


        build_msg = "<font color='green'>Success</font>"
        if result.statistics.total.critical.failed != 0:
            build_msg = "<font color='red'>Failure</font>"

        report_url = url_for("routes.q_view_report",
                             _external=True,
                             username=username,
                             project=name,
                             task=task_no)
        msg = MIMEMultipart()

        # 邮件正文内容
        msg.attach(MIMEText("""
                    项目名称：%s<hr>
                    构建编号: %s<hr>
                    构建状态: %s<hr>
                    通过用例: %s<hr>
                    失败用例: <font color='red'>%s</font><hr>
                    持续时间: %s毫秒<hr>
                    详细报告: <a href='%s'>%s</a><hr>
                    (本邮件是程序自动下发的，请勿回复！)""" %
                       (result.statistics.suite.stat.name,
                        task_no,
                        build_msg,
                        result.statistics.total.critical.passed,
                        result.statistics.total.critical.failed,
                        result.suite.elapsedtime,
                        report_url, report_url,
                        # codecs.open(output + "/debug.txt", "r", "utf-8").read().replace("\n", "<br>")
                        ),
                       "html", "utf-8"))

        pdfkit.from_file(output + "/report.html", output + "/report.pdf", )

        system = platform.system()
        encode = 'gbk' if system is 'Windows' else 'utf-8'
        pdf_att = MIMEText(open(output + "/report.pdf", 'rb').read(), 'base64', encode)
        pdf_att["Content-Type"] = 'application/octet-stream'
        pdf_att["Content-Disposition"] = 'attachment; filename="report.pdf"'
        msg.attach(pdf_att)


        debug_att = MIMEText(open(output + "/debug.txt", 'rb').read(), 'base64', 'utf-8')
        debug_att["Content-Type"] = 'application/octet-stream'
        debug_att["Content-Disposition"] = 'attachment; filename="debug.txt"'
        msg.attach(debug_att)

        html_att = MIMEText(open(output + "/report.html", 'rb').read(), 'base64', 'utf-8')
        html_att["Content-Type"] = 'application/octet-stream'
        html_att["Content-Disposition"] = 'attachment; filename="report_test.html"'
        msg.attach(html_att)


        msg["Subject"] = Header("AutoLink通知消息", "utf-8")

        # try:
        user_path = Config.AUTO_HOME + "/users/%s/config.json" % username
        app.logger.debug(user_path)
        user_conf = json.load(codecs.open(user_path, 'r', 'utf-8'))
        for p in user_conf["data"]:
            if p["name"] == name:
                if result.statistics.total.critical.failed != 0:
                    msg["To"] = p["fail_list"]
                else:
                    msg["To"] = p["success_list"]
                break

        conf_path = app.config["AUTO_HOME"] + "/auto.json"
        config = json.load(codecs.open(conf_path, 'r', 'utf-8'))
        msg["From"] = config["smtp"]["username"]
        app.logger.debug(config)
        app.logger.debug(config["smtp"]["server"])
        if config["smtp"]["ssl"]:
            smtpobj =smtplib.SMTP_SSL(host=config["smtp"]["server"]).connect(host=config["smtp"]["server"], port=config["smtp"]["port"])
        else:
            smtpobj = smtplib.SMTP(host=config["smtp"]["server"])

        # 连接至服务器



        smtpobj.connect(host=config["smtp"]["server"], port=config["smtp"]["port"])
        # 登录
        smtpobj.login(config["smtp"]["username"], config["smtp"]["password"])
        # 发送邮件
        smtpobj.sendmail(msg["From"], msg["To"].split(","), msg.as_string().encode("utf8"))
        # smtpobj.sendmail(msg["From"], msg["To"].split(","), msg.as_string())
        # 断开连接
        smtpobj.quit()
        # except Exception as e:
        #     print("邮件发送错误: %s" % e)
        print(current_app.name)

    # with staticVar.initapp.app_context():
    #     app = current_app._get_current_object()
    #     build_msg = "<font color='green'>Success</font>"
    #     if result.statistics.total.critical.failed != 0:
    #         build_msg = "<font color='red'>Failure</font>"
    #
    #     report_url = url_for("routes.q_view_report",
    #                          _external=True,
    #                          username=username,
    #                          project=name,
    #                          task=task_no)
    #     msg = MIMEText("""Hello, %s<hr>
    #                 项目名称：%s<hr>
    #                 构建编号: %s<hr>
    #                 构建状态: %s<hr>
    #                 持续时间: %s毫秒<hr>
    #                 详细报告: <a href='%s'>%s</a><hr>
    #                 构建日志: <br>%s<hr><br><br>
    #                 (本邮件是程序自动下发的，请勿回复！)""" %
    #                    (username,
    #                     result.statistics.suite.stat.name,
    #                     task_no,
    #                     build_msg,
    #                     result.suite.elapsedtime,
    #                     report_url, report_url,
    #                     codecs.open(output + "/debug.txt", "r", "utf-8").read().replace("\n", "<br>")
    #                     ),
    #                    "html", "utf-8")
    #
    #     msg["Subject"] = Header("AutoLink通知消息", "utf-8")
    #
    #     try:
    #         user_path = app.config["AUTO_HOME"] + "/users/%s/config.json" % username
    #         user_conf = json.load(codecs.open(user_path, 'r', 'utf-8'))
    #         for p in user_conf["data"]:
    #             if p["name"] == name:
    #                 if result.statistics.total.critical.failed != 0:
    #                     msg["To"] = p["fail_list"]
    #                 else:
    #                     msg["To"] = p["success_list"]
    #                 break
    #
    #         conf_path = app.config["AUTO_HOME"] + "/auto.json"
    #         config = json.load(codecs.open(conf_path, 'r', 'utf-8'))
    #         msg["From"] = config["smtp"]["username"]
    #         if config["smtp"]["ssl"]:
    #             smtp = smtplib.SMTP_SSL()
    #         else:
    #             smtp = smtplib.SMTP()
    #
    #         # 连接至服务器
    #         smtp.connect(config["smtp"]["server"], int(config["smtp"]["port"]))
    #         # 登录
    #         smtp.login(config["smtp"]["username"], config["smtp"]["password"])
    #         # 发送邮件
    #         smtp.sendmail(msg["From"], msg["To"].split(","), msg.as_string().encode("utf8"))
    #         # 断开连接
    #         smtp.quit()
    #     except Exception as e:
    #         print("邮件发送错误: %s" % e)


class RobotRun(threading.Thread):
    def __init__(self, name, output, lock, executor="auto"):
        threading.Thread.__init__(self)
        self.lock = lock
        self.project = name
        self.output = output
        self.executor = executor
        self.suite = None
        self.result = None

    def run(self):
        #lock = threading.Lock()

        # self.lock.acquire()
        if not exists_path(self.output):
            mk_dirs(self.output)

        self.suite = TestSuiteBuilder().build(self.project)

        (output, index) = self.reset_next_build_numb()

        self.setName(output)

        self.result = self.suite.run(output_directory=output,
                                     output=output + "/output.xml",
                                     debugfile=output + "/debug.txt",
                                     loglevel="TRACE")

        # self.reset_last_status(index)

        # Report and xUnit files can be generated based on the result object.
        # ResultWriter(self.result).write_results(report=output + '/report.html', log=output + '/log.html')

        # self.lock.release()

        # Generating log files requires processing the earlier generated output XML.
        # ResultWriter(self.output + '/output.xml').write_results()

        self.result = ExecutionResult(out + "/output.xml")

        self.reset_last_status(self.result, output, index)

        # Report and xUnit files can be generated based on the result object.
        ResultWriter(self.result).write_results(report=out + '/report.html', log=out + '/log.html')

    def reset_next_build_numb(self):

        next_build_number = self.output + "/nextBuildNumber"
        index = 1
        data = "%d" % (index + 1)
        if not exists_path(next_build_number):
            make_nod(next_build_number)
        else:
            index = int(read_file(next_build_number)["data"])
            data = "%d" % (index + 1)
        write_file(next_build_number, data)

        output = self.output + "/%d" % index
        if not exists_path(output):
            mk_dirs(output)

        return (output, index)

    def reset_last_status(self, index):
        stats = self.result.statistics
        fail = stats.total.critical.failed

        lock = threading.Lock()

        lock.acquire()
        last_fail = self.output + "/lastFail"
        last_passed = self.output + "/lastPassed"
        data = "%d" % index

        if fail != 0:
            if not exists_path(last_fail):
                make_nod(last_fail)

            write_file(last_fail, data)
        else:
            if not exists_path(last_passed):
                make_nod(last_passed)
            write_file(last_passed, data)

        lock.release()