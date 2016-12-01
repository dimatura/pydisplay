
import numpy as np
import pydisp

pydisp.dyplot([[x, x**2] for x in range(10)], title='dyplot', win='w0')

pydisp.text('foo', title='text', win='w1')

img = (np.random.random((32, 32, 3))*255).astype('u1')
pydisp.image(img, title='random image', win='w2')

img = np.zeros((32, 32, 3), dtype='u1')
img[:, :, 0] = 255
pydisp.image(img, title='blue image', win='w3')
