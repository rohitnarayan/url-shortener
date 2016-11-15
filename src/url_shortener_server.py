#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
A RESTful web service that shorten long URLs to short slugs (see "Usage"
section in README.md)
"""

import json
import logging
from flask import Flask, Response, request
from url_shortener import URLShortener


class URLShortenerServer(object):

    def __init__(self, config):
        self._app = Flask(__name__)
        self._config = config
        self._root_url = self._build_root_url()
        self._add_routes()
        self._shortener = URLShortener(config)

    def shorten(self, version):
        """Handles the `POST /:version/shorten` request. Status goes to
        header, data goes to body in JSON.

        Status codes are:
            - 200 OK
            - 400 BAD REQUEST (invalid parameter)
            - 500 INTERNAL SERVER ERROR (unknown exception)
            - 501 NOT IMPLEMENTED (not supported API)
        """
        if version != 'v1':
            return self._response(501)

        try:
            request_data = request.get_json()
            if request_data is None:
                return self._response(400)
            url = request_data.get('url', '')
            if not self._validate_url(url):
                return self._response(400)

            slug = self._shortener.shorten(url)
            data = {'short': '{}/{}'.format(self._root_url, slug)}
            return self._response(200, data)
        except Exception as e:
            print(e)
            return self._response(500)

    def original(self, version):
        """Handles the `GET /:version/original` request. Status goes to
        header, data goes to body in JSON.

        Status codes are:
            - 200 OK
            - 400 BAD REQUEST (invalid input)
            - 404 NOT FOUND (Given slug not found)
            - 500 INTERNAL SERVER ERROR (unknown exception)
            - 501 NOT IMPLEMENTED (not supported API)
        """
        if version != 'v1':
            return self._response(501)

        try:
            request_data = request.get_json()
            if request_data is None:
                return self._response(400)
            short = request_data.get('short', '')
            slug = self._get_slug(short)
            if not slug:
                return self._response(400)

            url = self._shortener.expand(slug)
            data = {'original': url}
            return self._response(200, data)
        except Exception as e:
            print(e)
            return self._response(500)

    def run(self):
        self._app.run(host=self._config['api']['bindAddress'],
                      port=self._config['api']['port'])

    def _add_routes(self):
        self._app.add_url_rule('/<version>/shorten',
                               endpoint='shorten',
                               view_func=self.shorten,
                               methods=['POST'])
        self._app.add_url_rule('/<version>/original',
                               endpoint='original',
                               view_func=self.original,
                               methods=['GET'])

    def _response(self, status, data=None):
        return Response(json.dumps(data), status=status,
                        mimetype='application/json')

    def _validate_url(self, url):
        # TODO: better validator according to tools.ietf.org/html/rfc3696, it
        # should accept uppercased schema and hostname
        return url.startswith('http://') or url.startswith('https://')

    def _get_slug(self, short):
        """Extract the slug part, return '' if short url is not under our
        domain or slug is missing.  TODO: validate the slug, it should be
        URL-ready
        """
        prefix = '{}/'.format(self._root_url)
        if not short.startswith(prefix):
            return ''
        return short[len(prefix):]

    def _build_root_url(self):
        # TODO: handle https schema, or we change the API to return the slug
        if self._config['api']['port'] == 80:
            return 'http://{}'.format(self._config['api']['serverName'])
        else:
            return 'http://{}:{}'.format(self._config['api']['serverName'],
                                         self._config['api']['port'])

    def _test_client(self):
        return self._app.test_client()


if __name__ == '__main__':  # pragma: no cover
    from optparse import OptionParser

    parser = OptionParser(usage='%prog [options]', add_help_option=False)
    parser.add_option('--help',
                      action='store_true',
                      help='Show this help message')
    parser.add_option('-c', '--config',
                      default='/opt/url-shortener/config.json',
                      help=('Config file to read, default is '
                            '/opt/url-shortener/config.json'))
    opts, _ = parser.parse_args()

    if opts.help:
        parser.print_help()

    with open(opts.config) as config_file:
        config = json.load(config_file)

    URLShortenerServer(config).run()
