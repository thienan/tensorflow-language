#!/usr/bin/python
#coding=utf-8

import web
import json
import subprocess

urls = (
    '/api', 'Api',
    )
app = web.application(urls,globals())

class Api:
    def POST(self):  
        i = web.input().data
        data = json.loads(i)
        return data[0]

if __name__ == "__main__":
    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
    app.run()