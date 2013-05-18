import sys
import lzmaffi


# just like psyopg2ct
def register():
    sys.modules['lzma'] = lzmaffi
