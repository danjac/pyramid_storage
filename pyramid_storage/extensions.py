TEXT = ('txt',)
DOCUMENTS = tuple('pdf rtf odf ods gnumeric abw doc docx xls xls'.split())
IMAGES = tuple('jpg jpe jpeg png gif svg bmp tiff'.split())
AUDIO = tuple('wav mp3 aac ogg oga flac'.split())
VIDEO = tuple('mpeg 3gp avi divx dvr flv mp4 wmv'.split())
DATA = tuple('csv ini json plist xml yaml yml'.split())
SCRIPTS = tuple('js php pl py rb sh'.split())
ARCHIVES = tuple('gz bz2 zip tar tgz txz 7z'.split())
EXECUTABLES = tuple('so exe dll'.split())
DEFAULT = DOCUMENTS + TEXT + IMAGES + DATA

GROUPS = dict((
    ('documents', DOCUMENTS),
    ('text', TEXT),
    ('images', IMAGES),
    ('audio', AUDIO),
    ('video', VIDEO),
    ('data', DATA),
    ('scripts', SCRIPTS),
    ('archives', ARCHIVES),
    ('executables', EXECUTABLES),
    ('default', DEFAULT)
))


def resolve_extensions(extensions):
    """
    Splits extensions string into a set of extensions
    ("jpg", "png" etc). If extensions string contains
    a known group e.g. "images" then fetches extensions
    for that group. Separate groups with "+".

    :param extensions: a string of extensions and/or group names
    """
    rv = set()
    groups = extensions.split('+')
    for group in groups:
        if group in GROUPS:
            rv.update(GROUPS[group])
        else:
            for ext in group.split():
                rv.add(ext.lower())
    return rv


