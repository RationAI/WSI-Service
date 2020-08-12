class Debug(object):
    DEBUG = True
    TESTING = False
    JSON_AS_ASCII = True
    INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS = 600
    COMPRESS_RAW = False

class Production(Debug):
    DEBUG = False
