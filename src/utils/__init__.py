"""Utility functions module."""
from .face_recognition_utils import (
    FaceDetector,
    FaceEncoder,
    FaceRecognizer,
    serialize_encoding,
    deserialize_encoding,
    preprocess_image,
    resize_image
)

from .tf_serving_client import (
    TFServingClient,
    FaceRecognitionTFServingClient
)
