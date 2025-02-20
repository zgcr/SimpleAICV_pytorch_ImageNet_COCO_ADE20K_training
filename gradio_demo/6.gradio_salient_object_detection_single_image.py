import os
import sys
import warnings

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(FILE_DIR)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
warnings.filterwarnings('ignore')

import cv2
import gradio as gr
import random
import numpy as np
from PIL import Image

import torch

from simpleAICV.salient_object_detection import models
from simpleAICV.salient_object_detection.common import load_state_dict

seed = 0
model_name = 'convformerm36_pfan_segmentation'

trained_model_path = '/root/autodl-tmp/pretrained_models/pfan_segmentation_train_on_salient_object_detection_dataset/convformerm36_pfan_segmentation-metric0.887.pth'
input_image_size = 832
clip_threshold = 0.2

os.environ['PYTHONHASHSEED'] = str(seed)
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

assert model_name in models.__dict__.keys(), 'Unsupported model!'
model = models.__dict__[model_name](**{})

if trained_model_path:
    load_state_dict(trained_model_path, model)
else:
    print('No pretrained model load!')
model.eval()


def preprocess_image(image, resize):
    # PIL image(RGB) to opencv image(RGB)
    image = np.asarray(image).astype(np.float32)

    origin_image = image.copy()
    h, w, _ = origin_image.shape

    origin_size = [h, w]

    factor = resize / max(h, w)

    resize_h, resize_w = int(round(h * factor)), int(round(w * factor))
    image = cv2.resize(image, (resize_w, resize_h))

    pad_w = 0 if resize_w % 32 == 0 else 32 - resize_w % 32
    pad_h = 0 if resize_h % 32 == 0 else 32 - resize_h % 32

    padded_img = np.zeros((resize_h + pad_h, resize_w + pad_w, 3),
                          dtype=np.float32)
    padded_img[:resize_h, :resize_w, :] = image
    scale = factor

    # normalize
    padded_img = padded_img.astype(np.float32) / 255.

    scaled_size = [resize_h, resize_w]

    return origin_image, padded_img, scale, scaled_size, origin_size


@torch.no_grad
def predict(image):
    origin_image, resized_img, scale, scaled_size, origin_size = preprocess_image(
        image, input_image_size)
    resized_img = torch.tensor(resized_img).permute(2, 0, 1).unsqueeze(0)

    with torch.no_grad():
        outputs = model(resized_img)

    outputs = outputs[0]
    outputs = torch.squeeze(outputs, dim=0)

    outputs = outputs.numpy()
    outputs = outputs[0:scaled_size[0], 0:scaled_size[1]]

    outputs = cv2.resize(outputs, (origin_size[1], origin_size[0]))
    outputs[outputs < clip_threshold] = 0
    outputs = (outputs * 255.).astype('uint8')
    origin_image = cv2.cvtColor(origin_image, cv2.COLOR_RGB2BGR)
    origin_image = origin_image.astype('uint8')

    b_channel, g_channel, r_channel = cv2.split(origin_image)
    combine_image = cv2.merge([r_channel, g_channel, b_channel, outputs])

    return combine_image


title = '显著性检测demo'
description = '选择一张图片进行显著性检测吧！'
inputs = gr.Image(type='pil')
outputs = gr.Image(type='pil')
gradio_demo = gr.Interface(
    fn=predict,
    title=title,
    description=description,
    inputs=inputs,
    outputs=outputs,
    examples=[
        'test_salient_object_detection_images/HRSOD_1221805113_d07ea11ee6_o.jpg',
        'test_salient_object_detection_images/HRSOD_10113619975_0b1690a93d_k.jpg',
        'test_salient_object_detection_images/HRSOD_10818344253_b21ff4aa80_o.jpg',
        'test_salient_object_detection_images/HRSOD_11866374765_54b2ff86de_o.jpg',
        'test_salient_object_detection_images/HRSOD_12554681053_ec00ba4a3d_o.jpg',
    ])
# local website: http://127.0.0.1:6006/
gradio_demo.launch(share=True,
                   server_name='0.0.0.0',
                   server_port=6006,
                   show_error=True)
