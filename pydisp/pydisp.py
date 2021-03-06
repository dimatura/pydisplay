# -*- coding: utf-8 -*-

import cStringIO as StringIO
import base64
import json
import uuid
import os

from PIL import Image

import matplotlib as mpl
import matplotlib.cm as cm
import numpy as np
import requests


__all__ = ['image',
           'dyplot',
           'send',
           'text',
           'pylab',
           'pane',
           'b64_encode',
           'is_valid_image_mime_type',
           'CONFIG',
           ]


VALID_IMAGE_MIME_TYPES = {'png','gif','bmp','webp','jpeg'}


class CONFIG(object):
    PORT = 8000
    HOSTNAME = 'localhost'


    @staticmethod
    def load_config():
        # TODO what is the right way (TM)
        fname = os.path.join(os.environ['HOME'], '.display', 'config.json')
        if os.path.exists(fname):
            with open(fname, 'r') as f:
                cfg = json.load(f)
            CONFIG.PORT = int(cfg['port'])
            CONFIG.HOSTNAME = cfg['hostname']


    @staticmethod
    def display_url():
        return "http://{:s}:{:d}/events".format(CONFIG.HOSTNAME, CONFIG.PORT)


CONFIG.load_config()


def send(**command):
    """ send command to server """
    command = json.dumps(command)
    headers = {'Content-Type': 'application/text'}
    req = requests.post(CONFIG.display_url(), headers=headers, data=command.encode('ascii'))
    resp = req.content
    return resp is not None


def uid():
    """ return a unique id for a pane """
    return 'pane_{}'.format(uuid.uuid4())


def pane(panetype, win, title, content):
    """ create a pane (formerly window) """
    if win is None:
        win = uid()
    send(command='pane', type=panetype, id=win, title=title, content=content)
    return win


def is_valid_image_mime_type(mt):
    return mt in VALID_IMAGE_MIME_TYPES


def scalar_preprocess(img, **kwargs):
    """ vmin, vmax, clip, cmap """
    vmin = kwargs.get('vmin')
    vmax = kwargs.get('vmax')
    clip = kwargs.get('clip')
    cmap = kwargs.get('cmap', 'jet')
    # TODO customization
    normalizer = mpl.colors.Normalize(vmin, vmax, clip)
    nimg = normalizer(img)
    cmap = cm.get_cmap(cmap)
    cimg = cmap(nimg)[:, :, :3]  # ignore alpha
    simg = (255*cimg).astype(np.uint8)
    return simg


def rgb_preprocess(img):
    if np.issubdtype(img.dtype, np.float):
        # assuming 0., 1. range
        return (img*255).clip(0, 255).astype(np.uint8)
    if not img.dtype == np.uint8:
        raise ValueError('only uint8 or float for 3-channel images')
    return img


def img_encode(img, encoding):
    # ret, data = cv2.imencode('.'+encoding, img)

    if encoding=='jpg':
        encoding = 'jpeg'

    buf = StringIO.StringIO()
    Image.fromarray(img).save(buf, format=encoding)
    data = buf.getvalue()
    buf.close()

    return data


def b64_encode(data, encoding):
    b64data = ('data:image/{};base64,{}'
        .format(encoding, base64.b64encode(data).decode('ascii')))
    return b64data


def pylab(fig, **kwargs):
    """ Display a matplotlib figure. """

    # save figure to buffer
    output = StringIO.StringIO()
    fig.savefig(output, format='png')
    data = output.getvalue()
    output.close()

    encoded = b64_encode(data, 'png')
    pydisp.pane('image',
                win=kwargs.get('win'),
                title=kwargs.get('title'),
                content={
                         'src': encoded,
                         'width': kwargs.get('width'),
                        })
    return win


def image(img, **kwargs):
    """ Display image encoded as an array.

    image(img, [win, title, labels, width, kwargs])
    to_bgr: swap blue and red channels (default False)
    encoding: 'jpg' (default) or 'png'
    kwargs is argument for scalar preprocessing
    """

    to_bgr = kwargs.get('to_bgr', False)

    if img.ndim not in (2, 3):
        raise ValueError('image should be 2 (gray) or 3 (rgb) dimensional')

    assert img.ndim == 2 or img.ndim == 3

    if img.ndim == 3:
        img = rgb_preprocess(img)
    else:
        img = scalar_preprocess(img, **kwargs)

    if to_bgr:
        img = img[...,[2, 1, 0]]

    encoding = kwargs.get('encoding', 'jpg')
    data = img_encode(img, encoding)
    encoded = b64_encode(data, encoding)

    return pane('image',
                kwargs.get('win'),
                kwargs.get('title'),
                content={
                    'src': encoded,
                    'labels': kwargs.get('labels'),
                    'width': kwargs.get('width'),
                })


def text(txt, **kwargs):
    win = kwargs.get('win') or uid()
    title = kwargs.get('title') or 'text'
    return pane('text',
                win,
                title,
                content=txt)


def dyplot(data, **kwargs):
    """ Plot data as line chart with dygraph
    Params:
        data: either a 2-d numpy array or a list of lists.
        win: pane id
        labels: list of series names, first series is always the X-axis
        see http://dygraphs.com/options.html for other supported options
    """
    win = kwargs.get('win') or uid()

    dataset = {}
    if type(data).__module__ == np.__name__:
        dataset = data.tolist()
    else:
        dataset = data

    # clone kwargs into options
    options = dict(kwargs)
    options['file'] = dataset
    if options.get('labels'):
        options['xlabel'] = options['labels'][0]

    # Don't pass our options to dygraphs.
    options.pop('win', None)

    return pane('plot', kwargs.get('win'), kwargs.get('title'), content=options)
