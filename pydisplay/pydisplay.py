# -*- coding: utf-8 -*-

import base64
import json
import uuid

import matplotlib as mpl
import matplotlib.cm as cm
import numpy as np
import cv2
import requests

__all__ = ['image',
           'images',
           'plot',
           'send',
           'text']


# TODO some configuration mechanism
URL = 'http://localhost:8000/events'


def uid():
    """ return a unique id for a pane """
    return 'pane_{}' % uuid.uuid4()


def send(**command):
    """ send command to server """
    command = json.dumps(command)
    headers = {'Content-Type' : 'application/text'}
    req = requests.post(URL, headers=headers, data=command.encode('ascii'))
    resp = req.content
    return resp is not None


def scalar_preprocess(img, **kwargs):
    """ vmin, vmax, clip, cmap """
    vmin = kwargs.get('vmin', None)
    vmax = kwargs.get('vmax', None)
    clip = kwargs.get('clip', None)
    cmap = kwargs.get('jet', None)
    # TODO customization
    normalizer = mpl.colors.Normalizer(vmin, vmax, clip)
    nimg = normalizer(img)
    cmap = cm.get_cmap(cmap)
    cimg = cmap(nimg)[:,:,:3] # ignore alpha
    simg = (255*cimg).astype(np.uint8)
    return simg


def rgb_preprocess(img):
    if np.issubdtype(img.dtype, np.float):
        # assuming 0., 1. range
        return (img*255).clip(0, 255).astype(np.uint8)
    if not img.dtype==np.uint8:
        raise ValueError('only uint8 or float for 3-channel images')
    return img


def encode(img, **kwargs):
    encoding = kwargs.get('encoding', 'jpg')
    if encoding=='jpg':
        ret, data = cv2.imencode('.jpg', img)
    elif encoding=='png':
        ret, data = cv2.imencode('.png', img)[1]
    else:
        raise ValueError('unknown encoding')
    imgdata = 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
    return imgdata


def image(img, **kwargs):
    """ image(img, [win, title, labels, width, kwargs])
    to_bgr: converts to bgr, if encoded as rgb (default True because opencv).
    encoding: 'jpg' (default) or 'png'
    kwargs is argument for scalar preprocessing
    """

    win = kwargs.get('win', uid())
    to_bgr = kwargs.get('to_bgr', True)

    if img.ndim not in (2, 3):
        raise ValueError('image should be 2 (gray) or 3 (rgb) dimensional')

    assert img.ndim == 2 or img.ndim == 3

    if img.ndim==3:
        img = rgb_preprocess(img)
    else:
        img = scalar_preprocess(img, **kwargs)

    if to_bgr:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    encoded = encode(img, **kwargs)

    send(command='image', id=win, src=encoded,
         labels=kwargs.get('labels'),
         width=kwargs.get('width'),
         title=kwargs.get('title'))
    return win


def text(txt, **kwargs):
    win = kwargs.get('win') or uid()
    title = kwargs.get('title') or 'text'
    send(command='text', id=win, title=title, text=txt)


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
    if type(data).__module__ == numpy.__name__:
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

    send(command='plot', id=win, title=kwargs.get('title'), options=options)
    return win
