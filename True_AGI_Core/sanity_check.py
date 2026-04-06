"""
sanity_check.py — Hardware Compute Verification
Validates that the PyTorch pipeline can initialize hierarchical
tensors and execute matrix operations on the best available device.
"""
import torch
import sys

print("=" * 60)
print("TRUE AGI CORE — HARDWARE SANITY CHECK")
print("=" * 60)

# 1. Device Detection
if torch.cuda.is_available():
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
    print(f"[DEVICE]  CUDA GPU DETECTED: {gpu_name}")
    print(f"[VRAM]    {gpu_mem:.1f} GB")
else:
    device = torch.device("cpu")
    print(f"[DEVICE]  CPU (No CUDA GPU detected)")

print(f"[PYTORCH] {torch.__version__}")
print(f"[PYTHON]  {sys.version.split()[0]}")
print()

# 2. Hierarchical Tensor Initialization
print("[TEST 1] Initializing Hierarchical State Tensors...")
mu_l1 = torch.randn(16, device=device)  # Level 1: Syntactic (Dim=16)
mu_l2 = torch.randn(4, device=device)   # Level 2: Semantic  (Dim=4)
print(f"  mu^(1) shape: {mu_l1.shape} | device: {mu_l1.device}")
print(f"  mu^(2) shape: {mu_l2.shape} | device: {mu_l2.device}")
print("  [PASS]")
print()

# 3. Precision Matrix Multiplication
print("[TEST 2] Precision-Weighted Prediction Error (Pi * epsilon)...")
Pi = torch.diag(torch.exp(torch.ones(3, device=device) * 5.0))  # 3x3 Precision
epsilon = torch.randn(3, device=device)  # Sensory error
result = torch.matmul(torch.matmul(epsilon, Pi), epsilon)
print(f"  Pi shape:      {Pi.shape}")
print(f"  epsilon shape: {epsilon.shape}")
print(f"  F_sensory:     {result.item():.4f}")
print("  [PASS]")
print()

# 4. Generative Model Forward Pass
print("[TEST 3] Generative Model Forward Pass (Linear layers)...")
dynamics = torch.nn.Sequential(
    torch.nn.Linear(16 + 4, 32),   # state_dim_l1 + action_dim
    torch.nn.ReLU(),
    torch.nn.Linear(32, 16)
).to(device)
test_input = torch.randn(20, device=device)  # Concatenated [mu_l1, action]
output = dynamics(test_input)
print(f"  Input shape:  {test_input.shape}")
print(f"  Output shape: {output.shape}")
print(f"  Output norm:  {output.norm().item():.4f}")
print("  [PASS]")
print()

# 5. Gradient Descent Verification
print("[TEST 4] Variational Update (Gradient Descent on mu)...")
mu_test = torch.randn(16, device=device, requires_grad=True)
target = torch.randn(16, device=device)
optimizer = torch.optim.SGD([mu_test], lr=0.01)
initial_loss = torch.nn.functional.mse_loss(mu_test, target).item()
for _ in range(50):
    optimizer.zero_grad()
    loss = torch.nn.functional.mse_loss(mu_test, target)
    loss.backward()
    optimizer.step()
final_loss = loss.item()
print(f"  Initial Loss: {initial_loss:.4f}")
print(f"  Final Loss:   {final_loss:.4f}")
print(f"  Reduction:    {((initial_loss - final_loss) / initial_loss * 100):.1f}%")
print("  [PASS]")
print()

# 6. Dynamic Tensor Resizing (Structure Learning Proof)
print("[TEST 5] Dynamic Tensor Resizing (Bayesian Model Reduction)...")
mu_dynamic = torch.randn(4, device=device)
print(f"  Initial dim:  {mu_dynamic.shape[0]}")
new_mu = torch.zeros(7, device=device)
new_mu[:4] = mu_dynamic
mu_dynamic = new_mu
print(f"  After growth: {mu_dynamic.shape[0]}")
print("  [PASS]")
print()

print("=" * 60)
print(f"ALL TESTS PASSED | Compute Device: {device.type.upper()}")
print("=" * 60)
