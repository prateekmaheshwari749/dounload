import kagglehub

# Download latest version
path = kagglehub.dataset_download("unidpro/hindi-speech-recognition-dataset")

print("Path to dataset files:", path)