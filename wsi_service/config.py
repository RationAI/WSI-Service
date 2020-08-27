class Debug(object):
    DEBUG = True
    JSON_AS_ASCII = True
    INACTIVE_HISTO_IMAGE_TIMEOUT_SECONDS = 600

class Production(Debug):
    DEBUG = False
    MAX_RETURNED_REGION_SIZE = 6250000 # 2500 x 2500
