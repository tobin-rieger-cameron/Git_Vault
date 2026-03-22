import numpy as np
import matplotlib.pyplot as plt

class SimpleNeuralNetwork:
    def __init__(self, input_size, hidden_size, output_size, learning_rate=0.1):
        """
        Initialize a simple feedforward neural network with one hidden layer
        
        Args:
            input_size: Number of input features
            hidden_size: Number of neurons in hidden layer
            output_size: Number of output neurons
            learning_rate: Learning rate for gradient descent
        """
        self.learning_rate = learning_rate
        
        # Initialize weights randomly (small values work better)
        # Weights from input to hidden layer
        self.W1 = np.random.randn(input_size, hidden_size) * 0.01
        self.b1 = np.zeros((1, hidden_size))
        
        # Weights from hidden to output layer
        self.W2 = np.random.randn(hidden_size, output_size) * 0.01
        self.b2 = np.zeros((1, output_size))
        
        # Store training history
        self.loss_history = []
    
    def sigmoid(self, x):
        """Sigmoid activation function"""
        # Clip x to prevent overflow
        x = np.clip(x, -500, 500)
        return 1 / (1 + np.exp(-x))
    
    def sigmoid_derivative(self, x):
        """Derivative of sigmoid function"""
        return x * (1 - x)
    
    def forward(self, X):
        """
        Forward propagation through the network
        
        Args:
            X: Input data (batch_size, input_size)
            
        Returns:
            Output predictions
        """
        # Hidden layer
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.sigmoid(self.z1)
        
        # Output layer
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self.sigmoid(self.z2)
        
        return self.a2
    
    def backward(self, X, y, output):
        """
        Backward propagation (backpropagation) to compute gradients
        
        Args:
            X: Input data
            y: True labels
            output: Network predictions
        """
        m = X.shape[0]  # Number of examples
        
        # Calculate error at output layer
        output_error = output - y
        output_delta = output_error * self.sigmoid_derivative(output)
        
        # Calculate error at hidden layer
        hidden_error = output_delta.dot(self.W2.T)
        hidden_delta = hidden_error * self.sigmoid_derivative(self.a1)
        
        # Update weights and biases using gradients
        self.W2 -= self.learning_rate * self.a1.T.dot(output_delta) / m
        self.b2 -= self.learning_rate * np.sum(output_delta, axis=0, keepdims=True) / m
        self.W1 -= self.learning_rate * X.T.dot(hidden_delta) / m
        self.b1 -= self.learning_rate * np.sum(hidden_delta, axis=0, keepdims=True) / m
    
    def compute_loss(self, y_true, y_pred):
        """Compute mean squared error loss"""
        return np.mean((y_true - y_pred) ** 2)
    
    def train(self, X, y, epochs=1000, verbose=True):
        """
        Train the neural network
        
        Args:
            X: Training input data
            y: Training labels
            epochs: Number of training iterations
            verbose: Whether to print progress
        """
        for epoch in range(epochs):
            # Forward pass
            output = self.forward(X)
            
            # Compute loss
            loss = self.compute_loss(y, output)
            self.loss_history.append(loss)
            
            # Backward pass
            self.backward(X, y, output)
            
            # Print progress
            if verbose and epoch % 100 == 0:
                print(f"Epoch {epoch}, Loss: {loss:.4f}")
    
    def predict(self, X):
        """Make predictions on new data"""
        return self.forward(X)
    
    def plot_loss(self):
        """Plot training loss over time"""
        plt.figure(figsize=(10, 6))
        plt.plot(self.loss_history)
        plt.title('Training Loss Over Time')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.grid(True)
        plt.show()

# Example usage: XOR problem
def create_xor_dataset():
    """Create XOR dataset - a classic non-linearly separable problem"""
    X = np.array([[0, 0],
                  [0, 1],
                  [1, 0],
                  [1, 1]])
    y = np.array([[0],
                  [1],
                  [1],
                  [0]])
    return X, y

# Demo: Training on XOR problem
if __name__ == "__main__":
    print("Training Neural Network on XOR Problem")
    print("=" * 40)
    
    # Create dataset
    X, y = create_xor_dataset()
    
    # Create and train network
    nn = SimpleNeuralNetwork(input_size=2, hidden_size=4, output_size=1, learning_rate=1.0)
    nn.train(X, y, epochs=2000, verbose=True)
    
    # Test the network
    print("\nTesting the trained network:")
    print("Input -> Predicted Output (Expected)")
    for i in range(len(X)):
        prediction = nn.predict(X[i:i+1])
        print(f"{X[i]} -> {prediction[0][0]:.4f} ({y[i][0]})")
    
    # Plot loss
    nn.plot_loss()
    
    # Example with different dataset
    print("\n" + "=" * 40)
    print("Training on a simple classification problem")
    
    # Create a simple 2D classification dataset
    np.random.seed(42)
    n_samples = 100
    X_class = np.random.randn(n_samples, 2)
    y_class = ((X_class[:, 0] + X_class[:, 1]) > 0).astype(int).reshape(-1, 1)
    
    # Train network
    nn_class = SimpleNeuralNetwork(input_size=2, hidden_size=8, output_size=1, learning_rate=0.5)
    nn_class.train(X_class, y_class, epochs=1000, verbose=False)
    
    # Calculate accuracy
    predictions = nn_class.predict(X_class)
    predicted_classes = (predictions > 0.5).astype(int)
    accuracy = np.mean(predicted_classes == y_class)
    print(f"Final accuracy: {accuracy:.2f}")