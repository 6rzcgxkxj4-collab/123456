"""
TensorFlow Serving client for face recognition model inference.
"""
import json
import numpy as np
import requests
from typing import Optional, List, Dict, Any

# Try to import gRPC dependencies
try:
    import grpc
    from tensorflow_serving.apis import predict_pb2
    from tensorflow_serving.apis import prediction_service_pb2_grpc
    import tensorflow as tf
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False


class TFServingClient:
    """Client for TensorFlow Serving REST and gRPC APIs."""
    
    def __init__(
        self,
        host: str = 'localhost',
        rest_port: int = 8501,
        grpc_port: int = 8500,
        model_name: str = 'face_recognition',
        model_version: Optional[int] = None,
        timeout: float = 10.0
    ):
        """
        Initialize TensorFlow Serving client.
        
        Args:
            host: TensorFlow Serving host
            rest_port: REST API port
            grpc_port: gRPC API port
            model_name: Name of the model
            model_version: Specific model version (None for latest)
            timeout: Request timeout in seconds
        """
        self.host = host
        self.rest_port = rest_port
        self.grpc_port = grpc_port
        self.model_name = model_name
        self.model_version = model_version
        self.timeout = timeout
        
        # Build REST API URL
        version_path = f'/versions/{model_version}' if model_version else ''
        self.rest_url = f'http://{host}:{rest_port}/v1/models/{model_name}{version_path}:predict'
        self.model_status_url = f'http://{host}:{rest_port}/v1/models/{model_name}'
        
        # gRPC channel (lazy initialization)
        self._grpc_channel = None
        self._grpc_stub = None
    
    @property
    def grpc_channel(self):
        """Get or create gRPC channel."""
        if self._grpc_channel is None and GRPC_AVAILABLE:
            self._grpc_channel = grpc.insecure_channel(
                f'{self.host}:{self.grpc_port}'
            )
        return self._grpc_channel
    
    @property
    def grpc_stub(self):
        """Get or create gRPC stub."""
        if self._grpc_stub is None and GRPC_AVAILABLE:
            self._grpc_stub = prediction_service_pb2_grpc.PredictionServiceStub(
                self.grpc_channel
            )
        return self._grpc_stub
    
    def predict_rest(
        self,
        input_data: np.ndarray,
        input_name: str = 'input_image',
        signature_name: str = 'serving_default'
    ) -> Dict[str, Any]:
        """
        Make prediction using REST API.
        
        Args:
            input_data: Input data as numpy array
            input_name: Name of the input tensor
            signature_name: Signature name
            
        Returns:
            Prediction result as dictionary
        """
        # Prepare request payload
        payload = {
            'signature_name': signature_name,
            'instances': input_data.tolist() if isinstance(input_data, np.ndarray) else input_data
        }
        
        try:
            response = requests.post(
                self.rest_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"REST API request failed: {e}")
    
    def predict_grpc(
        self,
        input_data: np.ndarray,
        input_name: str = 'input_image',
        signature_name: str = 'serving_default'
    ) -> np.ndarray:
        """
        Make prediction using gRPC API.
        
        Args:
            input_data: Input data as numpy array
            input_name: Name of the input tensor
            signature_name: Signature name
            
        Returns:
            Prediction result as numpy array
        """
        if not GRPC_AVAILABLE:
            raise RuntimeError("gRPC dependencies not available")
        
        # Create prediction request
        request = predict_pb2.PredictRequest()
        request.model_spec.name = self.model_name
        request.model_spec.signature_name = signature_name
        
        if self.model_version:
            request.model_spec.version.value = self.model_version
        
        # Set input tensor
        request.inputs[input_name].CopyFrom(
            tf.make_tensor_proto(input_data)
        )
        
        try:
            # Make prediction
            result = self.grpc_stub.Predict(request, self.timeout)
            
            # Extract output
            output = result.outputs
            # Get the first output tensor
            for output_name in output:
                return tf.make_ndarray(output[output_name])
            
            return None
        except grpc.RpcError as e:
            raise RuntimeError(f"gRPC request failed: {e}")
    
    def predict(
        self,
        input_data: np.ndarray,
        use_grpc: bool = False,
        **kwargs
    ) -> Any:
        """
        Make prediction using preferred API.
        
        Args:
            input_data: Input data
            use_grpc: Whether to use gRPC (default: REST)
            **kwargs: Additional arguments for predict methods
            
        Returns:
            Prediction result
        """
        if use_grpc:
            return self.predict_grpc(input_data, **kwargs)
        return self.predict_rest(input_data, **kwargs)
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Get model status from TensorFlow Serving.
        
        Returns:
            Model status as dictionary
        """
        try:
            response = requests.get(
                self.model_status_url,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to get model status: {e}")
    
    def is_model_ready(self) -> bool:
        """
        Check if model is ready for serving.
        
        Returns:
            True if model is ready, False otherwise
        """
        try:
            status = self.get_model_status()
            model_version_status = status.get('model_version_status', [])
            for version in model_version_status:
                if version.get('state') == 'AVAILABLE':
                    return True
            return False
        except Exception:
            return False
    
    def close(self):
        """Close gRPC channel."""
        if self._grpc_channel:
            self._grpc_channel.close()
            self._grpc_channel = None
            self._grpc_stub = None


class FaceRecognitionTFServingClient(TFServingClient):
    """Specialized TensorFlow Serving client for face recognition."""
    
    def __init__(
        self,
        host: str = 'localhost',
        rest_port: int = 8501,
        grpc_port: int = 8500,
        model_name: str = 'face_recognition',
        **kwargs
    ):
        """Initialize face recognition TF Serving client."""
        super().__init__(
            host=host,
            rest_port=rest_port,
            grpc_port=grpc_port,
            model_name=model_name,
            **kwargs
        )
    
    def preprocess_image(self, image: np.ndarray, target_size: tuple = (160, 160)) -> np.ndarray:
        """
        Preprocess image for face recognition model.
        
        Args:
            image: Input image as numpy array
            target_size: Target size for model input
            
        Returns:
            Preprocessed image
        """
        try:
            import cv2
            # Resize image
            image = cv2.resize(image, target_size)
        except ImportError:
            # Fallback without cv2
            from PIL import Image
            img = Image.fromarray(image)
            img = img.resize(target_size)
            image = np.array(img)
        
        # Normalize pixel values
        image = image.astype(np.float32) / 255.0
        
        # Add batch dimension if needed
        if len(image.shape) == 3:
            image = np.expand_dims(image, axis=0)
        
        return image
    
    def get_face_embedding(
        self,
        face_image: np.ndarray,
        preprocess: bool = True,
        use_grpc: bool = False
    ) -> np.ndarray:
        """
        Get face embedding from face image.
        
        Args:
            face_image: Face image as numpy array
            preprocess: Whether to preprocess the image
            use_grpc: Whether to use gRPC
            
        Returns:
            Face embedding as numpy array
        """
        if preprocess:
            face_image = self.preprocess_image(face_image)
        
        result = self.predict(face_image, use_grpc=use_grpc)
        
        if isinstance(result, dict):
            # REST API response
            predictions = result.get('predictions', [])
            if predictions:
                return np.array(predictions[0])
        else:
            # gRPC response (already numpy array)
            return result
        
        return None
    
    def compare_faces(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compare two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Calculate Euclidean distance
        distance = np.linalg.norm(embedding1 - embedding2)
        
        # Convert distance to similarity (using typical face recognition threshold)
        # Distance of 0.6 is typically used as threshold
        similarity = max(0.0, 1.0 - distance / 2.0)
        
        return similarity
