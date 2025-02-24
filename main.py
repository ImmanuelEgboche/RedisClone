if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    from server import Server
    Server().run()