import re

def sanitize_id(id):
    id_no_invalid_chars = re.sub('[^A-Za-z0-9\s_-]', '_', id)
    id_no_invalid_chars_no_multiple_underscores = re.sub('_+', '_', id_no_invalid_chars)
    return id_no_invalid_chars_no_multiple_underscores