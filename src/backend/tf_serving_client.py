"""
TensorFlow Serving client for face recognition model inference.
"""

import json
import logging
from typing import Optional

import numpy as np
import requests

from config.config import config

logger = logging.getLogger(__name__)


class TFServingClient:
    """Client for communicating with TensorFlow Serving."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        model_name: str = None
    ):
        """
        Initialize TensorFlow Serving client.
        
        Args:
            host: TensorFlow Serving host address.
            port: TensorFlow Serving port number.
            model_name: Name of the model to use for inference.
        """
        self.host = host or config.TF_SERVING_HOST
        self.port = port or config.TF_SERVING_PORT
        self.model_name = model_name or config.TF_SERVING_MODEL_NAME
        self.base_url = f"http://{self.host}:{self.port}"
    
    def get_model_status(self) -> dict:
        """
        Get the status of the model.
        
        Returns:
            Dictionary containing model status information.
        """
        url = f"{self.base_url}/v1/models/{self.model_name}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get model status: {e}")
            return {"error": str(e)}
    
    def predict(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Get face embedding from the model.
        
        Args:
            image: Preprocessed face image as numpy array with shape (H, W, C).
        
        Returns:
            Face embedding vector as numpy array, or None if prediction fails.
        """
        url = f"{self.base_url}/v1/models/{self.model_name}:predict"
        
        # Prepare the input data
        # Add batch dimension if not present
        if len(image.shape) == 3:
            image = np.expand_dims(image, axis=0)
        
        # Prepare request payload
        payload = {
            "instances": image.tolist()
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if "predictions" in result:
                # Return the embedding (first prediction)
                embedding = np.array(result["predictions"][0])
                return embedding
            else:
                logger.error(f"Unexpected response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Prediction request failed: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse prediction response: {e}")
            return None
    
    def batch_predict(self, images: np.ndarray) -> Optional[np.ndarray]:
        """
        Get face embeddings for a batch of images.
        
        Args:
            images: Batch of preprocessed face images with shape (N, H, W, C).
        
        Returns:
            Array of face embedding vectors, or None if prediction fails.
        """
        url = f"{self.base_url}/v1/models/{self.model_name}:predict"
        
        # Prepare request payload
        payload = {
            "instances": images.tolist()
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            if "predictions" in result:
                embeddings = np.array(result["predictions"])
                return embeddings
            else:
                logger.error(f"Unexpected response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Batch prediction request failed: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse batch prediction response: {e}")
            return None


# Create default TensorFlow Serving client instance
tf_serving_client = TFServingClient()
