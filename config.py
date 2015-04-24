import os
import jinja2

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DM_API_URL = None
    DM_API_AUTH_TOKEN = None
    DEBUG = False
    SECRET_KEY = 'this is not secret'
    STATIC_URL_PATH = '/supplier/static'
    ASSET_PATH = STATIC_URL_PATH + '/'
    BASE_TEMPLATE_DATA = {
        'asset_path': ASSET_PATH,
        'header_class': 'with-proposition'
    }

    @staticmethod
    def init_app(app):
        repo_root = os.path.abspath(os.path.dirname(__file__))
        template_folders = [
            os.path.join(repo_root,
                         'bower_components/govuk_template/views/layouts'),
            os.path.join(repo_root, 'app/templates')
        ]
        jinja_loader = jinja2.FileSystemLoader(template_folders)
        app.jinja_loader = jinja_loader


class Test(Config):
    DEBUG = True
    DM_API_AUTH_TOKEN = 'test'
    DM_API_URL = 'http://localhost'


class Development(Config):
    DEBUG = True,


class Live(Config):
    DEBUG = False


config = {
    'development': Development,
    'preview': Development,
    'staging': Live,
    'production': Live,
    'test': Test,
}
