import librosa
import numpy as np
from sklearn.neighbors import NearestNeighbors

def extract_audio_features(file_path: str) -> list[float]:
    y, sr = librosa.load(file_path, sr=22050, duration=30)
    
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    
    features = [
        float(tempo[0] if isinstance(tempo, np.ndarray) else tempo),
        float(np.mean(spectral_centroids)),
        float(np.mean(spectral_rolloff))
    ]
    
    for mfcc in mfccs:
        features.append(float(np.mean(mfcc)))
        
    return features

def get_knn_recommendations(target_features: list[float], all_features: list[list[float]], all_ids: list[str], k: int = 5) -> list[str]:
    if not all_features or len(all_features) < k + 1:
        return []
        
    knn = NearestNeighbors(n_neighbors=k + 1, algorithm='auto', metric='cosine')
    knn.fit(all_features)
    
    distances, indices = knn.kneighbors([target_features])
    
    recommended_ids = []
    for i in range(1, len(indices[0])):
        recommended_ids.append(all_ids[indices[0][i]])
        
    return recommended_ids