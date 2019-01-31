#!/usr/bin/env python
# -*- coding: utf-8 -*-

from web import app


if __name__ == '__main__':
    app.run(port=8000, workers=1, debug=False, access_log=False)
