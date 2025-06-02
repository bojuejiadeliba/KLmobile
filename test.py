import torch
checkpoint = torch.load("D:/AU/Dissertation/KLCaption/checkpoints/clip_mobile_test-v3.ckpt")
print("Hyperparameters from training:")
print(checkpoint.get('hyper_parameters', 'Not found'))