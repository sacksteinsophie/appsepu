#
# Copyright 2018-2021 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from maxfw.core import MAX_API, PredictAPI, CustomMAXAPI
from flask_restx import fields
from werkzeug.datastructures import FileStorage
from core.model import ModelWrapper
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from flask_restx import fields
from PIL import Image
from flask import send_file
from tempfile import NamedTemporaryFile
from shutil import copyfileobj
from os import remove
model_label = MAX_API.model('ModelLabel', {
    'id': fields.String(required=True, description='Class label identifier'),
    'name': fields.String(required=True, description='Class label'),
})

labels_response = MAX_API.model('LabelsResponse', {
    'count': fields.Integer(required=True,
                            description='Number of class labels returned'),
    'labels': fields.List(fields.Nested(model_label),
                          description='Class labels that can be predicted by '
                                      'the model')
})

model_wrapper = ModelWrapper()


class ModelLabelsAPI(CustomMAXAPI):

    @MAX_API.doc('labels')
    @MAX_API.marshal_with(labels_response)
    def get(self):
        """Return the list of labels that can be predicted by the model"""
        return {
            'labels': model_wrapper.categories,
            'count': len(model_wrapper.categories)
        }


input_parser = MAX_API.parser()
input_parser.add_argument('image', type=FileStorage, location='files', required=True,
                          help='An image file (encoded as PNG or JPG/JPEG)')
input_parser.add_argument('threshold', type=float, default=0.7,
                          help='Probability threshold for including a detected object in the response in the range '
                               '[0, 1] (default: 0.7). Lowering the threshold includes objects the model is less '
                               'certain about.')


label_prediction = MAX_API.model('LabelPrediction', {
    'label_id': fields.String(required=False, description='Class label identifier'),
    'label': fields.String(required=True, description='Class label'),
    'probability': fields.Float(required=True, description='Predicted probability for the class label'),
    'detection_box': fields.List(fields.Float(required=True), description='Coordinates of the bounding box for '
                                                                          'detected object. Format is an array of '
                                                                          'normalized coordinates (ranging from 0 to 1'
                                                                          ') in the form [ymin, xmin, ymax, xmax].')
})




class ModelPredictAPI(PredictAPI):

    @MAX_API.doc('predict')
    @MAX_API.expect(input_parser)

    def post(self):
        """Make a prediction given input data"""
        result = {'status': 'error'}

        args = input_parser.parse_args()
        threshold = args['threshold']
        image_data = args['image'].read()
        image = model_wrapper._read_image(image_data)
        label_preds = model_wrapper._predict(image, threshold)

        result['predictions'] = label_preds
        result['status'] = 'ok'
        file_loc = open('./api/data.png', 'wb')
        model_response=result
        file_loc.write(image_data)
        img_path = './api/data.png'
        image = Image.open(img_path)
        image_width, image_height = image.size
        # Create figure and axes
        fig, ax = plt.subplots()
        # Set larger figure size
        fig.set_dpi(600)
        # Display the image
        plt.imshow(image)

        # Set up the color of the bounding boxes and text
        color = '#00FF00'
        # For each object, draw the bounding box and predicted class together with the probability
        for prediction in model_response['predictions']:
            bbox = prediction['detection_box']
            # Unpack the coordinate values
            y1, x1, y2, x2 = bbox
            # Map the normalized coordinates to pixel values: scale by image height for 'y' and image width for 'x'
            y1 *= image_height
            y2 *= image_height
            x1 *= image_width
            x2 *= image_width
            # Format the class probability for display
            probability = '{0:.4f}'.format(prediction['probability'])
            # Format the class label for display
            if prediction['label'] == 'person' or 'ell' in str(prediction['label']) or 'able' in str(prediction['label']):
                label = '{}'.format('boat')
            else:
                label = '{}'.format(prediction['label'])
            label = label.capitalize()
            # Create the bounding box rectangle - we need the base point (x, y) and the width and height of the rectangle
            rectangle = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=1, edgecolor=color, facecolor='none')
            ax.add_patch(rectangle)
            # Plot the bounding boxes and class labels with confidence scores
            plt.text(x1, y1-5, label, fontsize=4, color=color, fontweight='bold',horizontalalignment='left')
            plt.text(x2, y1-5, probability, fontsize=4, color=color, fontweight='bold',horizontalalignment='right')
            plt.axis('off')

            
            
            plt.savefig('./api/pred.png')
            tempFileObj = NamedTemporaryFile(mode='w+b',suffix='jpg')
            pilImage = open('./api/pred.png','rb')
            copyfileobj(pilImage,tempFileObj)
            pilImage.close()
            tempFileObj.seek(0,0)
            response = send_file(tempFileObj, as_attachment=True, attachment_filename="./api/pred.png")
            return response
