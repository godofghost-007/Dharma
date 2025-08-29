"""Machine learning model trainer for bot detection."""

import asyncio
import logging
import os
import pickle
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.utils.class_weight import compute_class_weight
import joblib

from ..core.config import settings

logger = logging.getLogger(__name__)


class BotModelTrainer:
    """Train and evaluate machine learning models for bot detection."""
    
    def __init__(self, model_save_path: Optional[str] = None):
        """Initialize the model trainer.
        
        Args:
            model_save_path: Path to save trained models
        """
        self.model_save_path = model_save_path or settings.bot_detection_model_name
        self.feature_names = [
            # Temporal features
            'avg_posts_per_day',
            'posting_time_variance',
            'weekend_activity_ratio',
            'activity_burst_frequency',
            'hourly_posting_entropy',
            'daily_posting_entropy',
            'inter_post_time_variance',
            'night_posting_ratio',
            'regular_interval_score',
            'account_age_days',
            
            # Content features
            'duplicate_content_ratio',
            'avg_content_length',
            'hashtag_usage_frequency',
            'mention_usage_frequency',
            'content_length_variance',
            'unique_word_ratio',
            'repetitive_phrase_score',
            'url_sharing_frequency',
            'emoji_usage_frequency',
            'caps_lock_frequency',
            
            # Network features
            'follower_following_ratio',
            'mutual_connections_ratio',
            'network_clustering_coefficient',
            'interaction_diversity_score',
            'reciprocal_connection_ratio',
            'suspicious_connection_ratio',
            'new_account_connection_ratio',
            'bot_connection_ratio',
            
            # Behavioral features
            'avg_likes_per_post',
            'avg_shares_per_post',
            'engagement_consistency',
            'response_time_variance',
            'engagement_rate_variance',
            'activity_consistency_score',
            'human_interaction_ratio'
        ]
        
        # Model components
        self.classifier = None
        self.scaler = None
        self.anomaly_detector = None
        
        # Training history
        self.training_history = []
        
    async def train_models(
        self,
        training_data: List[Dict[str, Any]],
        labels: List[int],
        validation_split: float = 0.2,
        use_cross_validation: bool = True
    ) -> Dict[str, Any]:
        """Train bot detection models with provided data.
        
        Args:
            training_data: List of feature dictionaries
            labels: List of labels (0=human, 1=bot)
            validation_split: Fraction of data to use for validation
            use_cross_validation: Whether to use cross-validation
            
        Returns:
            Training results and metrics
        """
        try:
            logger.info(f"Starting model training with {len(training_data)} samples")
            
            # Prepare feature matrix
            X = await self._prepare_feature_matrix(training_data)
            y = np.array(labels)
            
            # Validate data
            if len(X) != len(y):
                raise ValueError("Feature matrix and labels must have same length")
            
            if len(np.unique(y)) < 2:
                raise ValueError("Training data must contain both bot and human examples")
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=validation_split, random_state=42, stratify=y
            )
            
            # Train models
            training_results = {}
            
            # Train classifier
            classifier_results = await self._train_classifier(
                X_train, y_train, X_val, y_val, use_cross_validation
            )
            training_results['classifier'] = classifier_results
            
            # Train scaler
            scaler_results = await self._train_scaler(X_train)
            training_results['scaler'] = scaler_results
            
            # Train anomaly detector
            anomaly_results = await self._train_anomaly_detector(X_train, y_train)
            training_results['anomaly_detector'] = anomaly_results
            
            # Save models
            await self._save_models()
            
            # Record training history
            training_record = {
                'timestamp': datetime.utcnow(),
                'samples_count': len(training_data),
                'validation_split': validation_split,
                'results': training_results
            }
            self.training_history.append(training_record)
            
            logger.info("Model training completed successfully")
            return training_results
            
        except Exception as e:
            logger.error(f"Error during model training: {e}")
            raise
    
    async def _prepare_feature_matrix(self, training_data: List[Dict[str, Any]]) -> np.ndarray:
        """Prepare feature matrix from training data.
        
        Args:
            training_data: List of feature dictionaries
            
        Returns:
            Feature matrix as numpy array
        """
        try:
            feature_matrix = []
            
            for sample in training_data:
                feature_vector = []
                for feature_name in self.feature_names:
                    value = sample.get(feature_name, 0.0)
                    # Handle None values
                    if value is None:
                        value = 0.0
                    feature_vector.append(float(value))
                
                feature_matrix.append(feature_vector)
            
            return np.array(feature_matrix)
            
        except Exception as e:
            logger.error(f"Error preparing feature matrix: {e}")
            raise
    
    async def _train_classifier(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        use_cross_validation: bool
    ) -> Dict[str, Any]:
        """Train the main classification model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            use_cross_validation: Whether to use cross-validation
            
        Returns:
            Training results and metrics
        """
        try:
            logger.info("Training classification model")
            
            # Calculate class weights for imbalanced data
            class_weights = compute_class_weight(
                'balanced', classes=np.unique(y_train), y=y_train
            )
            class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
            
            # Define parameter grid for hyperparameter tuning
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
            
            # Create base classifier
            base_classifier = RandomForestClassifier(
                random_state=42,
                class_weight=class_weight_dict,
                n_jobs=-1
            )
            
            # Perform grid search if we have enough data
            if len(X_train) > 100:
                logger.info("Performing hyperparameter tuning")
                grid_search = GridSearchCV(
                    base_classifier,
                    param_grid,
                    cv=5,
                    scoring='roc_auc',
                    n_jobs=-1,
                    verbose=1
                )
                grid_search.fit(X_train, y_train)
                self.classifier = grid_search.best_estimator_
                best_params = grid_search.best_params_
            else:
                # Use default parameters for small datasets
                self.classifier = base_classifier
                self.classifier.fit(X_train, y_train)
                best_params = {}
            
            # Evaluate on validation set
            val_predictions = self.classifier.predict(X_val)
            val_probabilities = self.classifier.predict_proba(X_val)[:, 1]
            
            # Calculate metrics
            val_accuracy = self.classifier.score(X_val, y_val)
            val_auc = roc_auc_score(y_val, val_probabilities)
            
            # Cross-validation if requested
            cv_scores = []
            if use_cross_validation and len(X_train) > 50:
                cv_scores = cross_val_score(
                    self.classifier, X_train, y_train, cv=5, scoring='roc_auc'
                )
            
            # Feature importance
            feature_importance = dict(zip(
                self.feature_names,
                self.classifier.feature_importances_
            ))
            
            # Sort features by importance
            sorted_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            results = {
                'model_type': 'RandomForestClassifier',
                'best_params': best_params,
                'validation_accuracy': float(val_accuracy),
                'validation_auc': float(val_auc),
                'cross_validation_scores': cv_scores.tolist() if len(cv_scores) > 0 else [],
                'feature_importance': feature_importance,
                'top_features': sorted_features[:10],
                'classification_report': classification_report(y_val, val_predictions, output_dict=True),
                'confusion_matrix': confusion_matrix(y_val, val_predictions).tolist()
            }
            
            logger.info(f"Classifier training completed. Validation AUC: {val_auc:.3f}")
            return results
            
        except Exception as e:
            logger.error(f"Error training classifier: {e}")
            raise
    
    async def _train_scaler(self, X_train: np.ndarray) -> Dict[str, Any]:
        """Train feature scaler.
        
        Args:
            X_train: Training features
            
        Returns:
            Scaler training results
        """
        try:
            logger.info("Training feature scaler")
            
            self.scaler = StandardScaler()
            self.scaler.fit(X_train)
            
            # Calculate scaling statistics
            feature_stats = {}
            for i, feature_name in enumerate(self.feature_names):
                feature_stats[feature_name] = {
                    'mean': float(self.scaler.mean_[i]),
                    'std': float(self.scaler.scale_[i])
                }
            
            results = {
                'scaler_type': 'StandardScaler',
                'feature_statistics': feature_stats
            }
            
            logger.info("Feature scaler training completed")
            return results
            
        except Exception as e:
            logger.error(f"Error training scaler: {e}")
            raise
    
    async def _train_anomaly_detector(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> Dict[str, Any]:
        """Train anomaly detection model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            
        Returns:
            Anomaly detector training results
        """
        try:
            logger.info("Training anomaly detector")
            
            # Scale features for anomaly detection
            X_train_scaled = self.scaler.transform(X_train)
            
            # Train on normal (human) samples only
            human_samples = X_train_scaled[y_train == 0]
            
            # Estimate contamination based on bot ratio in training data
            bot_ratio = np.sum(y_train) / len(y_train)
            contamination = min(max(bot_ratio, 0.05), 0.3)  # Clamp between 5% and 30%
            
            self.anomaly_detector = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_jobs=-1
            )
            
            # Fit on human samples
            self.anomaly_detector.fit(human_samples)
            
            # Evaluate anomaly detection
            anomaly_scores = self.anomaly_detector.decision_function(X_train_scaled)
            anomaly_predictions = self.anomaly_detector.predict(X_train_scaled)
            
            # Calculate metrics
            # Anomaly detector returns -1 for outliers, 1 for inliers
            # Convert to 0/1 format (0=normal, 1=anomaly)
            anomaly_binary = (anomaly_predictions == -1).astype(int)
            
            # Calculate how well anomalies correspond to bots
            anomaly_precision = np.sum((anomaly_binary == 1) & (y_train == 1)) / max(np.sum(anomaly_binary), 1)
            anomaly_recall = np.sum((anomaly_binary == 1) & (y_train == 1)) / max(np.sum(y_train), 1)
            
            results = {
                'model_type': 'IsolationForest',
                'contamination': float(contamination),
                'anomaly_precision': float(anomaly_precision),
                'anomaly_recall': float(anomaly_recall),
                'mean_anomaly_score': float(np.mean(anomaly_scores)),
                'std_anomaly_score': float(np.std(anomaly_scores))
            }
            
            logger.info(f"Anomaly detector training completed. Precision: {anomaly_precision:.3f}")
            return results
            
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            raise
    
    async def _save_models(self) -> None:
        """Save trained models to disk."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.model_save_path, exist_ok=True)
            
            # Save classifier
            if self.classifier is not None:
                classifier_path = os.path.join(self.model_save_path, 'bot_classifier.pkl')
                joblib.dump(self.classifier, classifier_path)
                logger.info(f"Classifier saved to {classifier_path}")
            
            # Save scaler
            if self.scaler is not None:
                scaler_path = os.path.join(self.model_save_path, 'feature_scaler.pkl')
                joblib.dump(self.scaler, scaler_path)
                logger.info(f"Scaler saved to {scaler_path}")
            
            # Save anomaly detector
            if self.anomaly_detector is not None:
                anomaly_path = os.path.join(self.model_save_path, 'anomaly_detector.pkl')
                joblib.dump(self.anomaly_detector, anomaly_path)
                logger.info(f"Anomaly detector saved to {anomaly_path}")
            
            # Save feature names and metadata
            metadata = {
                'feature_names': self.feature_names,
                'training_history': self.training_history,
                'model_version': '1.0.0',
                'created_at': datetime.utcnow().isoformat()
            }
            
            metadata_path = os.path.join(self.model_save_path, 'model_metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info("All models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
            raise
    
    async def generate_synthetic_training_data(
        self,
        num_samples: int = 1000,
        bot_ratio: float = 0.3
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Generate synthetic training data for model development.
        
        Args:
            num_samples: Total number of samples to generate
            bot_ratio: Ratio of bot samples (0.0 to 1.0)
            
        Returns:
            Tuple of (feature_data, labels)
        """
        try:
            logger.info(f"Generating {num_samples} synthetic training samples")
            
            np.random.seed(42)  # For reproducibility
            
            num_bots = int(num_samples * bot_ratio)
            num_humans = num_samples - num_bots
            
            training_data = []
            labels = []
            
            # Generate human samples
            for _ in range(num_humans):
                sample = await self._generate_human_sample()
                training_data.append(sample)
                labels.append(0)  # 0 = human
            
            # Generate bot samples
            for _ in range(num_bots):
                sample = await self._generate_bot_sample()
                training_data.append(sample)
                labels.append(1)  # 1 = bot
            
            # Shuffle the data
            combined = list(zip(training_data, labels))
            np.random.shuffle(combined)
            training_data, labels = zip(*combined)
            
            logger.info(f"Generated {num_humans} human and {num_bots} bot samples")
            return list(training_data), list(labels)
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            raise
    
    async def _generate_human_sample(self) -> Dict[str, Any]:
        """Generate a synthetic human user sample."""
        return {
            # Temporal features - humans have varied patterns
            'avg_posts_per_day': np.random.lognormal(1.0, 0.8),  # 1-10 posts/day typically
            'posting_time_variance': np.random.uniform(0.3, 0.8),
            'weekend_activity_ratio': np.random.uniform(0.2, 0.5),
            'activity_burst_frequency': np.random.uniform(0.05, 0.3),
            'hourly_posting_entropy': np.random.uniform(0.6, 0.9),
            'daily_posting_entropy': np.random.uniform(0.7, 0.95),
            'inter_post_time_variance': np.random.uniform(0.4, 0.9),
            'night_posting_ratio': np.random.uniform(0.1, 0.4),
            'regular_interval_score': np.random.uniform(0.0, 0.2),
            'account_age_days': np.random.lognormal(5.0, 1.0),  # Varied account ages
            
            # Content features - humans have diverse content
            'duplicate_content_ratio': np.random.uniform(0.0, 0.3),
            'avg_content_length': np.random.lognormal(4.0, 0.5),  # ~50-200 chars
            'hashtag_usage_frequency': np.random.uniform(0.1, 0.6),
            'mention_usage_frequency': np.random.uniform(0.05, 0.4),
            'content_length_variance': np.random.uniform(0.3, 0.8),
            'unique_word_ratio': np.random.uniform(0.5, 0.9),
            'repetitive_phrase_score': np.random.uniform(0.0, 0.2),
            'url_sharing_frequency': np.random.uniform(0.1, 0.5),
            'emoji_usage_frequency': np.random.uniform(0.2, 0.7),
            'caps_lock_frequency': np.random.uniform(0.0, 0.2),
            
            # Network features - humans have natural networks
            'follower_following_ratio': np.random.lognormal(0.0, 1.5),
            'mutual_connections_ratio': np.random.uniform(0.1, 0.5),
            'network_clustering_coefficient': np.random.uniform(0.1, 0.4),
            'interaction_diversity_score': np.random.uniform(0.4, 0.9),
            'reciprocal_connection_ratio': np.random.uniform(0.2, 0.6),
            'suspicious_connection_ratio': np.random.uniform(0.0, 0.1),
            'new_account_connection_ratio': np.random.uniform(0.05, 0.3),
            'bot_connection_ratio': np.random.uniform(0.0, 0.05),
            
            # Behavioral features - humans have natural engagement
            'avg_likes_per_post': np.random.lognormal(1.5, 1.0),
            'avg_shares_per_post': np.random.lognormal(0.5, 1.0),
            'engagement_consistency': np.random.uniform(0.3, 0.8),
            'response_time_variance': np.random.uniform(0.4, 0.9),
            'engagement_rate_variance': np.random.uniform(0.2, 0.7),
            'activity_consistency_score': np.random.uniform(0.4, 0.8),
            'human_interaction_ratio': np.random.uniform(0.6, 0.95)
        }
    
    async def _generate_bot_sample(self) -> Dict[str, Any]:
        """Generate a synthetic bot user sample."""
        return {
            # Temporal features - bots have more regular patterns
            'avg_posts_per_day': np.random.lognormal(2.5, 1.0),  # Higher posting frequency
            'posting_time_variance': np.random.uniform(0.1, 0.4),  # More regular timing
            'weekend_activity_ratio': np.random.uniform(0.4, 0.7),  # Less weekend variation
            'activity_burst_frequency': np.random.uniform(0.2, 0.6),  # More bursts
            'hourly_posting_entropy': np.random.uniform(0.3, 0.7),  # Less entropy
            'daily_posting_entropy': np.random.uniform(0.4, 0.8),
            'inter_post_time_variance': np.random.uniform(0.1, 0.5),  # More regular intervals
            'night_posting_ratio': np.random.uniform(0.3, 0.8),  # More night activity
            'regular_interval_score': np.random.uniform(0.3, 0.8),  # More regular intervals
            'account_age_days': np.random.lognormal(3.0, 1.5),  # Often newer accounts
            
            # Content features - bots have repetitive content
            'duplicate_content_ratio': np.random.uniform(0.4, 0.9),  # High duplication
            'avg_content_length': np.random.lognormal(3.5, 0.3),  # More consistent length
            'hashtag_usage_frequency': np.random.uniform(0.3, 0.8),  # High hashtag use
            'mention_usage_frequency': np.random.uniform(0.2, 0.7),
            'content_length_variance': np.random.uniform(0.1, 0.4),  # Low variance
            'unique_word_ratio': np.random.uniform(0.2, 0.6),  # Less unique words
            'repetitive_phrase_score': np.random.uniform(0.3, 0.8),  # High repetition
            'url_sharing_frequency': np.random.uniform(0.4, 0.9),  # High URL sharing
            'emoji_usage_frequency': np.random.uniform(0.1, 0.4),  # Less emoji use
            'caps_lock_frequency': np.random.uniform(0.2, 0.6),  # More caps
            
            # Network features - bots have artificial networks
            'follower_following_ratio': np.random.choice([
                np.random.uniform(0.01, 0.1),  # Very low ratio
                np.random.uniform(10, 100)     # Very high ratio
            ]),
            'mutual_connections_ratio': np.random.uniform(0.0, 0.2),  # Low mutual connections
            'network_clustering_coefficient': np.random.uniform(0.5, 0.9),  # High clustering
            'interaction_diversity_score': np.random.uniform(0.1, 0.5),  # Low diversity
            'reciprocal_connection_ratio': np.random.uniform(0.0, 0.3),  # Low reciprocity
            'suspicious_connection_ratio': np.random.uniform(0.2, 0.7),  # High suspicious connections
            'new_account_connection_ratio': np.random.uniform(0.3, 0.8),  # Connect to new accounts
            'bot_connection_ratio': np.random.uniform(0.1, 0.4),  # Connect to other bots
            
            # Behavioral features - bots have artificial engagement
            'avg_likes_per_post': np.random.choice([
                np.random.uniform(0, 2),       # Very low engagement
                np.random.uniform(50, 200)     # Artificially high engagement
            ]),
            'avg_shares_per_post': np.random.choice([
                np.random.uniform(0, 1),
                np.random.uniform(20, 100)
            ]),
            'engagement_consistency': np.random.choice([
                np.random.uniform(0.0, 0.3),   # Very inconsistent
                np.random.uniform(0.8, 1.0)    # Too consistent
            ]),
            'response_time_variance': np.random.uniform(0.0, 0.3),  # Low variance
            'engagement_rate_variance': np.random.uniform(0.0, 0.2),
            'activity_consistency_score': np.random.uniform(0.7, 1.0),  # Too consistent
            'human_interaction_ratio': np.random.uniform(0.0, 0.4)  # Low human interaction
        }
    
    def get_training_history(self) -> List[Dict[str, Any]]:
        """Get model training history.
        
        Returns:
            List of training records
        """
        return self.training_history
    
    async def evaluate_model(
        self,
        test_data: List[Dict[str, Any]],
        test_labels: List[int]
    ) -> Dict[str, Any]:
        """Evaluate trained models on test data.
        
        Args:
            test_data: Test feature data
            test_labels: Test labels
            
        Returns:
            Evaluation metrics
        """
        try:
            if self.classifier is None or self.scaler is None:
                raise ValueError("Models must be trained before evaluation")
            
            # Prepare test features
            X_test = await self._prepare_feature_matrix(test_data)
            y_test = np.array(test_labels)
            
            # Scale features
            X_test_scaled = self.scaler.transform(X_test)
            
            # Classifier evaluation
            test_predictions = self.classifier.predict(X_test_scaled)
            test_probabilities = self.classifier.predict_proba(X_test_scaled)[:, 1]
            
            test_accuracy = self.classifier.score(X_test_scaled, y_test)
            test_auc = roc_auc_score(y_test, test_probabilities)
            
            # Anomaly detector evaluation
            anomaly_predictions = self.anomaly_detector.predict(X_test_scaled)
            anomaly_binary = (anomaly_predictions == -1).astype(int)
            
            evaluation_results = {
                'test_accuracy': float(test_accuracy),
                'test_auc': float(test_auc),
                'classification_report': classification_report(y_test, test_predictions, output_dict=True),
                'confusion_matrix': confusion_matrix(y_test, test_predictions).tolist(),
                'anomaly_detection_accuracy': float(np.mean(anomaly_binary == y_test))
            }
            
            logger.info(f"Model evaluation completed. Test AUC: {test_auc:.3f}")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            raise