"""蓝图注册入口。"""

from flask import Flask

from . import auth, comments, english, mistakes, notifications, posts, stats, uploads

BLUEPRINTS = (
    auth.bp,
    posts.bp,
    comments.bp,
    english.bp,
    mistakes.bp,
    notifications.bp,
    uploads.bp,
    stats.bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
