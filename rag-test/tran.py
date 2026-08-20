def train_model(data):
    model_name = "xgboost"
    print(f"Training with {model_name}")
    return model_name


def predict(model, features):
    return model.predict(features)