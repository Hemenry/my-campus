"""开发入口：python wsgi.py 或 flask --app wsgi run

是否开启调试器由 FLASK_DEBUG 控制（.env 里本地默认 1），避免把 Werkzeug
调试器带到公网（debugger 可被用来执行任意代码）。
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_RUN_PORT", "5000")),
        debug=app.debug,
    )
