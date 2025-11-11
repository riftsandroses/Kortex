import os
import joblib
import numpy as np
from typing import Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from django.conf import settings
from .models import ModelVersion, LLMResponse, ResponseCategory, IntegratedApplication
import logging

logger = logging.getLogger(__name__)


class GuardrailsMLService:
    """Service for ML model training and inference"""

    def __init__(self):
        self.models_dir = os.path.join(settings.KATANA_MODEL_ROOT, 'katana_models')
        os.makedirs(self.models_dir, exist_ok=True)

    def get_base_model(self) -> Tuple[MLPClassifier, TfidfVectorizer]:
        """Initialize base neural network model"""
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=1.0,
            strip_accents='unicode',
            lowercase=True,
            stop_words=None
        )

        classifier = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=16,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=100,
            early_stopping=True,
            validation_fraction=0.2,
            n_iter_no_change=5,
            random_state=42,
            verbose=False
        )

        return classifier, vectorizer

    def train_model(
        self,
        application: IntegratedApplication,
        version_name: str,
        hyperparameters: Optional[Dict] = None
    ) -> ModelVersion:
        """Train a new model for an application"""
        
        # Get training data
        training_data = LLMResponse.objects.filter(
            application=application,
            labeled_category__isnull=False
        ).select_related('labeled_category')

        if training_data.count() < 20:
            raise ValueError("Insufficient training data. Minimum 20 labeled samples required.")

        # Prepare data
        texts = []
        labels = []
        label_mapping = {}
        
        for response in training_data:
            combined_text = f"{response.prompt} [SEP] {response.response_text}"
            texts.append(combined_text)
            
            category_id = str(response.labeled_category.id)
            if category_id not in label_mapping:
                label_mapping[category_id] = len(label_mapping)
            labels.append(label_mapping[category_id])

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        # Initialize model and vectorizer
        classifier, vectorizer = self.get_base_model()
        
        # Apply custom hyperparameters if provided
        if hyperparameters:
            for key, value in hyperparameters.items():
                if hasattr(classifier, key):
                    setattr(classifier, key, value)

        # Train
        logger.info(f"Training model for {application.name} with {len(texts)} samples")
        
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)
        
        classifier.fit(X_train_vec, y_train)

        # Evaluate
        y_pred = classifier.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='weighted', zero_division=0
        )

        # Save model and vectorizer
        model_filename = f"{application.id}_{version_name}_model.pkl"
        vectorizer_filename = f"{application.id}_{version_name}_vectorizer.pkl"
        
        model_path = os.path.join(self.models_dir, model_filename)
        vectorizer_path = os.path.join(self.models_dir, vectorizer_filename)

        # Save with label mapping
        model_data = {
            'classifier': classifier,
            'label_mapping': label_mapping,
            'reverse_label_mapping': {v: k for k, v in label_mapping.items()}
        }
        
        joblib.dump(model_data, model_path)
        joblib.dump(vectorizer, vectorizer_path)

        # Create model version record
        model_version = ModelVersion.objects.create(
            application=application,
            version_name=version_name,
            model_file_path=model_path,
            vectorizer_file_path=vectorizer_path,
            training_samples=len(texts),
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            model_type='neural_network',
            hyperparameters=hyperparameters or {}
        )

        logger.info(
            f"Model trained successfully. Accuracy: {accuracy:.4f}, "
            f"Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}"
        )

        return model_version

    def load_model(self, model_version: ModelVersion) -> Tuple:
        """Load a trained model and vectorizer"""
        try:
            model_data = joblib.load(model_version.model_file_path)
            vectorizer = joblib.load(model_version.vectorizer_file_path)
            
            return (
                model_data['classifier'],
                vectorizer,
                model_data['reverse_label_mapping']
            )
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def predict(
        self,
        application: IntegratedApplication,
        prompt: str,
        response_text: str
    ) -> Tuple[Optional[str], Optional[float], bool]:
        """
        Predict category for a response
        Returns: (category_id, confidence_score, should_block)
        """
        try:
            # Get active model
            active_model = ModelVersion.objects.filter(
                application=application,
                is_active=True
            ).first()

            if not active_model:
                # Use base model with default safe classification
                return None, None, False

            # Load model
            classifier, vectorizer, label_mapping = self.load_model(active_model)

            # Prepare input
            combined_text = f"{prompt} [SEP] {response_text}"
            X = vectorizer.transform([combined_text])

            # Predict
            prediction = classifier.predict(X)[0]
            probabilities = classifier.predict_proba(X)[0]
            confidence = float(max(probabilities))

            # Get category ID
            category_id = label_mapping[prediction]
            
            # Get category to check if should block
            category = ResponseCategory.objects.filter(id=category_id).first()
            should_block = False
            
            if category:
                should_block = (
                    category.should_block and 
                    confidence >= application.confidence_threshold
                )

            return category_id, confidence, should_block

        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return None, None, False

    def activate_model(self, model_version: ModelVersion):
        """Activate a model version and deactivate others"""
        # Deactivate all other models for this application
        ModelVersion.objects.filter(
            application=model_version.application,
            is_active=True
        ).update(is_active=False)

        # Activate this model
        model_version.is_active = True
        model_version.save()

        # Update application's model version
        model_version.application.model_version = model_version.version_name
        model_version.application.save()

    def retrain_with_new_data(
        self,
        application: IntegratedApplication,
        version_name: str
    ) -> ModelVersion:
        """
        Retrain model with all labeled data including new samples
        """
        return self.train_model(application, version_name)

    def evaluate_model(self, model_version: ModelVersion) -> Dict:
        """Evaluate model on test set"""
        try:
            classifier, vectorizer, label_mapping = self.load_model(model_version)

            # Get labeled data
            test_data = LLMResponse.objects.filter(
                application=model_version.application,
                labeled_category__isnull=False,
                is_training_data=False
            ).select_related('labeled_category')[:500]

            if test_data.count() < 10:
                return {
                    'error': 'Insufficient test data',
                    'samples': test_data.count()
                }

            texts = []
            true_labels = []
            
            for response in test_data:
                combined_text = f"{response.prompt} [SEP] {response.response_text}"
                texts.append(combined_text)
                
                category_id = str(response.labeled_category.id)
                # Find the label index
                label_idx = None
                for idx, cat_id in label_mapping.items():
                    if cat_id == category_id:
                        label_idx = idx
                        break
                
                if label_idx is not None:
                    true_labels.append(label_idx)

            if len(texts) != len(true_labels):
                return {
                    'error': 'Label mapping mismatch',
                    'samples': len(texts)
                }

            X_test = vectorizer.transform(texts)
            y_pred = classifier.predict(X_test)

            accuracy = accuracy_score(true_labels, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                true_labels, y_pred, average='weighted', zero_division=0
            )

            return {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'test_samples': len(texts)
            }

        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {'error': str(e)}


# Global instance
ml_service = GuardrailsMLService()