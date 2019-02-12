#!/usr/bin/env python
# -*- coding: utf-8 -*-

# connection url will contains login data, if the data display in web, use shadow_password to
# shadow the sensitive infomation
# example: redis://:password@host:port/db -> redis://host:port/db
# example: mysql://user:password@host:port/db -> mysql://host:port/db
def shadow_password(self, url):
    return ''.join([url[:8], url[url.index('@') + 1:]]) if '@' in url else url
