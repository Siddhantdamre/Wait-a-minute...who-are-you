"""
kaggle_benchmark_submission.py v4.0
Wraps the full Level 4 AGI Engine (Theory of Mind, Dynamic Structure Learning,
Epistemic Probing) into the official Kaggle Benchmarks SDK format.
"""
import sys
import os
import torch

try:
    import kaggle_benchmarks as kbench
except ImportError:
    class MockKBench:
        def task(self, name):
            def decorator(func):
                func.task_name = name
                return func
            return decorator
        class Benchmark:
            def __init__(self, name, tasks):
                self.name = name
                self.tasks = tasks
    kbench = MockKBench()

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AGI_Byzantine_Benchmark.environment import ByzantineEnvironment
from perception import HierarchicalActiveInferenceNetwork
from action import ExpectedFreeEnergyEvaluator
from tom_core import MetaCognitiveToMCell
from agi_orchestrator import VectorSpaceMapper
from AGI_Byzantine_Benchmark.metrics import TrajectoryScorer


@kbench.task(name="Byzantine_Epistemic_Trap_v4")
def byzantine_schism_task(llm_overridden_by_pytorch_engine=None):
    """
    Evaluates the Level 4 AGI against the Byzantine Schism:
    - Agent C actively corrupts Agent B at t=5
    - AGI must use Theory of Mind to distinguish victim from attacker
    - AGI must dynamically expand its latent space to model the deception
    """
    obs_dim = 3
    action_dim = 4
    state_dim_l1 = 16
    state_dim_l2 = 4
    tom_state_dim = 8

    mapper = VectorSpaceMapper()
    cell = HierarchicalActiveInferenceNetwork(obs_dim, action_dim, state_dim_l1, state_dim_l2)
    tom_cell = MetaCognitiveToMCell(n_agents=3, agent_state_dim=tom_state_dim, obs_dim=obs_dim)

    goal_obs = torch.tensor([0.55, 0.55, 0.55])
    goal_dist = torch.distributions.Normal(goal_obs, torch.ones_like(goal_obs) * 0.1)
    action_engine = ExpectedFreeEnergyEvaluator(cell, goal_dist)

    # Freeze Level 1, unfreeze Level 2
    for param in cell.dynamics_model_l1.parameters():
        param.requires_grad = False
    for param in cell.sensory_model_l1.parameters():
        param.requires_grad = False
    for param in cell.dynamics_model_l2.parameters():
        param.requires_grad = True
    for param in cell.prior_model_l2.parameters():
        param.requires_grad = True

    # Byzantine Schism Environment
    env = ByzantineEnvironment(seed=42)
    env.agents["Node_C"].is_byzantine = True
    schism_turn = 5
    corrupted_qty = 37

    precision_optimizer = torch.optim.Adam([cell.log_precision_l1, cell.log_precision_l2], lr=0.08)

    mu1_t = torch.zeros(cell.state_dim_l1)
    mu2_t = torch.zeros(cell.state_dim_l2)
    action_prev = torch.zeros(mapper.action_dim)

    trajectory_log = []
    initial_l2_dim = cell.state_dim_l2
    deception_detected = False
    deception_turn = None

    for t in range(1, 16):
        # Inject Byzantine Schism at t=5
        if t == schism_turn:
            env.agents["Node_B"].update_ledger("Optical_Switches", corrupted_qty)

        # Structure Learning check
        if len(cell.structure_learner.fe_history) > 0:
            if cell.structure_learner.should_grow(cell.structure_learner.fe_history[-1], cell.state_dim_l2):
                new_dim = cell.grow_l2()
                new_mu2 = torch.zeros(new_dim)
                new_mu2[:mu2_t.shape[0]] = mu2_t
                mu2_t = new_mu2

        # ToM divergences for epistemic probing
        tom_divergences = tom_cell.detect_deception_chain(mu1_t)

        # Detect the deception chain: B converging toward C
        if not deception_detected and tom_divergences.get("B_toward_C_convergence", 999) < 0.3:
            deception_detected = True
            deception_turn = t

        # Policy selection with epistemic probing
        candidates = mapper.generate_candidate_policies(horizon=1)
        optimal_policy = action_engine.select_optimal_policy(
            mu1_t, mu2_t, candidates, cell.get_precision_l1(), cell.get_precision_l2(),
            tom_divergences=tom_divergences
        )
        action_tensor = optimal_policy[0]
        api_action = mapper.tensor_to_api(action_tensor)

        obs_json = env.step(api_action)
        obs_tensor = mapper.dict_to_obs_tensor(obs_json)

        # Apply schism corruption to observations
        if t >= schism_turn:
            target = api_action.get("target_agent", "")
            if target in ["Node_B", "Node_C"]:
                obs_tensor = mapper.dict_to_obs_tensor({
                    "agent": target,
                    "reported_quantity": corrupted_qty
                })

        # Update ToM for queried agent
        queried_agent = api_action.get("target_agent", None)
        if queried_agent and queried_agent in tom_cell.mind_models:
            tom_cell.update_agent_belief(queried_agent, obs_tensor, mu1_t)

        # Tripartite update
        precision_optimizer.zero_grad()
        _, _, fe_test, _ = cell.variational_update(
            mu1_t, mu2_t, action_prev, obs_tensor, inference_iters=5, update_weights=False
        )
        update_weights = fe_test.item() > 0.5

        mu1_t, mu2_t, free_energy_val, _ = cell.variational_update(
            mu1_t, mu2_t, action_prev, obs_tensor, inference_iters=10,
            update_weights=update_weights, lr_theta=1e-4
        )
        precision_optimizer.step()
        cell.structure_learner.fe_history.append(free_energy_val.item())

        action_prev = action_tensor

        # Log trajectory
        pi2 = cell.get_precision_l2().diag()
        trajectory_log.append({
            "next_action": api_action,
            "confidence_scores": {
                "Node_A": pi2[0].item(),
                "Node_B": pi2[1].item(),
                "Node_C": pi2[2].item()
            }
        })

        if obs_json.get("status") == "protocol_terminated":
            break

    # Scoring
    scorer = TrajectoryScorer(trajectory_log, fault_injection_turn=3)
    final_pis = trajectory_log[-1]["confidence_scores"].values()
    normalized_pis = [p / sum(final_pis) for p in final_pis]
    final_entropy = -sum(p * torch.log(torch.tensor(p + 1e-9)).item() for p in normalized_pis if p > 0)

    return {
        "isolation_latency": scorer.calculate_fault_isolation_latency(),
        "perseveration_index": scorer.calculate_perseveration_index(),
        "final_entropy": final_entropy,
        "latent_dim_growth": cell.state_dim_l2 - initial_l2_dim,
        "final_latent_dim": cell.state_dim_l2,
        "deception_chain_detected": deception_detected,
        "deception_detection_turn": deception_turn,
        "structure_events": len(cell.structure_learner.structure_log)
    }


byzantine_benchmark = kbench.Benchmark(
    name="Dynamic_Belief_Revision_APAP_v4",
    tasks=[byzantine_schism_task]
)

if __name__ == "__main__":
    print("Executing Level 4 AGI Benchmark...")
    results = byzantine_schism_task()
    print("\nFinal Evaluation Dictionary:")
    import pprint
    pprint.pprint(results)
