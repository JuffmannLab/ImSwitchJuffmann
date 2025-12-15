import numpy as np

class KalmanFilter:
    """Simple 1D Kalman filter for position and velocity estimation."""
    def __init__(self, initial_pos, initial_vel, dt=0.001, process_noise=0.1, measurement_noise=1.0):
        # State vector: [position, velocity]
        self.state = np.array([initial_pos, initial_vel])
        
        # State transition matrix
        self.F = np.array([[1, dt],
                          [0,  1]])
        
        # Process noise covariance
        self.Q = np.array([[dt**3/3, dt**2/2],
                          [dt**2/2,      dt]]) * process_noise
        
        # Measurement matrix (we only measure position)
        self.H = np.array([[1, 0]])
        
        # Measurement noise
        self.R = np.array([[measurement_noise]])
        
        # Covariance matrix
        self.P = np.eye(2) * 100  # Large initial uncertainty

    def predict(self):
        # Predict state
        self.state = self.F @ self.state
        # Predict covariance
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.state[0]  # Return predicted position

    def update(self, measurement):
        # Kalman gain
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state
        y = measurement - self.H @ self.state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P
        
        return self.state[0], self.state[1]  # Return position and velocity
