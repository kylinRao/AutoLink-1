
# -*- coding: utf-8 -*-

from flask import Flask

from auto.configuration import config

import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
class static:
    is_init = None
def create_app(config_name):
    if not static.is_init:
        static.is_init = True
        # 默认日志等级的设置
        logging.basicConfig(level=logging.DEBUG)
        # 创建日志记录器，指明日志保存路径,每个日志的大小，保存日志的上限
        file_log_handler = RotatingFileHandler('WarningLogs.log', maxBytes=1024 * 1024, backupCount=10)
        # 设置日志的格式                   发生时间    日志等级     日志信息文件名      函数名          行数        日志信息
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')
        # 将日志记录器指定日志的格式
        file_log_handler.setFormatter(formatter)
        # 日志等级的设置
        # file_log_handler.setLevel(logging.WARNING)
        # 为全局的日志工具对象添加日志记录器

        app.logger.addHandler(file_log_handler)
        app.config.from_object(config[config_name])
        config[config_name].init_app(app)



        # mail.init_app(app)

        # app.config["MAIL"] = mail



        # for blueprints
        from .blueprints import routes as routes_blueprint
        app.register_blueprint(routes_blueprint)

        from .api import api_bp as api_blueprint
        app.register_blueprint(api_blueprint, url_prefix='/api/v1')

        if app.config['SSL_REDIRECT']:
            from flask_sslify import SSLify
            sslify = SSLify(app)
    return app
def get_app():
    return app